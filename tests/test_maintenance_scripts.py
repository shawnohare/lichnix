"""Exercise maintenance workflows with fake tools; never fetch/update gems."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_BIN = Path(os.environ.get("LICHNIX_MAINTENANCE_BIN", str(ROOT / "bin")))
SCRIPTS = ("update-lich-dependencies",)


class MaintenanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="lich-maintenance-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.repo = self.base / "repository with spaces"
        (self.repo / "bin").mkdir(parents=True)
        (self.repo / "nix/gems").mkdir(parents=True)
        for name in SCRIPTS:
            shutil.copy(SCRIPT_BIN / name, self.repo / "bin" / name)
        self.source = self.base / "pinned source"
        self.source.mkdir()
        (self.source / "Gemfile").write_text("pinned upstream Gemfile\n")
        (self.source / "Gemfile").chmod(0o444)
        (self.source / "Gemfile.lock").write_text("pinned upstream lockfile\n")
        (self.source / "Gemfile.lock").chmod(0o444)
        self.log = self.base / "commands.jsonl"
        fake_bin = self.base / "tools"
        fake_bin.mkdir()
        mock = '''#!/usr/bin/env python3
import json, os, pathlib, subprocess, sys
name = pathlib.Path(sys.argv[0]).name
args = sys.argv[1:]
with open(os.environ["COMMAND_LOG"], "a") as log:
    log.write(json.dumps([name, args, os.getcwd()]) + "\\n")
if name == "nix":
    if args[0] == "eval":
        print(os.environ["PINNED_SOURCE"])
    elif args[0] == "develop":
        sys.exit(subprocess.call(args[args.index("--command") + 1:]))
elif name == "bundix" and os.environ.get("FAIL_BUNDIX"):
    sys.exit(23)
'''
        for name in ("nix", "bundix"):
            tool = fake_bin / name
            tool.write_text(mock)
            tool.chmod(0o755)
        self.env = dict(os.environ, HOME=str(self.base),
                        PATH=f"{fake_bin}:{os.environ['PATH']}",
                        COMMAND_LOG=str(self.log), PINNED_SOURCE=str(self.source))

    def run_helper(self, name, *args):
        # Run from outside the repository to verify script-relative paths.
        return subprocess.run([str(self.repo / "bin" / name), *args],
                              cwd=self.base, env=self.env, capture_output=True,
                              text=True, timeout=30)

    def commands(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()]

    def test_regenerate_uses_upstream_files_without_resolving_versions(self):
        result = self.run_helper("update-lich-dependencies")
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = self.commands()
        self.assertEqual([c[0] for c in calls],
                         ["nix", "nix", "nix", "bundix", "nix", "nix", "nix"])
        self.assertEqual(calls[0][1], ["flake", "update", "lich-src"])
        self.assertEqual(calls[3][1], [
            f"--gemfile={self.source}/Gemfile",
            f"--lockfile={self.source}/Gemfile.lock",
            f"--gemset={self.repo}/nix/gems/gemset.nix",
        ])
        self.assertTrue(all(c[2] == str(self.repo) for c in calls))
        self.assertEqual(calls[4][1], ["build", ".#ruby-lich"])
        self.assertEqual(calls[5][1], ["build", "--no-link", ".#lich-development-gems"])
        self.assertEqual(calls[6][1], ["flake", "check"])
        self.assertFalse((self.repo / "nix/gems/Gemfile").exists())
        self.assertEqual((self.source / "Gemfile.lock").read_text(),
                         "pinned upstream lockfile\n")

    def test_targeted_updates_are_rejected_before_running_tools(self):
        result = self.run_helper("update-lich-dependencies", "sqlite3")
        self.assertEqual(result.returncode, 2)
        self.assertIn("edit the release tag", result.stderr)
        self.assertFalse(self.log.exists())

    def test_help_does_not_run_tools(self):
        for option in ("--help", "-h"):
            result = self.run_helper("update-lich-dependencies", option)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Usage:", result.stdout)
            self.assertFalse(self.log.exists())

    def test_failed_generation_stops_builds(self):
        self.env["FAIL_BUNDIX"] = "1"
        result = self.run_helper("update-lich-dependencies")
        self.assertEqual(result.returncode, 23)
        self.assertEqual([c[0] for c in self.commands()], ["nix", "nix", "nix", "bundix"])
        self.assertNotIn("Review and commit", result.stdout)


if __name__ == "__main__":
    unittest.main()
