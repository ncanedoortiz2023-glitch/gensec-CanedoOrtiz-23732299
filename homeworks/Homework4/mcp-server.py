"""Read-only repository analysis tools exposed through FastMCP over stdio."""

import ast
import io
import os
import re
import stat
import tokenize
from collections.abc import Iterator
from pathlib import Path

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Python Repository Analysis")
EXCLUDED_DIRECTORIES = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".ruff_cache"}


def _python_files(repository_dir: str) -> Iterator[tuple[str, bytes]]:
    """Yield relative names and contents without following child symlinks.

    repository_dir is the analysis boundary and must name an existing directory.
    Directory-relative opens and O_NOFOLLOW keep file reads inside the traversed
    directory even if a file is replaced with a symlink during scanning.
    """
    root = Path(repository_dir).expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError("repository_dir must be an existing directory")

    def fail(error: OSError) -> None:
        """Propagate traversal errors instead of hiding incomplete scans."""
        raise error

    for directory, directories, files, directory_fd in os.fwalk(
        root, topdown=True, onerror=fail, follow_symlinks=False
    ):
        directories[:] = sorted(set(directories) - EXCLUDED_DIRECTORIES)
        for name in sorted(files):
            if not name.endswith(".py"):
                continue
            info = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
            if not stat.S_ISREG(info.st_mode):
                continue
            descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory_fd)
            with os.fdopen(descriptor, "rb") as source:
                if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
                    continue
                yield (Path(directory) / name).relative_to(root).as_posix(), source.read()


@mcp.tool()
def list_python_files(repository_dir: str) -> list[str]:
    """List Python files recursively, returning sorted repository-relative paths.

    Args:
        repository_dir: Existing repository directory defining the scan boundary.
            Child symlinks and Git, virtual environment, and cache directories
            are excluded. Only regular files ending in .py are included.
    """
    return sorted(name for name, _ in _python_files(repository_dir))


@mcp.tool()
def find_missing_docstrings(repository_dir: str) -> list[dict[str, str | int]]:
    """Find functions, async functions, and methods without AST docstrings.

    Args:
        repository_dir: Existing repository directory to scan within, excluding
            child symlinks, Git metadata, virtual environments, and caches.

    Returns:
        Findings with repository-relative file, function name, and 1-based line.
        Nested functions are included. Invalid Python raises a syntax error
        rather than silently returning an incomplete report.
    """
    findings = []
    for name, source in _python_files(repository_dir):
        tree = ast.parse(source, filename=name)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if ast.get_docstring(node) is None:
                    findings.append({"file": name, "function": node.name, "line": node.lineno})
    return sorted(findings, key=lambda item: (item["file"], item["line"]))


@mcp.tool()
def find_todo_comments(repository_dir: str) -> list[dict[str, str | int]]:
    """Find case-insensitive TODO words in actual Python comment tokens.

    Args:
        repository_dir: Existing repository directory to scan within, excluding
            child symlinks, Git metadata, virtual environments, and caches.

    Returns:
        One finding per matching comment, with repository-relative file,
        1-based line, and comment text including its leading #. Strings and
        docstrings containing TODO are ignored. Encoding cookies are honored.
        Tokenization errors are reported rather than silently skipped.
    """
    findings = []
    for name, source in _python_files(repository_dir):
        for token in tokenize.tokenize(io.BytesIO(source).readline):
            if token.type == tokenize.COMMENT and re.search(r"\bTODO\b", token.string, re.IGNORECASE):
                findings.append({"file": name, "line": token.start[0], "comment": token.string})
    return sorted(findings, key=lambda item: (item["file"], item["line"]))


if __name__ == "__main__":
    mcp.run(transport="stdio")
