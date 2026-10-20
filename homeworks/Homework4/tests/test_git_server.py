"""Test the official Git server independently using its checked-in launch config."""

import asyncio
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

PROJECT = Path(__file__).resolve().parents[1]


def git_output(*arguments: str) -> str:
    """Run a read-only Git query from Homework 4 and return its output."""
    return subprocess.check_output(
        ["git", *arguments], cwd=PROJECT, text=True
    ).strip()


class OfficialGitServerTests(unittest.IsolatedAsyncioTestCase):
    """Check the installed upstream server without starting the custom server."""

    async def test_startup_discovery_status_and_history(self):
        """Initialize MCP, discover tools, and compare read results to native Git."""
        async with asyncio.timeout(30):
            await self._check_server()

    async def _check_server(self):
        """Launch the exact checked-in configuration with Homework 4 as cwd."""
        configuration = json.loads((PROJECT / "git-server" / "mcp.json").read_text())
        settings = configuration["mcpServers"]["git"]
        parameters = StdioServerParameters(**settings, cwd=str(PROJECT))
        repository = git_output("rev-parse", "--show-toplevel")
        original_head = git_output("rev-parse", "HEAD")
        original_status = git_output("status", "--porcelain=v1")
        original_index = git_output("diff", "--cached", "--binary")
        expected_status = git_output("-C", repository, "status")
        expected_commits = git_output("log", "-3", "--format=%H").splitlines()
        async with stdio_client(parameters) as (read, write):
            async with ClientSession(read, write) as session:
                initialized = await session.initialize()
                self.assertEqual(initialized.serverInfo.name, "mcp-git")
                self.assertEqual(initialized.serverInfo.version, "2026.10.19")
                tools = {tool.name: tool for tool in (await session.list_tools()).tools}
                self.assertTrue({"git_status", "git_log", "git_show", "git_diff"} <= tools.keys())
                for name in ("git_status", "git_log"):
                    self.assertIn("repo_path", tools[name].inputSchema["required"])
                status = await session.call_tool("git_status", {"repo_path": repository})
                self.assertFalse(status.isError, status)
                status_text = "\n".join(item.text for item in status.content if item.type == "text")
                self.assertEqual(status_text.strip(), "Repository status:\n" + expected_status)
                history = await session.call_tool("git_log", {"repo_path": repository, "max_count": 3})
                self.assertFalse(history.isError, history)
                history_text = "\n".join(item.text for item in history.content if item.type == "text")
                self.assertEqual(history_text.count("Commit: "), len(expected_commits))
                positions = [history_text.index(f"Commit: {sha}") for sha in expected_commits]
                self.assertEqual(positions, sorted(positions))
                for label in ("Author:", "Date:", "Message:"):
                    self.assertIn(label, history_text)
                with tempfile.TemporaryDirectory() as outside:
                    rejected = await session.call_tool("git_status", {"repo_path": outside})
                    self.assertTrue(rejected.isError)
                    self.assertIn("outside", " ".join(
                        item.text for item in rejected.content if item.type == "text"))
                print(f"\nOfficial Git MCP {initialized.serverInfo.version}: discovered {len(tools)} tools; "
                      f"status matched Git; verified {len(expected_commits)} recent commits.")
        self.assertEqual(git_output("rev-parse", "HEAD"), original_head)
        self.assertEqual(git_output("status", "--porcelain=v1"), original_status)
        self.assertEqual(git_output("diff", "--cached", "--binary"), original_index)


if __name__ == "__main__":
    unittest.main()
