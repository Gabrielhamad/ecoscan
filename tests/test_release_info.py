import subprocess
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from ecoscan.services import release_info as module


class ReleaseInfoTests(unittest.TestCase):
    def setUp(self):
        module.code_revision.cache_clear()
        self.addCleanup(module.code_revision.cache_clear)
        self.root = str(Path(module.__file__).resolve().parents[3])

    @patch.object(module.subprocess, "run")
    def test_returns_only_version_and_commit_and_caches_lookup(self, run):
        run.side_effect = [SimpleNamespace(stdout=self.root), SimpleNamespace(stdout="a" * 40)]
        expected = {"app_version": module.__version__, "code_revision": "a" * 40}
        self.assertEqual(module.release_info(), expected)
        self.assertEqual(module.release_info(), expected)
        self.assertEqual(run.call_count, 2)

    @patch.object(module.subprocess, "run")
    def test_parent_workspace_is_not_application_revision(self, run):
        run.return_value.stdout = str(Path(self.root).parent)
        self.assertIsNone(module.code_revision())
        self.assertEqual(run.call_count, 1)

    @patch.object(module.subprocess, "run")
    def test_invalid_revision_is_not_exposed(self, run):
        run.side_effect = [SimpleNamespace(stdout=self.root), SimpleNamespace(stdout="private/path")]
        self.assertIsNone(module.code_revision())

    @patch.object(module.subprocess, "run")
    def test_git_failure_does_not_block_the_application(self, run):
        for error in (OSError("secret"), subprocess.TimeoutExpired("git", 2),
                      subprocess.CalledProcessError(1, "git")):
            with self.subTest(error=type(error).__name__):
                module.code_revision.cache_clear()
                run.side_effect = error
                self.assertEqual(module.release_info(), {"app_version": module.__version__, "code_revision": None})
