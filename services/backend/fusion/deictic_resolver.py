"""
Deictic Pronoun & Visual-Semantic Reference Resolver.
Translates ambiguous conversational references ("this function", "this class", "that error")
into concrete AST codebase symbols, line numbers, and file paths using on-screen tokens.

Part of Phenom 21.0 Sovereign Omnimodal Intelligence (FUS-01.2).
"""

import re
import time
from typing import Any, Dict, List, Optional, Tuple, Union
from pydantic import BaseModel, Field

from services.backend.coding.workspace_indexer import workspace_indexer
from services.backend.safety.guardian import guardian
from services.backend.automation.gui_controller import Rule8ViolationError


class DeicticResolution(BaseModel):
    phrase: str = Field(..., description="Original user phrase containing deictic reference")
    resolved: bool = Field(default=False, description="Whether reference was successfully resolved")
    deictic_target_kind: Optional[str] = Field(default=None, description="Inferred target kind: function, class, file, error, ui_element, generic")
    symbol_name: Optional[str] = Field(default=None, description="Resolved AST symbol name")
    kind: Optional[str] = Field(default=None, description="Symbol kind: function, class, method, ui_element, etc.")
    file_path: Optional[str] = Field(default=None, description="Source file containing symbol")
    line_number: Optional[int] = Field(default=None, description="Line number in source file")
    signature: Optional[str] = Field(default=None, description="Function/class signature")
    confidence: float = Field(default=0.0, description="Resolution confidence [0.0 - 1.0]")
    explanation: str = Field(default="", description="Human-readable resolution rationale")
    ocr_token: Optional[str] = Field(default=None, description="Matching OCR text token")
    bounding_box: Optional[List[int]] = Field(default=None, description="Spatial coordinates [x1, y1, x2, y2]")

    def __await__(self):
        async def _identity():
            return self
        return _identity().__await__()


# Alias for backward compatibility
DeicticTarget = DeicticResolution


class DeicticResolver:
    """
    Resolves conversational on-screen references using active OCR/UIA tokens and AST workspace index.
    """

    FUNCTION_TRIGGER_RE = re.compile(r"\b(?:this|the)\s+(?:function|method|handler|coroutine|endpoint)\b", re.IGNORECASE)
    CLASS_TRIGGER_RE = re.compile(r"\b(?:this|the)\s+(?:class|struct|interface|type|object)\b", re.IGNORECASE)
    FILE_TRIGGER_RE = re.compile(r"\b(?:this|the)\s+(?:file|module|script|document)\b", re.IGNORECASE)
    ERROR_TRIGGER_RE = re.compile(r"\b(?:this|that|the)\s+(?:error|bug|issue|exception|traceback|failure)\b", re.IGNORECASE)
    BUTTON_TRIGGER_RE = re.compile(r"\b(?:this|the|that)\s+(?:button|checkbox|toggle|input|tab|link|icon)\b", re.IGNORECASE)

    RULE_8_PAYMENT_RE = re.compile(
        r"\b(?:checkout|place\s+order|pay\s+now|buy\s+now|complete\s+purchase|credit\s+card|cvv|password)\b",
        re.IGNORECASE
    )

    TOKEN_RE = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]{2,}\b")

    def resolve(
        self,
        query: Optional[str] = None,
        phrase: Optional[str] = None,
        screen_text: Optional[str] = None,
        active_file: Optional[str] = None,
        cursor_line: Optional[int] = None,
        ast_symbols: Optional[List[Dict[str, Any]]] = None,
        ocr_tokens: Optional[List[Dict[str, Any]]] = None,
        cursor_pos: Optional[Tuple[int, int]] = None,
        focused_window_title: Optional[str] = None,
    ) -> DeicticResolution:
        """
        Resolves on-screen references in query/phrase against screen_text, ocr_tokens, and AST workspace symbols.
        Strictly enforces Rule 8 anti-checkout invariants.
        """
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is active. Deictic resolution halted.")

        effective_query = (query or phrase or "").strip()

        # Rule 8 Check: Automated checkout and password entry are categorically blocked
        if self.RULE_8_PAYMENT_RE.search(effective_query):
            raise Rule8ViolationError(
                f"Rule 8 Violation: Deictic reference to payment/checkout target in '{effective_query}' is blocked by construction."
            )

        if ocr_tokens:
            for tok in ocr_tokens:
                txt = tok.get("text", "")
                if self.RULE_8_PAYMENT_RE.search(txt) and ("pay" in effective_query.lower() or "checkout" in effective_query.lower() or "buy" in effective_query.lower()):
                    raise Rule8ViolationError(
                        f"Rule 8 Violation: Action target '{txt}' is a payment or checkout control."
                    )

        t0 = time.perf_counter()

        # Step 1: Detect target category
        target_kind = "generic"
        if self.FUNCTION_TRIGGER_RE.search(effective_query):
            target_kind = "function"
        elif self.CLASS_TRIGGER_RE.search(effective_query):
            target_kind = "class"
        elif self.FILE_TRIGGER_RE.search(effective_query):
            target_kind = "file"
        elif self.ERROR_TRIGGER_RE.search(effective_query):
            target_kind = "error"
        elif self.BUTTON_TRIGGER_RE.search(effective_query) or "click" in effective_query.lower():
            target_kind = "ui_element"

        # If user explicitly references an active file
        if target_kind == "file" and active_file:
            return DeicticResolution(
                phrase=effective_query,
                resolved=True,
                deictic_target_kind="file",
                symbol_name=active_file,
                kind="file",
                file_path=active_file,
                line_number=cursor_line or 1,
                confidence=0.95,
                explanation=f"Resolved to active focused file '{active_file}'.",
            )

        # Step 2: Handle UI elements (buttons, inputs) with OCR tokens and cursor pos
        if target_kind == "ui_element" and ocr_tokens:
            best_tok = None
            min_dist = float("inf")
            for tok in ocr_tokens:
                bbox = tok.get("bbox", [0, 0, 0, 0])
                if cursor_pos:
                    cx = (bbox[0] + bbox[2]) / 2.0
                    cy = (bbox[1] + bbox[3]) / 2.0
                    dist = ((cursor_pos[0] - cx) ** 2 + (cursor_pos[1] - cy) ** 2) ** 0.5
                    if dist < min_dist:
                        min_dist = dist
                        best_tok = tok
                else:
                    best_tok = tok
                    break

            if best_tok:
                return DeicticResolution(
                    phrase=effective_query,
                    resolved=True,
                    deictic_target_kind="ui_element",
                    symbol_name=best_tok.get("text"),
                    kind="ui_element",
                    confidence=0.9,
                    ocr_token=best_tok.get("text"),
                    bounding_box=best_tok.get("bbox"),
                    explanation=f"Resolved to on-screen UI element '{best_tok.get('text')}' at {best_tok.get('bbox')}.",
                )

        # Step 3: Extract candidate tokens from screen_text or ocr_tokens
        candidate_tokens: List[str] = []
        if screen_text:
            candidate_tokens.extend(self.TOKEN_RE.findall(screen_text))
        if ocr_tokens:
            for tok in ocr_tokens:
                t_str = tok.get("text", "")
                candidate_tokens.extend(self.TOKEN_RE.findall(t_str))

        query_tokens = self.TOKEN_RE.findall(effective_query)
        candidate_tokens.extend(query_tokens)

        # Step 4: Check explicitly passed AST symbols
        if ast_symbols:
            for sym in ast_symbols:
                s_name = sym.get("name", "")
                s_kind = sym.get("kind", "")
                score = 0.5
                if target_kind == "function" and s_kind in ("function", "method", "async def"):
                    score += 0.4
                elif target_kind == "class" and s_kind in ("class", "interface"):
                    score += 0.4
                
                # Check if symbol appears in OCR tokens or query
                if any(s_name == c for c in candidate_tokens):
                    score += 0.2
                if focused_window_title and sym.get("file", "") in focused_window_title:
                    score += 0.2

                if score >= 0.7:
                    return DeicticResolution(
                        phrase=effective_query,
                        resolved=True,
                        deictic_target_kind=target_kind,
                        symbol_name=s_name,
                        kind=s_kind,
                        file_path=sym.get("file") or sym.get("file_path"),
                        line_number=sym.get("line") or sym.get("line_number"),
                        signature=sym.get("signature"),
                        confidence=min(1.0, round(score, 2)),
                        explanation=f"Resolved reference to {s_kind} '{s_name}' in {sym.get('file')}:{sym.get('line')}.",
                    )

        # Step 5: Match against AST Workspace Indexer
        best_match = None
        best_score = 0.0

        for token in set(candidate_tokens):
            sym = workspace_indexer.lookup_symbol(token)
            if sym:
                score = 0.5
                if target_kind == "function" and sym.get("kind") in ("function", "method", "async def"):
                    score += 0.4
                elif target_kind == "class" and sym.get("kind") in ("class", "interface"):
                    score += 0.4
                elif target_kind == "generic":
                    score += 0.2

                if active_file and sym.get("file_path") and active_file in sym.get("file_path", ""):
                    score += 0.2

                if score > best_score:
                    best_score = score
                    best_match = sym

        if best_match and best_score >= 0.5:
            return DeicticResolution(
                phrase=effective_query,
                resolved=True,
                deictic_target_kind=target_kind,
                symbol_name=best_match.get("name"),
                kind=best_match.get("kind"),
                file_path=best_match.get("file_path"),
                line_number=best_match.get("line_number"),
                signature=best_match.get("signature"),
                confidence=min(1.0, round(best_score, 2)),
                explanation=f"Resolved on-screen reference to {best_match.get('kind')} '{best_match.get('name')}' in {best_match.get('file_path')}:{best_match.get('line_number')}.",
            )

        # Fallback: unresolved
        return DeicticResolution(
            phrase=effective_query,
            resolved=False,
            deictic_target_kind=target_kind,
            confidence=0.0,
            explanation="No matching AST symbol found in visible screen context or active workspace.",
        )


# Global singleton
deictic_resolver = DeicticResolver()
