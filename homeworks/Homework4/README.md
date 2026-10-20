# Homework 4: Git Repository Analysis Agent

Python 3.13+ project managed with uv. Stage 2 implements the custom analysis
MCP server; the AI agent and external Git MCP server are reserved for later.

## Setup and run

```sh
uv sync --locked
uv run python mcp-server.py
```

The server uses MCP stdio transport and waits for an MCP client. The sole direct
dependency is the official `mcp` SDK, constrained to v1 for its FastMCP API.
uv creates the project-specific `.venv/`.

## Tools

Each tool takes `repository_dir`, an existing repository directory, and returns
sorted results with repository-relative paths:

- `list_python_files`: lists regular `.py` files recursively.
- `find_missing_docstrings`: reports file, function name, and 1-based line for
  functions, async functions, methods, and nested functions missing docstrings.
- `find_todo_comments`: reports file, 1-based line, and comment text for
  case-insensitive TODO words in Python comments; strings are ignored.

The supplied directory defines the analysis boundary; it need not contain Git
metadata. Child symlinks are never followed. `.git`, `.venv`, `venv`,
`__pycache__`, `.pytest_cache`, and `.ruff_cache` directories are excluded.
Directory-relative, non-following file opens prevent reading symlink targets.
The server requires a platform supporting `os.fwalk` and `os.O_NOFOLLOW`
(such as this project's Linux environment).

Invalid directories, read errors, syntax errors during AST analysis, and
comment tokenization errors are reported as tool errors rather than silently
omitting files. Python source encoding declarations are honored.

## Tests

```sh
uv run --locked python -m unittest discover -s tests -v
```

Tests use temporary repositories to check each tool, exclusions, symlink escape
attempts, nested and async functions, comment/string distinctions, source
encodings, invalid input, and empty repositories. A real stdio MCP client also
initializes the server, discovers the three tools, and calls each one.
No additional test dependency is required.

`agent.py` remains a placeholder. `screencast_url.txt` is reserved for the final
screencast URL. Keep API keys out of source files; use environment variables
if credentials are needed later. Local `.env` files are ignored.
