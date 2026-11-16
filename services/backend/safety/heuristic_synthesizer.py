"""Executable Heuristic Synthesizer & Rule Store (Milestone 49 Phase 2, REFL-02).

Compiles post-mortem evaluation results into persistent programmatic constraints,
validates syntax via Python AST, and exposes dynamic planner prompt guidelines.
"""

from __future__ import annotations

import ast
import json
import logging
import os
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

from services.backend.schemas.reflective_postmortem import (
    HeuristicRule,
    PostMortemAnalysis,
)
from services.backend.safety.guardian import guardian

logger = logging.getLogger("phenom.safety.heuristic_synthesizer")


class HeuristicSynthesizer:
    """Manages compilation, AST validation, persistence, and evaluation of heuristic rules."""

    def __init__(self, heuristics_dir: Optional[str] = None) -> None:
        self.heuristics_dir = os.path.abspath(heuristics_dir or "services/backend/safety/heuristics")
        self._lock = threading.RLock()
        self._rules: Dict[str, HeuristicRule] = {}

        os.makedirs(self.heuristics_dir, exist_ok=True)
        self.reload_from_disk()

    def _assert_guardian(self) -> None:
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is active. Heuristic operation aborted.")

    def reload_from_disk(self) -> None:
        """Loads all persisted .json heuristic definitions from disk."""
        with self._lock:
            self._rules.clear()
            if not os.path.exists(self.heuristics_dir):
                return
            for fname in os.listdir(self.heuristics_dir):
                if fname.endswith(".json"):
                    fpath = os.path.join(self.heuristics_dir, fname)
                    try:
                        with open(fpath, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        rule = HeuristicRule(**data)
                        self._rules[rule.rule_id] = rule
                    except Exception as e:
                        logger.warning(f"Could not load heuristic rule file {fname}: {e}")

    def synthesize_from_postmortem(self, analysis: PostMortemAnalysis) -> HeuristicRule:
        """Compiles a PostMortemAnalysis into an active HeuristicRule."""
        self._assert_guardian()

        prop = analysis.proposed_heuristic or {}
        rule_id = prop.get("rule_id") or f"heur_{analysis.failure_signature}"
        constraint_expr = prop.get("constraint_expression") or "True"
        guideline = prop.get("planner_guideline") or f"Prevent failure pattern: {analysis.failure_signature}"
        desc = prop.get("description") or analysis.remediation_strategy

        return self.register_rule(
            rule_id=rule_id,
            tool_name=analysis.tool_name,
            failure_signature=analysis.failure_signature,
            description=desc,
            constraint_expression=constraint_expr,
            planner_guideline=guideline,
            confidence=analysis.confidence,
        )

    def register_rule(
        self,
        rule_id: str,
        tool_name: str,
        failure_signature: str,
        description: str,
        constraint_expression: str,
        planner_guideline: str,
        confidence: float = 1.0,
    ) -> HeuristicRule:
        """Validates AST syntax and persists a new HeuristicRule."""
        self._assert_guardian()

        # AST Validation: verify constraint expression parses cleanly
        try:
            ast.parse(constraint_expression, mode="exec")
        except SyntaxError as e:
            raise ValueError(f"Invalid Python AST in heuristic constraint expression: {e}")

        rule = HeuristicRule(
            rule_id=rule_id,
            tool_name=tool_name,
            failure_signature=failure_signature,
            description=description,
            constraint_expression=constraint_expression,
            planner_guideline=planner_guideline,
            is_active=True,
            confidence=confidence,
            created_at=time.time(),
        )

        with self._lock:
            # Persist to disk as JSON
            fpath = os.path.join(self.heuristics_dir, f"{rule_id}.json")
            with open(fpath, "w", encoding="utf-8") as f:
                json.dump(rule.model_dump(), f, indent=2)

            self._rules[rule.rule_id] = rule

        return rule

    def evaluate_heuristics(self, tool_name: str, args: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Evaluates all active heuristics for a given tool before execution."""
        self._assert_guardian()

        with self._lock:
            active_rules = [
                r for r in self._rules.values()
                if r.is_active and (r.tool_name == "*" or r.tool_name == tool_name)
            ]

        for rule in active_rules:
            # Restricted execution environment
            eval_globals = {
                "__builtins__": {
                    "True": True,
                    "False": False,
                    "None": None,
                    "all": all,
                    "any": any,
                    "len": len,
                    "str": str,
                    "int": int,
                    "float": float,
                    "isinstance": isinstance,
                    "dict": dict,
                    "list": list,
                },
                "os": os,
                "args": args,
            }

            try:
                # If constraint is an assertion statement or expression
                expr = rule.constraint_expression.strip()
                if expr.startswith("assert "):
                    exec(expr, eval_globals)
                else:
                    result = eval(expr, eval_globals)
                    if not result:
                        return False, f"Heuristic Violation [{rule.rule_id}]: {rule.description}"
            except AssertionError as ae:
                return False, f"Heuristic Assertion Failed [{rule.rule_id}]: {str(ae) or rule.description}"
            except Exception as e:
                logger.warning(f"Error evaluating heuristic rule {rule.rule_id}: {e}")
                # Don't fail open on syntax/eval error in heuristic
                return False, f"Heuristic Evaluation Error [{rule.rule_id}]: {e}"

        return True, None

    def get_planner_prompt_guidelines(self, tool_name: Optional[str] = None) -> str:
        """Renders active heuristic rules into concise bullet points for DAG planner system prompt."""
        self._assert_guardian()

        with self._lock:
            if tool_name:
                applicable = [
                    r for r in self._rules.values()
                    if r.is_active and (r.tool_name == "*" or r.tool_name == tool_name)
                ]
            else:
                applicable = [r for r in self._rules.values() if r.is_active]

        if not applicable:
            return ""

        lines = ["### Active Learned Heuristics:"]
        for r in applicable:
            lines.append(f"- [{r.tool_name}] {r.planner_guideline}")
        return "\n".join(lines)

    def list_rules(self, active_only: bool = True) -> List[HeuristicRule]:
        self._assert_guardian()
        with self._lock:
            if active_only:
                return [r for r in self._rules.values() if r.is_active]
            return list(self._rules.values())

    def toggle_rule(self, rule_id: str, active: bool) -> bool:
        self._assert_guardian()
        with self._lock:
            if rule_id in self._rules:
                self._rules[rule_id].is_active = active
                fpath = os.path.join(self.heuristics_dir, f"{rule_id}.json")
                if os.path.exists(fpath):
                    with open(fpath, "w", encoding="utf-8") as f:
                        json.dump(self._rules[rule_id].model_dump(), f, indent=2)
                return True
            return False
