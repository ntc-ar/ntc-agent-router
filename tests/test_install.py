import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch


SPEC = importlib.util.spec_from_file_location("installer", Path(__file__).parents[1] / "install.py")
installer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(installer)


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.repo = self.base / "repo"
        self.home = self.base / "home"
        self.skill = self.repo / "skills" / installer.NAME
        (self.skill / "references").mkdir(parents=True)
        (self.skill / "SKILL.md").write_text("---\nname: ntc-agent-router\n---\nVersion one\n")
        (self.skill / "references" / "routing.md").write_text("Routing rules\n")
        self.profiles = self.repo / "claude-agents"
        self.profiles.mkdir()
        (self.profiles / "ntc-worker.md").write_text("---\nname: ntc-worker\n---\nWork\n")

    def run_install(self, **kwargs):
        return installer.install(self.repo, home=self.home, **kwargs)

    def destination(self, host="codex"):
        return self.home / f".{host}" / "skills" / installer.NAME

    def assert_no_staging(self):
        self.assertFalse(list(self.home.glob(".*/.ntc-agent-router-*")))

    def test_dry_run_does_not_create_home(self):
        messages = self.run_install(target="all", dry_run=True)
        self.assertFalse(self.home.exists())
        self.assertEqual(sum(line.startswith("Would install:") for line in messages), 3)

    def test_install_all_leaves_unrelated_configuration_untouched(self):
        untouched = {}
        for host in ("codex", "claude"):
            root = self.home / f".{host}"
            root.mkdir(parents=True)
            for name in ("auth.json", "config.toml", "settings.json", "AGENTS.md", "CLAUDE.md"):
                path = root / name
                path.write_text("Keep me exactly\n")
                untouched[path] = (path.read_bytes(), path.stat().st_mtime_ns)
            other = root / "skills" / "other-skill" / "SKILL.md"
            other.parent.mkdir(parents=True)
            other.write_text("An unrelated skill\n")
            untouched[other] = (other.read_bytes(), other.stat().st_mtime_ns)
        self.run_install(target="all")
        for host in ("codex", "claude"):
            self.assertEqual(installer.contents(self.skill), installer.contents(self.destination(host)))
        self.assertEqual((self.profiles / "ntc-worker.md").read_bytes(),
                         (self.home / ".claude/agents/ntc-worker.md").read_bytes())
        for path, expected in untouched.items():
            self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns), expected)
        self.assert_no_staging()

    def test_update_preserves_old_tree_outside_discovery(self):
        self.run_install()
        dest = self.destination()
        (dest / "local-note.txt").write_text("Preserve this in backup\n")
        before = installer.contents(dest)
        (self.skill / "SKILL.md").write_text("Version two\n")
        self.run_install()
        self.assertEqual(installer.contents(dest), installer.contents(self.skill))
        backups = list((self.home / ".codex/backups/ntc-agent-router").glob("*/skills/ntc-agent-router"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(installer.contents(backups[0]), before)
        self.assertEqual(list(dest.parent.iterdir()), [dest])
        self.assert_no_staging()

    def test_identical_install_performs_no_writes(self):
        self.run_install(target="all")
        before = {p: p.stat().st_mtime_ns for p in self.home.rglob("*")}
        with patch.object(installer.tempfile, "mkdtemp", side_effect=AssertionError("Unexpected write")):
            messages = self.run_install(target="all")
        self.assertTrue(all(line.startswith("Unchanged:") for line in messages))
        self.assertEqual(before, {p: p.stat().st_mtime_ns for p in self.home.rglob("*")})

    def test_home_override_ignores_environment(self):
        env = {"CODEX_HOME": str(self.base / "custom-codex"),
               "CLAUDE_CONFIG_DIR": str(self.base / "custom-claude")}
        self.run_install(target="all", environ=env)
        self.assertTrue(self.destination().is_dir())
        self.assertTrue(self.destination("claude").is_dir())
        self.assertFalse((self.base / "custom-codex").exists())
        self.assertFalse((self.base / "custom-claude").exists())

    def test_environment_directories_and_default_home(self):
        env = {"CODEX_HOME": str(self.base / "custom-codex"),
               "CLAUDE_CONFIG_DIR": str(self.base / "custom-claude")}
        installer.install(self.repo, target="all", environ=env)
        for directory in env.values():
            self.assertTrue((Path(directory) / "skills" / installer.NAME).is_dir())
        with patch.object(installer.Path, "home", return_value=self.home):
            installer.install(self.repo, target="all", environ={})
        self.assertTrue(self.destination().is_dir())
        self.assertTrue(self.destination("claude").is_dir())

    def test_optional_profiles_can_be_absent(self):
        (self.profiles / "ntc-worker.md").unlink()
        self.profiles.rmdir()
        self.run_install(target="all")
        self.assertFalse((self.home / ".claude/agents").exists())

    def test_late_invalid_target_fails_before_any_install(self):
        blocked = self.home / ".claude/skills"
        blocked.mkdir(parents=True)
        (blocked / installer.NAME).write_text("An unexpected regular file\n")
        with self.assertRaisesRegex(ValueError, "wrong type"):
            self.run_install(target="all")
        self.assertFalse((self.home / ".codex").exists())

    def test_failed_copy_does_not_change_existing_targets(self):
        self.run_install(target="all")
        before = {host: installer.contents(self.destination(host)) for host in ("codex", "claude")}
        (self.skill / "SKILL.md").write_text("Updated\n")
        real_copy = installer.shutil.copytree
        calls = 0

        def fail_second_copy(*args, **kwargs):
            nonlocal calls
            # copytree recurses through its public name; count only source skill roots.
            if Path(args[0]) == self.skill:
                calls += 1
                if calls == 2:
                    raise OSError("Injected copy failure")
            return real_copy(*args, **kwargs)

        with patch.object(installer.shutil, "copytree", side_effect=fail_second_copy):
            with self.assertRaisesRegex(OSError, "Injected copy failure"):
                self.run_install(target="all")
        for host in before:
            self.assertEqual(installer.contents(self.destination(host)), before[host])
        self.assert_no_staging()

    def test_failed_replace_rolls_back_already_committed_target(self):
        self.run_install(target="all")
        before = {host: installer.contents(self.destination(host)) for host in ("codex", "claude")}
        (self.skill / "SKILL.md").write_text("Updated\n")
        real_replace = installer.os.replace
        calls = 0

        def fail_fourth_replace(src, dest):
            nonlocal calls
            calls += 1
            if calls == 4:
                raise OSError("Injected replacement failure")
            return real_replace(src, dest)

        with patch.object(installer.os, "replace", side_effect=fail_fourth_replace):
            with self.assertRaisesRegex(OSError, "Injected replacement failure"):
                self.run_install(target="all")
        self.assertGreater(calls, 4)
        for host in before:
            self.assertEqual(installer.contents(self.destination(host)), before[host])
        self.assert_no_staging()

    def make_link(self, path, destination, directory=True):
        try:
            path.symlink_to(destination, target_is_directory=directory)
        except OSError:
            if os.name != "nt" or not directory:
                self.skipTest("Creating symlinks is not permitted on this system")
            # Both paths are generated by TemporaryDirectory, never user shell text.
            result = subprocess.run(["cmd", "/c", "mklink", "/J", str(path), str(destination)],
                                    capture_output=True, text=True)
            if result.returncode:
                self.skipTest("Creating junctions is not permitted on this system")
        def remove_link():
            if path.is_symlink():
                path.unlink()
            elif path.exists() and getattr(path.lstat(), "st_file_attributes", 0) & 0x400:
                path.rmdir()

        self.addCleanup(remove_link)
        return remove_link

    def test_rejects_linked_target_and_ancestor(self):
        external = self.base / "external"
        external.mkdir()
        (external / "keep.txt").write_text("Unchanged\n")
        for location in (self.home / ".codex", self.destination()):
            with self.subTest(location=location):
                location.parent.mkdir(parents=True, exist_ok=True)
                remove_link = self.make_link(location, external)
                try:
                    with self.assertRaisesRegex(ValueError, "symlink or junction"):
                        self.run_install()
                    self.assertEqual(list(external.iterdir()), [external / "keep.txt"])
                finally:
                    remove_link()

    def test_rejects_source_link_before_writing(self):
        external = self.base / "external"
        external.mkdir()
        (external / "secret.txt").write_text("Do not copy\n")
        self.make_link(self.skill / "linked", external)
        with self.assertRaisesRegex(ValueError, "symlink or junction"):
            self.run_install()
        self.assertFalse(self.home.exists())

    def test_rejects_linked_backup_ancestor(self):
        self.run_install()
        external = self.base / "external"
        external.mkdir()
        self.make_link(self.home / ".codex/backups", external)
        before = installer.contents(self.destination())
        (self.skill / "SKILL.md").write_text("Updated\n")
        with self.assertRaisesRegex(ValueError, "symlink or junction"):
            self.run_install()
        self.assertEqual(installer.contents(self.destination()), before)
        self.assertEqual(list(external.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
