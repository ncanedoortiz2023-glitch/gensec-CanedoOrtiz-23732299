# Homework 4: Git Repository Analysis Agent

Stage 1 provides a minimal Python 3.13+ project managed with uv.

## Setup

```sh
uv sync --locked
uv run python --version
```

uv creates a project-specific `.venv/`. No third-party dependencies are
needed for this stage.

## Files

- `agent.py`: placeholder for the analysis agent.
- `mcp-server.py`: placeholder for the custom Python code-analysis MCP server.
- `screencast_url.txt`: reserved for the final screencast URL; currently empty.

Later stages will combine the custom server with the official Git MCP server.
No agent behavior or MCP tools are implemented yet.

Keep API keys out of source files. If credentials are needed in later stages,
provide them through environment variables; local `.env` files are ignored.
