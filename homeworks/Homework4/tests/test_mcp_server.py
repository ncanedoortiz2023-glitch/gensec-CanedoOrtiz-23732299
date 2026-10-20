"""Independent tool tests and an MCP stdio integration test; run with unittest."""

import asyncio
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER_PATH = Path(__file__).resolve().parents[1] / "mcp-server.py"
spec = importlib.util.spec_from_file_location("analysis_server", SERVER_PATH)
server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server)


class ToolTests(unittest.TestCase):
    """Exercise real temporary repositories without additional test dependencies."""

    def setUp(self):
        """Create Python fixtures and paths that must remain outside the scan."""
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.root = self.base / "repo"
        self.root.mkdir()
        self.repository = str(self.root)
        (self.root / "sample.py").write_text(
            'def documented():\n    """A docstring."""\n    pass\n'
            'def missing():\n    def nested():\n        pass\n'
            'async def asynchronous():\n    pass\n'
            'class Example:\n    def method(self):\n        pass\n'
            '# TODO: fix this\nmessage = "TODO: not a comment"\n'
            '"""TODO: not a comment either"""\n# todo later\n# TODOLIST is not a marker\n'
        )
        (self.root / "nested").mkdir()
        (self.root / "nested" / "empty.py").write_text("")
        (self.root / "notes.txt").write_text("# TODO ignored")
        for directory in server.EXCLUDED_DIRECTORIES:
            excluded = self.root / directory
            excluded.mkdir()
            (excluded / "hidden.py").write_text("def hidden(): pass\n# TODO hidden\n")
        outside = self.base / "outside.py"
        outside.write_text("def secret(): pass\n# TODO secret\n")
        (self.root / "escape.py").symlink_to(outside)
        (self.root / "escape-dir").symlink_to(self.base, target_is_directory=True)
        (self.root / "cycle").symlink_to(self.root, target_is_directory=True)
        (self.root / "broken.py").symlink_to(self.base / "missing.py")

    def test_list_python_files(self):
        """Return only regular in-bound Python files in stable order."""
        self.assertEqual(server.list_python_files(self.repository), ["nested/empty.py", "sample.py"])

    def test_missing_docstrings(self):
        """Detect nested, async, and method definitions while accepting docstrings."""
        self.assertEqual(server.find_missing_docstrings(self.repository), [
            {"file": "sample.py", "function": "missing", "line": 4},
            {"file": "sample.py", "function": "nested", "line": 5},
            {"file": "sample.py", "function": "asynchronous", "line": 7},
            {"file": "sample.py", "function": "method", "line": 10},
        ])

    def test_todo_comments(self):
        """Recognize comment tokens, ignore strings, and honor encoding cookies."""
        (self.root / "encoded.py").write_bytes(b"# coding: latin-1\n# TODO: caf\xe9\n")
        findings = server.find_todo_comments(self.repository)
        self.assertEqual([(f["file"], f["line"]) for f in findings],
                         [("encoded.py", 2), ("sample.py", 12), ("sample.py", 15)])
        self.assertEqual(findings[0]["comment"], "# TODO: café")
        (self.root / "prefix.py").write_text("# TODOLIST\n")
        self.assertEqual(server.find_todo_comments(self.repository), findings)

    def test_invalid_repository(self):
        """Each tool rejects missing paths and files used as repository roots."""
        for tool in (server.list_python_files, server.find_missing_docstrings, server.find_todo_comments):
            with self.subTest(tool=tool.__name__):
                with self.assertRaises(FileNotFoundError):
                    tool(str(self.root / "absent"))
                with self.assertRaises(ValueError):
                    tool(str(self.root / "sample.py"))

    def test_empty_repository(self):
        """All tools return empty findings for an empty directory."""
        empty = self.base / "empty"
        empty.mkdir()
        for tool in (server.list_python_files, server.find_missing_docstrings, server.find_todo_comments):
            self.assertEqual(tool(str(empty)), [])

    def test_invalid_python(self):
        """Syntax errors are explicit, and listing still works on invalid code."""
        (self.root / "invalid.py").write_text("def broken(:\n")
        self.assertIn("invalid.py", server.list_python_files(self.repository))
        with self.assertRaises(SyntaxError):
            server.find_missing_docstrings(self.repository)
        with self.assertRaises(server.tokenize.TokenError):
            server.find_todo_comments(self.repository)


class ServerTests(unittest.IsolatedAsyncioTestCase):
    """Verify startup, discovery, and calls through the actual MCP transport."""

    async def test_stdio_initialization_and_tools(self):
        """Initialize the subprocess, discover three tools, and call each one."""
        async with asyncio.timeout(20):
            await self._check_stdio()

    async def _check_stdio(self):
        """Check tool results through a real subprocess within the test timeout."""
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "example.py").write_text("def example():\n    pass\n# TODO: test\n")
            parameters = StdioServerParameters(command=sys.executable, args=[str(SERVER_PATH)])
            async with stdio_client(parameters) as (read, write):
                async with ClientSession(read, write) as session:
                    initialized = await session.initialize()
                    self.assertEqual(initialized.serverInfo.name, "Python Repository Analysis")
                    tools = (await session.list_tools()).tools
                    self.assertEqual({tool.name for tool in tools}, {
                        "list_python_files", "find_missing_docstrings", "find_todo_comments"})
                    expected = {
                        "list_python_files": ["example.py"],
                        "find_missing_docstrings": [{"file": "example.py", "function": "example", "line": 1}],
                        "find_todo_comments": [{"file": "example.py", "line": 3, "comment": "# TODO: test"}],
                    }
                    for tool in tools:
                        self.assertTrue(tool.description)
                        self.assertIn("repository_dir", tool.inputSchema["required"])
                        result = await session.call_tool(tool.name, {"repository_dir": directory})
                        self.assertFalse(result.isError, result)
                        self.assertEqual(result.structuredContent["result"], expected[tool.name])


if __name__ == "__main__":
    unittest.main()
