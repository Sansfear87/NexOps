"""Unified diff parsing and code change analysis service."""
from __future__ import annotations

from dataclasses import dataclass, field
import os
import re
from typing import Dict, List, Optional


EXTENSION_LANGUAGE_MAP: Dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".jsx": "jsx",
    ".tsx": "tsx",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".c": "c",
    ".cpp": "cpp",
    ".h": "c_header",
    ".cs": "csharp",
    ".rb": "ruby",
    ".php": "php",
    ".sql": "sql",
    ".sh": "shell",
    ".bash": "shell",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".md": "markdown",
    ".html": "html",
    ".css": "css",
    ".dockerfile": "dockerfile",
}


@dataclass
class FileDiff:
    """Structured representation of differences for a single file."""
    filename: str
    status: str  # "added", "modified", "deleted", "renamed"
    additions: int = 0
    deletions: int = 0
    hunks: List[Dict[str, any]] = field(default_factory=list)  # {start_line, end_line, content}
    language: str = "text"


class DiffParser:
    """Parser for unified diff format generating structured change metadata."""

    def _detect_language(self, filename: str) -> str:
        """Detect programming language from file extension."""
        basename = os.path.basename(filename).lower()
        if basename == "dockerfile":
            return "dockerfile"
        _, ext = os.path.splitext(filename)
        return EXTENSION_LANGUAGE_MAP.get(ext.lower(), "text")

    def parse_unified_diff(self, diff_text: str) -> List[FileDiff]:
        """Parse unified diff string into a list of FileDiff objects.

        Args:
            diff_text: Raw unified diff output from git diff or GitHub API.

        Returns:
            List of FileDiff structures.
        """
        if not diff_text or not diff_text.strip():
            return []

        file_diffs: List[FileDiff] = []
        raw_files = re.split(r"(?m)(?=^diff --git )", diff_text)

        for chunk in raw_files:
            chunk = chunk.strip()
            if not chunk:
                continue

            lines = chunk.splitlines()
            filename = ""
            status = "modified"

            # Parse git diff header
            for line in lines[:10]:
                if line.startswith("diff --git "):
                    parts = line.split(" ")
                    if len(parts) >= 4:
                        filename = parts[3].lstrip("b/")
                elif "new file mode" in line:
                    status = "added"
                elif "deleted file mode" in line:
                    status = "deleted"
                elif "similarity index" in line or "rename from" in line:
                    status = "renamed"

            # Fallback filename extraction from +++ b/...
            if not filename:
                for line in lines:
                    if line.startswith("+++ b/"):
                        filename = line[6:].strip()
                        break
                    elif line.startswith("--- a/") and not filename:
                        filename = line[6:].strip()

            if not filename:
                filename = "unknown_file"

            # Parse hunks and count additions/deletions
            hunks: List[Dict[str, any]] = []
            additions = 0
            deletions = 0

            current_hunk: Optional[Dict[str, any]] = None
            hunk_lines: List[str] = []

            for line in lines:
                hunk_match = re.match(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,(\d+))? @@(.*)", line)
                if hunk_match:
                    if current_hunk:
                        current_hunk["content"] = "\n".join(hunk_lines)
                        hunks.append(current_hunk)
                        hunk_lines = []

                    start_line = int(hunk_match.group(2))
                    count = int(hunk_match.group(3)) if hunk_match.group(3) else 1
                    end_line = start_line + max(count - 1, 0)
                    header_context = hunk_match.group(4).strip()

                    current_hunk = {
                        "start_line": start_line,
                        "end_line": end_line,
                        "header_context": header_context,
                        "content": "",
                    }
                    continue

                if current_hunk:
                    hunk_lines.append(line)

                if line.startswith("+") and not line.startswith("+++"):
                    additions += 1
                elif line.startswith("-") and not line.startswith("---"):
                    deletions += 1

            if current_hunk:
                current_hunk["content"] = "\n".join(hunk_lines)
                hunks.append(current_hunk)

            language = self._detect_language(filename)
            file_diffs.append(
                FileDiff(
                    filename=filename,
                    status=status,
                    additions=additions,
                    deletions=deletions,
                    hunks=hunks,
                    language=language,
                )
            )

        return file_diffs

    def get_changed_functions(self, file_diff: FileDiff) -> List[str]:
        """Extract function and class signatures affected by this file diff."""
        changed: List[str] = []

        # 1. Inspect hunk headers context
        for hunk in file_diff.hunks:
            ctx = hunk.get("header_context", "")
            if ctx:
                fn_match = re.search(r"(?:def|function|class|func)\s+([a-zA-Z0-9_]+)", ctx)
                if fn_match:
                    changed.append(fn_match.group(1))

        # 2. Inspect added/modified lines in hunks
        function_patterns = [
            r"^\+\s*def\s+([a-zA-Z0-9_]+)\s*\(",             # Python def
            r"^\+\s*async\s+def\s+([a-zA-Z0-9_]+)\s*\(",       # Python async def
            r"^\+\s*class\s+([a-zA-Z0-9_]+)",                 # Class definition
            r"^\+\s*function\s+([a-zA-Z0-9_]+)\s*\(",         # JS/TS function
            r"^\+\s*(?:export\s+)?(?:const|let|var)\s+([a-zA-Z0-9_]+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>",  # JS/TS arrow
            r"^\+\s*func\s+(?:\([^)]+\)\s+)?([a-zA-Z0-9_]+)\s*\(",  # Go func
        ]

        for hunk in file_diff.hunks:
            content = hunk.get("content", "")
            for line in content.splitlines():
                if line.startswith("+"):
                    for pattern in function_patterns:
                        m = re.search(pattern, line)
                        if m:
                            changed.append(m.group(1))

        # Deduplicate preserving order
        seen = set()
        deduped = []
        for fn in changed:
            if fn not in seen:
                seen.add(fn)
                deduped.append(fn)
        return deduped

    def summarize(self, file_diffs: List[FileDiff]) -> str:
        """Produce a concise high-level summary string of file changes."""
        if not file_diffs:
            return "No changes detected."

        total_additions = sum(f.additions for f in file_diffs)
        total_deletions = sum(f.deletions for f in file_diffs)
        total_files = len(file_diffs)

        summary_lines = [
            f"Diff Summary: {total_files} file(s) changed (+{total_additions}, -{total_deletions})"
        ]

        for f in file_diffs:
            functions = self.get_changed_functions(f)
            fn_str = f" [functions: {', '.join(functions)}]" if functions else ""
            summary_lines.append(
                f"- {f.filename} ({f.status}, +{f.additions}/-{f.deletions}, {f.language}){fn_str}"
            )

        return "\n".join(summary_lines)
