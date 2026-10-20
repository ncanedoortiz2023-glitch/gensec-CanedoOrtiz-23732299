# Homework 4: Git Repository Analysis Agent

A read-only Gemini agent using the lab's FastAgent pattern. It connects a
custom Python analysis MCP server with the
[official Git MCP server](https://github.com/modelcontextprotocol/servers/tree/main/src/git).

## Setup

Requires Python 3.13+, uv, and Git on PATH. Run these commands from
`homeworks/Homework4`:

```sh
uv sync --locked
uv sync --project git-server --locked
```

The main `.venv` contains the agent and custom FastMCP server (MCP SDK 1.x).
`git-server/.venv` isolates the official Git server (MCP SDK 2.x). Both dependency
sets are recorded in their respective `pyproject.toml` and `uv.lock` files.

Export `GOOGLE_API_KEY` and `GOOGLE_MODEL` using your existing environment setup.
The agent reads both at runtime; no Gemini model or API key is hardcoded.
`GOOGLE_MODEL` can contain the model name alone or its `google.` prefix.
Do not put credentials in source files or commit them.

## Run

```sh
# Discover tools from both servers without calling Gemini.
uv run --locked python agent.py --list-tools

# Ask one question using Gemini.
uv run --locked python agent.py "Review recent commits and identify Python functions missing docstrings."

# Start an interactive conversation.
uv run --locked python agent.py

# Review a different local Git repository.
uv run --locked python agent.py --repository /absolute/path/to/repository "Summarize the latest three commits."
```

The agent starts both servers automatically. By default it reviews the enclosing
course repository, not only Homework 4. Example questions:

- Review the latest commit, then identify functions missing docstrings in the
  affected Python files. Include the commit hash, function names, and line numbers.
- Summarize the latest three commits and list current TODO comments in Python files.
- Show the current Git status and list the repository's Python files.

The custom tools list Python files, find missing function docstrings using AST,
and find actual TODO comments using tokenization. They skip child symlinks,
`.git`, virtual environments, and caches. Invalid source is reported as a tool
error. The agent exposes only read-only Git tools; dispatch checks also block
write-tool calls and paths outside the selected repository. There are no shell
or file-edit tools. Repository content used to answer questions is sent to Gemini.

The external server's launch configuration is `git-server/mcp.json`. The agent
resolves its paths at runtime and supplies the selected repository. To start
that server alone from Homework 4:

```sh
uv run --project git-server --locked python -m mcp_server_git --repository ../..
```

## Tests

```sh
# Existing tests; the live Gemini test is skipped by default.
uv run --locked python -m unittest discover -s tests -v

# Include the live multi-step Gemini test (uses your API credentials and quota).
RUN_LIVE_AGENT_TEST=1 uv run --locked python -m unittest discover -s tests -v
```

Tests cover each custom tool, both servers' initialization and discovery,
Git status and history, repository boundaries, and blocked write calls.
The live test has Gemini retrieve commits, inspect the newest commit, and use
docstring analysis to identify an undocumented function in a temporary repository.
File hashes, HEAD, index, and status are checked for unintended changes.

Fill in `screencast_url.txt` after recording the demonstration.
