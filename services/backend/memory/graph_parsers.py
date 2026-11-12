"""
Phenom Multi-Domain Knowledge Graph Parsers
Extracts structured knowledge nodes and relational edges across 4 domains:
1. Obsidian Vault Notes (wikilinks, tags, frontmatter, daily notes)
2. Code Repositories (Python AST, TypeScript/JS symbols, Git commit history)
3. Local Documents (PDF, DOCX, XLSX, PPTX with semantic chunking)
4. Workspace History (Gmail threads, Google Calendar meetings)

Includes strict secret exclusion and in-memory credential regex scrubbing.
"""

from __future__ import annotations

import ast
import logging
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import yaml

from services.backend.schemas.graph_rag import GraphEdge, GraphNode

logger = logging.getLogger("phenom.graph_parsers")

# Wikilink: [[Target]], [[Target#Section]], [[Target|Alias]]
WIKILINK_REGEX = re.compile(r"\[\[([^\]\|\#]+)(?:#[^\]\|]+)?(?:\|[^\]]+)?\]\]")
INLINE_TAG_REGEX = re.compile(r"(?:^|\s)#([a-zA-Z][a-zA-Z0-9_\-\/]*)")
FRONTMATTER_REGEX = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
DAILY_NOTE_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}(?:\.md)?$")

# TypeScript / JavaScript symbol matchers
TS_CLASS_REGEX = re.compile(r"^\s*(?:export\s+)?(?:default\s+)?class\s+([A-Za-z0-9_$]+)", re.MULTILINE)
TS_INTERFACE_REGEX = re.compile(r"^\s*(?:export\s+)?interface\s+([A-Za-z0-9_$]+)", re.MULTILINE)
TS_FUNC_REGEX = re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z0-9_$]+)", re.MULTILINE)
TS_CONST_FUNC_REGEX = re.compile(r"^\s*(?:export\s+)?const\s+([A-Za-z0-9_$]+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>", re.MULTILINE)

# Credential scrubbing patterns
CREDENTIAL_PATTERNS = [
    re.compile(r"-----BEGIN (?:[A-Z\s]+)?PRIVATE KEY-----[\s\S]*?-----END (?:[A-Z\s]+)?PRIVATE KEY-----"),
    re.compile(r"(?:api[_-]?key|secret|token|password|passwd|auth)\s*[:=]\s*['\"][A-Za-z0-9_\-\./+=]{8,}['\"]", re.IGNORECASE),
    re.compile(r"AKIA[0-9A-Z]{16}"),  # AWS Access Key
    re.compile(r"nvapi-[A-Za-z0-9_\-]{20,}"),  # NVIDIA API key
    re.compile(r"sk-[A-Za-z0-9_\-]{20,}"),  # OpenAI key
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),  # GitHub token
    re.compile(r"ya29\.[A-Za-z0-9_\-]{20,}"),  # Google OAuth token
]

SECRET_FILENAMES = {
    ".env", ".env.local", ".env.production", ".env.development",
    "id_rsa", "id_dsa", "id_ecdsa", "id_ed25519",
    "token.pickle", "credentials.json", "client_secret.json",
}

SECRET_EXTENSIONS = {
    ".pem", ".key", ".pkcs12", ".pfx", ".p12", ".crt", ".der",
}

IGNORED_DIRS = {
    ".git", ".venv", "venv", "node_modules", "dist", "build",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    ".idea", ".vscode", ".system_generated"
}


def scrub_credentials(text: str) -> str:
    """Sanitizes text by masking API keys, private keys, tokens, and passwords."""
    if not text:
        return ""
    sanitized = text
    for pattern in CREDENTIAL_PATTERNS:
        sanitized = pattern.sub("[REDACTED_CREDENTIAL]", sanitized)
    return sanitized


def is_secret_or_ignored_file(path_str: str) -> bool:
    """Checks whether a file path contains sensitive credentials or should be skipped."""
    normalized = path_str.replace("\\", "/")
    parts = normalized.split("/")
    filename = parts[-1].lower()

    # Check ignored directories
    for part in parts[:-1]:
        if part in IGNORED_DIRS:
            return True

    # Check exact secret filenames
    if filename in SECRET_FILENAMES or filename.startswith(".env"):
        return True

    # Check secret extensions
    _, ext = os.path.splitext(filename)
    if ext in SECRET_EXTENSIONS:
        return True

    # Check credential keywords in filename
    if any(k in filename for k in ["credential", "id_rsa", "secret_key", "private_key"]):
        return True

    return False


# ==============================================================================
# Domain 1: Obsidian Vault Parser
# ==============================================================================

class ObsidianVaultParser:
    """Parses Obsidian Markdown notes into GraphNode instances with wikilink edges."""

    def __init__(self, vault_root: Optional[str] = None):
        self.vault_root = vault_root

    def parse_content(self, content: str, rel_path: str) -> GraphNode:
        """Parses markdown content string into a GraphNode."""
        title = Path(rel_path).stem
        sanitized_content = scrub_credentials(content)

        # Extract YAML frontmatter
        frontmatter: Dict[str, Any] = {}
        body = sanitized_content
        fm_match = FRONTMATTER_REGEX.match(sanitized_content)
        if fm_match:
            try:
                fm_data = yaml.safe_load(fm_match.group(1))
                if isinstance(fm_data, dict):
                    frontmatter = fm_data
                    if "title" in frontmatter and isinstance(frontmatter["title"], str):
                        title = frontmatter["title"]
            except Exception as e:
                logger.debug(f"Failed to parse frontmatter in {rel_path}: {e}")
            body = sanitized_content[fm_match.end():]

        # Extract tags
        tags: Set[str] = set()
        if "tags" in frontmatter:
            fm_tags = frontmatter["tags"]
            if isinstance(fm_tags, list):
                tags.update([str(t).lstrip("#") for t in fm_tags])
            elif isinstance(fm_tags, str):
                tags.update([t.strip().lstrip("#") for t in fm_tags.split(",")])

        inline_tags = INLINE_TAG_REGEX.findall(body)
        tags.update(inline_tags)

        # Check daily note pattern
        is_daily = bool(DAILY_NOTE_REGEX.match(Path(rel_path).name))

        node_id = f"vault://{rel_path.replace(os.sep, '/')}"

        # Extract wikilinks and construct edges
        edges: List[GraphEdge] = []
        wikilinks = WIKILINK_REGEX.findall(body)
        for target in wikilinks:
            target_clean = target.strip()
            if target_clean:
                target_uri = f"vault://{target_clean}" if not target_clean.endswith(".md") else f"vault://{target_clean[:-3]}"
                edges.append(
                    GraphEdge(
                        source_id=node_id,
                        target_id=target_uri,
                        relation="references",
                        weight=1.0,
                        metadata={"target_name": target_clean}
                    )
                )

        # Generate summary
        summary_lines = [line.strip() for line in body.splitlines() if line.strip() and not line.startswith("#")]
        summary = " ".join(summary_lines[:5])[:400]

        return GraphNode(
            node_id=node_id,
            domain="vault",
            title=title,
            entity_type="note",
            summary=summary,
            tags=sorted(list(tags)),
            metadata={
                "rel_path": rel_path.replace(os.sep, "/"),
                "is_daily_note": is_daily,
                "frontmatter": frontmatter,
                "aliases": frontmatter.get("aliases", []),
            },
            edges=edges
        )

    def parse_file(self, file_path: str, vault_root: Optional[str] = None) -> Optional[GraphNode]:
        """Parses a single file on disk."""
        if is_secret_or_ignored_file(file_path):
            return None
        v_root = vault_root or self.vault_root or os.path.dirname(file_path)
        try:
            rel_path = os.path.relpath(file_path, v_root)
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            return self.parse_content(content, rel_path)
        except Exception as e:
            logger.error(f"Error parsing vault file {file_path}: {e}")
            return None

    def parse_vault(self, vault_root: Optional[str] = None) -> List[GraphNode]:
        """Scans and parses all markdown notes in a vault directory."""
        root = vault_root or self.vault_root
        if not root or not os.path.isdir(root):
            return []

        nodes: List[GraphNode] = []
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS]
            for fname in filenames:
                if fname.endswith(".md"):
                    full_path = os.path.join(dirpath, fname)
                    node = self.parse_file(full_path, root)
                    if node:
                        nodes.append(node)
        return nodes


# ==============================================================================
# Domain 2: Code Repository Parser
# ==============================================================================

class CodeRepositoryParser:
    """Parses code repositories using Python AST, JS/TS regex, and git log history."""

    def __init__(self, repo_root: Optional[str] = None, repo_name: str = "phenom"):
        self.repo_root = repo_root
        self.repo_name = repo_name

    def parse_python_content(self, content: str, rel_path: str) -> List[GraphNode]:
        """Parses Python source code with AST, generating class and function nodes."""
        sanitized = scrub_credentials(content)
        nodes: List[GraphNode] = []
        file_uri = f"code://{self.repo_name}/{rel_path.replace(os.sep, '/')}"

        try:
            tree = ast.parse(sanitized)
        except Exception as e:
            logger.debug(f"AST parsing failed for {rel_path}: {e}")
            # Fallback file node
            return [
                GraphNode(
                    node_id=file_uri,
                    domain="code",
                    title=Path(rel_path).name,
                    entity_type="code_symbol",
                    summary=f"Python source file: {rel_path}",
                    tags=["python"],
                    metadata={"rel_path": rel_path.replace(os.sep, "/")}
                )
            ]

        # File-level node
        module_doc = ast.get_docstring(tree) or ""
        file_node = GraphNode(
            node_id=file_uri,
            domain="code",
            title=Path(rel_path).name,
            entity_type="code_symbol",
            summary=module_doc[:300] if module_doc else f"Python module {rel_path}",
            tags=["python", "module"],
            metadata={"rel_path": rel_path.replace(os.sep, "/"), "type": "module"},
            edges=[]
        )
        nodes.append(file_node)

        # Traverse classes and functions
        for item in tree.body:
            if isinstance(item, ast.ClassDef):
                class_uri = f"{file_uri}:{item.name}"
                class_doc = ast.get_docstring(item) or ""
                bases = [ast.unparse(b) for b in item.bases] if hasattr(ast, "unparse") else []

                class_node = GraphNode(
                    node_id=class_uri,
                    domain="code",
                    title=item.name,
                    entity_type="code_symbol",
                    summary=class_doc[:300] if class_doc else f"Class {item.name}",
                    tags=["python", "class"],
                    metadata={
                        "rel_path": rel_path.replace(os.sep, "/"),
                        "symbol": item.name,
                        "type": "class",
                        "bases": bases,
                        "lineno": item.lineno
                    },
                    edges=[
                        GraphEdge(
                            source_id=class_uri,
                            target_id=file_uri,
                            relation="contains",
                            weight=1.0
                        )
                    ]
                )
                nodes.append(class_node)
                file_node.edges.append(
                    GraphEdge(source_id=file_uri, target_id=class_uri, relation="contains", weight=1.0)
                )

                # Class methods
                for m in item.body:
                    if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        method_uri = f"{file_uri}:{item.name}.{m.name}"
                        m_doc = ast.get_docstring(m) or ""
                        args = [arg.arg for arg in m.args.args]
                        method_node = GraphNode(
                            node_id=method_uri,
                            domain="code",
                            title=f"{item.name}.{m.name}",
                            entity_type="code_symbol",
                            summary=m_doc[:300] if m_doc else f"Method {item.name}.{m.name}({', '.join(args)})",
                            tags=["python", "method"],
                            metadata={
                                "rel_path": rel_path.replace(os.sep, "/"),
                                "symbol": f"{item.name}.{m.name}",
                                "type": "method",
                                "args": args,
                                "is_async": isinstance(m, ast.AsyncFunctionDef),
                                "lineno": m.lineno
                            },
                            edges=[
                                GraphEdge(source_id=method_uri, target_id=class_uri, relation="contains", weight=1.0)
                            ]
                        )
                        nodes.append(method_node)
                        class_node.edges.append(
                            GraphEdge(source_id=class_uri, target_id=method_uri, relation="contains", weight=1.0)
                        )

            elif isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_uri = f"{file_uri}:{item.name}"
                f_doc = ast.get_docstring(item) or ""
                args = [arg.arg for arg in item.args.args]
                func_node = GraphNode(
                    node_id=func_uri,
                    domain="code",
                    title=item.name,
                    entity_type="code_symbol",
                    summary=f_doc[:300] if f_doc else f"Function {item.name}({', '.join(args)})",
                    tags=["python", "function"],
                    metadata={
                        "rel_path": rel_path.replace(os.sep, "/"),
                        "symbol": item.name,
                        "type": "function",
                        "args": args,
                        "is_async": isinstance(item, ast.AsyncFunctionDef),
                        "lineno": item.lineno
                    },
                    edges=[
                        GraphEdge(source_id=func_uri, target_id=file_uri, relation="contains", weight=1.0)
                    ]
                )
                nodes.append(func_node)
                file_node.edges.append(
                    GraphEdge(source_id=file_uri, target_id=func_uri, relation="contains", weight=1.0)
                )

        return nodes

    def parse_ts_js_content(self, content: str, rel_path: str) -> List[GraphNode]:
        """Parses TypeScript/JavaScript source code via regex symbol extraction."""
        sanitized = scrub_credentials(content)
        nodes: List[GraphNode] = []
        file_uri = f"code://{self.repo_name}/{rel_path.replace(os.sep, '/')}"

        file_node = GraphNode(
            node_id=file_uri,
            domain="code",
            title=Path(rel_path).name,
            entity_type="code_symbol",
            summary=f"TypeScript/JavaScript source file: {rel_path}",
            tags=["typescript" if rel_path.endswith((".ts", ".tsx")) else "javascript"],
            metadata={"rel_path": rel_path.replace(os.sep, "/"), "type": "file"},
            edges=[]
        )
        nodes.append(file_node)

        symbols = set()
        for regex, stype in [
            (TS_CLASS_REGEX, "class"),
            (TS_INTERFACE_REGEX, "interface"),
            (TS_FUNC_REGEX, "function"),
            (TS_CONST_FUNC_REGEX, "function"),
        ]:
            for sym in regex.findall(sanitized):
                if sym not in symbols:
                    symbols.add(sym)
                    sym_uri = f"{file_uri}:{sym}"
                    sym_node = GraphNode(
                        node_id=sym_uri,
                        domain="code",
                        title=sym,
                        entity_type="code_symbol",
                        summary=f"{stype.capitalize()} {sym} in {rel_path}",
                        tags=[stype],
                        metadata={"rel_path": rel_path.replace(os.sep, "/"), "symbol": sym, "type": stype},
                        edges=[GraphEdge(source_id=sym_uri, target_id=file_uri, relation="contains", weight=1.0)]
                    )
                    nodes.append(sym_node)
                    file_node.edges.append(
                        GraphEdge(source_id=file_uri, target_id=sym_uri, relation="contains", weight=1.0)
                    )

        return nodes

    def parse_file(self, file_path: str, repo_root: Optional[str] = None) -> List[GraphNode]:
        """Parses a single code file if not ignored/secret."""
        if is_secret_or_ignored_file(file_path):
            return []
        root = repo_root or self.repo_root or os.path.dirname(file_path)
        try:
            rel_path = os.path.relpath(file_path, root)
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            if file_path.endswith(".py"):
                return self.parse_python_content(content, rel_path)
            elif file_path.endswith((".ts", ".tsx", ".js", ".jsx")):
                return self.parse_ts_js_content(content, rel_path)
            return []
        except Exception as e:
            logger.error(f"Error parsing code file {file_path}: {e}")
            return []

    def parse_git_history(
        self,
        repo_root: Optional[str] = None,
        max_commits: int = 50,
        commit_log_output: Optional[str] = None
    ) -> List[GraphNode]:
        """
        Parses recent git commit history, linking commits to modified code files.
        Accepts raw git log output or executes git log command.
        """
        root = repo_root or self.repo_root
        output = commit_log_output

        if output is None:
            if not root or not os.path.isdir(os.path.join(root, ".git")):
                return []
            try:
                cmd = ["git", "log", f"-n{max_commits}", "--name-only", "--pretty=format:COMMIT_START%h|%an|%ad|%s"]
                res = subprocess.run(cmd, cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
                output = res.stdout
            except Exception as e:
                logger.warning(f"Failed to run git log: {e}")
                return []

        nodes: List[GraphNode] = []
        raw_commits = output.split("COMMIT_START")
        for chunk in raw_commits:
            chunk = chunk.strip()
            if not chunk:
                continue
            lines = chunk.splitlines()
            header = lines[0]
            parts = header.split("|", 3)
            if len(parts) < 4:
                continue

            commit_hash, author, date_str, subject = parts[0].strip(), parts[1].strip(), parts[2].strip(), parts[3].strip()
            subject_scrubbed = scrub_credentials(subject)
            commit_uri = f"git://{self.repo_name}:{commit_hash}"

            changed_files = [line.strip().replace(os.sep, "/") for line in lines[1:] if line.strip()]
            edges: List[GraphEdge] = []
            for f in changed_files:
                if not is_secret_or_ignored_file(f):
                    target_file_uri = f"code://{self.repo_name}/{f}"
                    edges.append(
                        GraphEdge(
                            source_id=commit_uri,
                            target_id=target_file_uri,
                            relation="implements",
                            weight=0.9,
                            metadata={"action": "modifies"}
                        )
                    )

            commit_node = GraphNode(
                node_id=commit_uri,
                domain="code",
                title=f"Commit {commit_hash}: {subject_scrubbed[:60]}",
                entity_type="git_commit",
                summary=f"Commit by {author} on {date_str}: {subject_scrubbed}",
                tags=["git", "commit"],
                metadata={
                    "commit_hash": commit_hash,
                    "author": author,
                    "date": date_str,
                    "subject": subject_scrubbed,
                    "files": changed_files
                },
                edges=edges
            )
            nodes.append(commit_node)

        return nodes


# ==============================================================================
# Domain 3: Document Parser (PDF, DOCX, XLSX, PPTX, TXT)
# ==============================================================================

class DocumentParser:
    """Parses local rich documents with semantic chunking into doc:// nodes."""

    def __init__(self, doc_root: Optional[str] = None):
        self.doc_root = doc_root

    def parse_document(
        self,
        file_path: str,
        doc_root: Optional[str] = None,
        chunk_size: int = 1000,
        overlap: int = 100
    ) -> List[GraphNode]:
        """Parses document text, generating root document node and chunk nodes."""
        if is_secret_or_ignored_file(file_path):
            return []

        root = doc_root or self.doc_root or os.path.dirname(file_path)
        rel_path = os.path.relpath(file_path, root).replace(os.sep, "/")
        doc_uri = f"doc://{rel_path}"

        try:
            from services.backend.memory.doc_reader import doc_reader
            text = doc_reader.read_document(file_path)
        except Exception as e:
            logger.debug(f"Document reader failed for {file_path} ({e}). Attempting plain text read.")
            try:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    text = f.read()
            except Exception:
                return []

        sanitized_text = scrub_credentials(text)
        if not sanitized_text.strip():
            return []

        words = sanitized_text.split()
        chunks: List[str] = []
        step = max(1, chunk_size - overlap)
        for i in range(0, len(words), step):
            c = " ".join(words[i: i + chunk_size])
            chunks.append(c)
            if i + chunk_size >= len(words):
                break

        nodes: List[GraphNode] = []
        root_node = GraphNode(
            node_id=doc_uri,
            domain="doc",
            title=Path(file_path).name,
            entity_type="pdf_section" if file_path.lower().endswith(".pdf") else "doc_chunk",
            summary=sanitized_text[:300],
            tags=["document", Path(file_path).suffix.lstrip(".")],
            metadata={"rel_path": rel_path, "total_chunks": len(chunks)},
            edges=[]
        )
        nodes.append(root_node)

        for idx, chunk in enumerate(chunks):
            chunk_uri = f"{doc_uri}#chunk={idx}"
            chunk_node = GraphNode(
                node_id=chunk_uri,
                domain="doc",
                title=f"{Path(file_path).name} (chunk {idx})",
                entity_type="pdf_section" if file_path.lower().endswith(".pdf") else "doc_chunk",
                summary=chunk[:300],
                tags=["chunk"],
                metadata={"rel_path": rel_path, "chunk_index": idx},
                edges=[
                    GraphEdge(source_id=chunk_uri, target_id=doc_uri, relation="contains", weight=1.0)
                ]
            )
            nodes.append(chunk_node)
            root_node.edges.append(
                GraphEdge(source_id=doc_uri, target_id=chunk_uri, relation="contains", weight=1.0)
            )

        return nodes


# ==============================================================================
# Domain 4: Workspace History Parser (Gmail Threads & Calendar Events)
# ==============================================================================

class WorkspaceHistoryParser:
    """Parses priority Gmail threads and Google Calendar meetings into knowledge nodes."""

    @staticmethod
    def parse_email_threads(threads: List[Dict[str, Any]]) -> List[GraphNode]:
        """Converts priority email thread dictionaries into email:// GraphNodes."""
        nodes: List[GraphNode] = []
        for t in threads:
            thread_id = str(t.get("thread_id") or t.get("id") or abs(hash(t.get("subject", ""))))
            subject = scrub_credentials(str(t.get("subject") or "No Subject"))
            sender = scrub_credentials(str(t.get("sender") or t.get("from") or "Unknown"))
            snippet = scrub_credentials(str(t.get("snippet") or t.get("body") or ""))

            node_id = f"email://gmail:{thread_id}"
            node = GraphNode(
                node_id=node_id,
                domain="email",
                title=f"Email: {subject[:70]}",
                entity_type="email_thread",
                summary=f"From: {sender} | Snippet: {snippet[:300]}",
                tags=["email", "workspace"],
                metadata={
                    "thread_id": thread_id,
                    "sender": sender,
                    "subject": subject,
                    "urgency": t.get("urgency", "normal"),
                },
                edges=[]
            )
            nodes.append(node)
        return nodes

    @staticmethod
    def parse_calendar_events(events: List[Dict[str, Any]]) -> List[GraphNode]:
        """Converts Google Calendar event dictionaries into meeting:// GraphNodes."""
        nodes: List[GraphNode] = []
        for e in events:
            event_id = str(e.get("event_id") or e.get("id") or abs(hash(e.get("summary", ""))))
            summary = scrub_credentials(str(e.get("summary") or "Untitled Meeting"))
            description = scrub_credentials(str(e.get("description") or ""))
            attendees = [scrub_credentials(str(a)) for a in e.get("attendees", [])]
            start_time = str(e.get("start") or e.get("start_time") or "")

            node_id = f"meeting://cal:{event_id}"
            node = GraphNode(
                node_id=node_id,
                domain="meeting",
                title=f"Meeting: {summary[:70]}",
                entity_type="meeting_agenda",
                summary=f"Start: {start_time} | Attendees: {', '.join(attendees[:4])} | Agenda: {description[:300]}",
                tags=["calendar", "meeting", "workspace"],
                metadata={
                    "event_id": event_id,
                    "summary": summary,
                    "start": start_time,
                    "attendees": attendees,
                },
                edges=[]
            )
            nodes.append(node)
        return nodes

    @staticmethod
    def synthesize_cross_domain_links(
        workspace_nodes: List[GraphNode],
        other_nodes: List[GraphNode]
    ) -> List[GraphEdge]:
        """
        Heuristically matches meeting/email titles with code symbol or note titles,
        generating 'discussed_in' or 'references' cross-domain edges.
        """
        synthesized: List[GraphEdge] = []
        for ws in workspace_nodes:
            ws_text = f"{ws.title} {ws.summary}".lower()
            for other in other_nodes:
                other_title_clean = other.title.lower()
                # If a significant keyword/symbol is discussed
                if len(other_title_clean) > 3 and other_title_clean in ws_text:
                    synthesized.append(
                        GraphEdge(
                            source_id=ws.node_id,
                            target_id=other.node_id,
                            relation="discussed_in",
                            weight=0.85,
                            metadata={"matched_term": other.title}
                        )
                    )
        return synthesized
