"""Read-only agent tests, including an opt-in live Gemini multi-step review."""

import asyncio
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import agent


def git(repository: Path, *arguments: str) -> str:
    """Run Git in a test repository, configuring commit identity only per command."""
    return subprocess.check_output(
        ["git", "-C", str(repository), "-c", "user.name=Homework Test",
         "-c", "user.email=homework-test@example.invalid", *arguments], text=True,
    ).strip()


def snapshot(repository: Path) -> tuple:
    """Capture fixture file hashes, HEAD, status, and staged changes for comparison."""
    files = {path.relative_to(repository).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
             for path in repository.rglob("*") if path.is_file()
             and ".git" not in path.relative_to(repository).parts}
    return (files, git(repository, "rev-parse", "HEAD"),
            git(repository, "status", "--porcelain=v1"), git(repository, "diff", "--cached", "--binary"))


class AgentTests(unittest.IsolatedAsyncioTestCase):
    """Exercise configuration, server access, dispatch safety, and live reasoning."""

    def setUp(self):
        """Create a two-commit fixture with a newly introduced undocumented function."""
        temporary = tempfile.TemporaryDirectory(prefix="homework4-review-test-")
        self.addCleanup(temporary.cleanup)
        self.repository = Path(temporary.name).resolve()
        git(self.repository, "init", "-q", "-b", "main")
        source = self.repository / "review.py"
        source.write_text('def documented():\n    """Return a constant."""\n    return 1\n')
        git(self.repository, "add", "review.py")
        git(self.repository, "commit", "-q", "-m", "Add documented baseline")
        source.write_text(source.read_text() + '\ndef needs_docs(value):\n    return value\n# TODO: add documentation\n')
        git(self.repository, "add", "review.py")
        git(self.repository, "commit", "-q", "-m", "Add needs_docs helper")

    def test_environment_model(self):
        """Require both lab variables and preserve an explicitly qualified model."""
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "GOOGLE_API_KEY"):
                agent.gemini_model()
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-only-placeholder", "GOOGLE_MODEL": ""}):
            with self.assertRaisesRegex(ValueError, "GOOGLE_MODEL"):
                agent.gemini_model()
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-only-placeholder", "GOOGLE_MODEL": "test-model"}):
            self.assertEqual(agent.gemini_model(), "google.test-model")
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-only-placeholder", "GOOGLE_MODEL": "google.test-model"}):
            self.assertEqual(agent.gemini_model(), "google.test-model")

    async def test_permission_boundary(self):
        """Reject writes, unknown servers, missing paths, and paths outside the root."""
        policy = agent.ReadOnlyPolicy(self.repository)
        allowed = await policy.check_permission("git_log", "git", {"repo_path": str(self.repository)})
        self.assertTrue(allowed.allowed)
        attempts = [
            ("git_commit", "git", {"repo_path": str(self.repository)}),
            ("write_file", "analysis", {"repository_dir": str(self.repository)}),
            ("git_status", "unknown", {"repo_path": str(self.repository)}),
            ("git_status", "git", {}),
            ("find_missing_docstrings", "analysis", {"repository_dir": str(self.repository.parent)}),
        ]
        for tool, server, arguments in attempts:
            with self.subTest(tool=tool, server=server):
                self.assertFalse((await policy.check_permission(tool, server, arguments)).allowed)

    async def test_both_servers_and_write_denial(self):
        """Discover both servers, call their tools, and attempt a blocked write."""
        before = snapshot(self.repository)
        async with asyncio.timeout(90):
            async with agent.open_agent(self.repository, discovery_only=True) as (app, policy):
                runtime = app["reviewer"]
                names = {tool.name for tool in (await runtime.list_tools()).tools}
                expected = {f"{server}__{tool}" for server, tools in agent.READ_ONLY_TOOLS.items() for tool in tools}
                self.assertEqual(names, expected)
                status = await runtime.call_tool("git__git_status", {"repo_path": str(self.repository)})
                self.assertFalse(status.isError, status)
                findings = await runtime.call_tool("analysis__find_missing_docstrings", {
                    "repository_dir": str(self.repository)})
                self.assertFalse(findings.isError, findings)
                self.assertEqual(findings.structuredContent["result"], [
                    {"file": "review.py", "function": "needs_docs", "line": 5}])
                # Exercise dispatch directly, bypassing model-facing tool filtering.
                blocked = await runtime.call_tool("git__git_create_branch", {
                    "repo_path": str(self.repository), "branch_name": "must-not-exist"})
                self.assertTrue(blocked.isError)
                self.assertIn("blocked", " ".join(item.text for item in blocked.content if item.type == "text"))
                self.assertEqual(git(self.repository, "branch", "--list", "must-not-exist"), "")
                outside = await runtime.call_tool("analysis__list_python_files", {
                    "repository_dir": str(self.repository.parent)})
                self.assertTrue(outside.isError)
                self.assertEqual(policy.completed, [
                    ("git", "git_status", True), ("analysis", "find_missing_docstrings", True)])
        self.assertEqual(snapshot(self.repository), before)

    @unittest.skipUnless(os.environ.get("RUN_LIVE_AGENT_TEST") == "1", "Opt in to paid Gemini calls with RUN_LIVE_AGENT_TEST=1")
    async def test_live_multistep_review(self):
        """Have Gemini inspect a commit, connect AST findings, and leave files intact."""
        before = snapshot(self.repository)
        latest = git(self.repository, "rev-parse", "HEAD")
        async with asyncio.timeout(180):
            async with agent.open_agent(self.repository) as (app, policy):
                answer = await app["reviewer"].send(
                    "Review the latest commit for missing Python docstrings. First retrieve the "
                    "latest two commits with git_log, then inspect the newest with git_show, then "
                    "run find_missing_docstrings on the repository. Explain which function "
                    "introduced by the latest commit is missing a docstring. Include the full "
                    "latest commit hash, filename, function name, and line number. Do not modify anything."
                )
                completed = [(server, tool) for server, tool, success in policy.completed if success]
                for expected in [("git", "git_log"), ("git", "git_show"), ("analysis", "find_missing_docstrings")]:
                    self.assertIn(expected, completed, policy.completed)
                self.assertLess(completed.index(("git", "git_log")), completed.index(("git", "git_show")))
                for expected in (latest, "review.py", "needs_docs", "5"):
                    self.assertIn(expected, answer)
                print("\nLive Gemini review succeeded; completed tools:", completed)
                print(answer)
        self.assertEqual(snapshot(self.repository), before)


if __name__ == "__main__":
    unittest.main()
