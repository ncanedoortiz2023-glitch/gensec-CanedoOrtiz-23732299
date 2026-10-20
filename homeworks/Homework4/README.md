# Homework 4: Git Repository Analysis Agent

Python 3.13+ project managed with uv. Stage 2 provides the custom analysis
MCP server. Stage 3 configures the official Git MCP server independently.
Stage 4 connects both servers through a read-only Gemini FastAgent reviewer.

## Setup and run

```sh
uv sync --locked
uv run python mcp-server.py
```

The server uses MCP stdio transport and waits for an MCP client. The main
environment contains `fast-agent-mcp` and the official `mcp` SDK, constrained
to v1 for the custom server's FastMCP API.
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

`screencast_url.txt` is reserved for the final
screencast URL. Keep API keys out of source files; use environment variables
if credentials are needed later. Local `.env` files are ignored.

## Stage 3: official Git MCP server

Reviewed upstream before configuring:

- [README](https://github.com/modelcontextprotocol/servers/blob/main/src/git/README.md)
- [Implementation](https://github.com/modelcontextprotocol/servers/blob/main/src/git/src/mcp_server_git/server.py)
- [CLI entry point](https://github.com/modelcontextprotocol/servers/blob/main/src/git/src/mcp_server_git/__init__.py)
- [Package metadata](https://github.com/modelcontextprotocol/servers/blob/main/src/git/pyproject.toml)

The reviewed release is `mcp-server-git==2026.10.19`. It requires SDK 2.x;
our custom FastMCP server uses SDK 1.x. `git-server/pyproject.toml` and its
lockfile isolate the official server in `git-server/.venv/`, leaving the
Stage 2 server and its dependencies unchanged. Git must be installed on PATH.
No upstream source is copied or modified.

From `homeworks/Homework4`, install and start it independently:

```sh
uv sync --project git-server --locked
uv run --project git-server --locked python -m mcp_server_git --repository ../..
```

`git-server/mcp.json` records this stdio launch configuration for an MCP client.
Its relative paths require the client working directory to be Homework 4;
it is a configuration template, not an automatically enabled IDE connection.
The integration test loads this exact configuration with the correct cwd.
Use absolute project and repository paths if launching from elsewhere.

`../..` is the course repository root. `--repository` confines tool calls to
that repository, not just the Homework 4 subdirectory. Calls still supply
`repo_path` as the absolute repository root. The server advertises both read
and write tools; this stage invokes only `git_status` and `git_log` (plus an
expected rejected status request outside the configured repository).

Run only the external server test, or the complete suite:

```sh
uv run --locked python -m unittest discover -s tests -p test_git_server.py -v
uv run --locked python -m unittest discover -s tests -v
```

The Git test checks initialization and version, tool discovery, working-tree
status against native Git, and the latest three commit hashes in order. It
also checks repository confinement and that HEAD, index, and working-tree
status remain unchanged. These Stage 3 tests run the Git server independently.

## Stage 4: read-only Gemini agent

`agent.py` follows the labs' `FastAgent`, `@fast.agent`, and `fast.run()` pattern.
It starts the unchanged custom server with the main environment's Python and
loads the official server's launch command from `git-server/mcp.json`.
Absolute paths are resolved at runtime, so the agent can run from another cwd.
The Git server retains its isolated SDK 2.x environment.

Install both environments before running:

```sh
uv sync --locked
uv sync --project git-server --locked
```

Supply the existing lab variables `GOOGLE_API_KEY` and `GOOGLE_MODEL` through
your environment. Both are required for Gemini calls. The model is selected as
`google.${GOOGLE_MODEL}` unless the variable already has the `google.` prefix.
There is no hardcoded Gemini model or API key. The agent does not load `.env`
files explicitly; export variables in your shell or use your existing environment
loader. Do not put keys into source, configuration, command arguments, or commits.

```sh
# Tool discovery only: no model request or credentials needed.
uv run --locked python agent.py --list-tools

# One multi-step question; defaults to the enclosing course repository.
uv run --locked python agent.py "Review recent commits and identify Python functions missing docstrings."

# Interactive questions, or a different repository.
uv run --locked python agent.py
uv run --locked python agent.py --repository /absolute/path/to/repository "Summarize recent commits and TODO comments."
```

The reviewer exposes three custom analysis tools and seven read-only Git tools:
status, log, show, diff, staged diff, unstaged diff, and branch listing. It has no
shell, file-edit tools, skills, or child agents. A dispatch permission handler
also rejects every tool outside that allowlist, including guessed write-tool
names, and requires each tool's repository argument to resolve to the selected
Git root. This enforcement is separate from the model's read-only instructions.
Repository text is treated as untrusted data. Answers can cite hashes, paths,
function names, and line numbers; AST syntax errors are reported by the existing
server. Nothing in this stage automatically edits findings.

Conversation history remains in memory during a session. File logging,
trajectory saving, session history persistence, and telemetry are disabled;
generated configuration contains paths only and is removed from a temporary
directory when the session closes. Repository content requested through tools
is sent to Gemini to answer your question.

Run the normal suite (live model test is skipped by default), or explicitly opt
in to the Gemini integration test, which uses your credentials and API quota:

```sh
uv run --locked python -m unittest discover -s tests -v
RUN_LIVE_AGENT_TEST=1 uv run --locked python -m unittest discover -s tests -p test_agent.py -v
```

Agent tests create a temporary two-commit repository. They discover both servers,
verify AST findings, reject a branch-creation attempt and out-of-root scan, and
compare file hashes, HEAD, index, and status before and after. The live test
requires Gemini itself to call Git log, inspect the latest commit, call the
docstring analysis tool, and identify the new undocumented function with its
commit hash and source location. Server activity is recorded in memory without
tool contents. No credentials or test transcripts are stored in the repository.

Framework API reference: [FastAgent](https://fast-agent.ai/ref/class_reference/).
