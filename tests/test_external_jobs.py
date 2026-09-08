"""Local worker invariants. No credentials, model calls, or real worker processes."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from external_workers import jobs
from external_workers.openrouter_client import OpenRouterError


class JobsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.config = self.root / "config.toml"
        self.config.write_text("enabled = true\nmax_parallel = 1\n", encoding="utf-8")
        for name, value in (("STATE", self.root / "state"), ("CONFIG", self.config)):
            p = patch.object(jobs, name, value)
            p.start()
            self.addCleanup(p.stop)
        for name, value in (("load_key", "test-key"), ("subprocess.Popen", None)):
            p = patch(f"external_workers.jobs.{name}", return_value=value)
            p.start()
            self.addCleanup(p.stop)

    def start(self):
        return jobs.start_task("Write a Python addition function.", "vendor/code:free")["task_id"]

    def test_disabled_never_dispatches(self):
        self.config.write_text("enabled = false\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "disabled"):
            self.start()
        jobs.subprocess.Popen.assert_not_called()

    def test_concurrency_and_success_artifact(self):
        task_id = self.start()
        with self.assertRaisesRegex(ValueError, "limit"):
            self.start()
        response = {"content": "def add(a, b): return a + b", "actual_model": "vendor/code:free",
                    "provider": "example", "usage": {}, "finish_reason": "stop", "reported_cost_usd": 0}
        with patch.object(jobs.client, "generate", return_value=response):
            jobs.run_task(task_id)
        result = jobs.read_task(task_id)
        self.assertEqual(result["status"], "succeeded")
        self.assertNotIn("content", result)
        self.assertTrue(Path(result["output_path"]).exists())
        self.assertFalse((jobs.task_dir(task_id) / "request.json").exists())

    def test_cancelled_before_run_makes_no_request(self):
        task_id = self.start()
        jobs.cancel_task(task_id)
        with patch.object(jobs.client, "generate") as generate:
            jobs.run_task(task_id)
            generate.assert_not_called()
        self.assertEqual(jobs.read_task(task_id)["status"], "cancelled")
        self.assertFalse((jobs.task_dir(task_id) / "request.json").exists())

    def test_rate_limit_no_retry_and_shared_cooldown(self):
        task_id = self.start()
        with patch.object(jobs.client, "generate", side_effect=OpenRouterError("rate_limited", "HTTP 429", 120)) as generate:
            jobs.run_task(task_id)
            self.assertEqual(generate.call_count, 1)
        self.assertEqual(jobs.read_task(task_id)["code"], "rate_limited")
        with self.assertRaisesRegex(ValueError, "cooling down"):
            self.start()

    def test_context_boundary_and_secret_rejection(self):
        (self.root / "code.py").write_text("print('hello')", encoding="utf-8")
        (self.root / ".env").write_text("CREDENTIAL=hidden", encoding="utf-8")
        for name in ("../outside.py", ".env", str(self.root / "code.py")):
            with self.assertRaises(ValueError):
                jobs.prompt_with_context("Review", str(self.root), [name], 1000)
        prompt = jobs.prompt_with_context("Review", str(self.root), ["code.py"], 1000)
        self.assertIn("print('hello')", prompt)
        with self.assertRaises(ValueError):
            jobs.prompt_with_context("secret " + "sk-or-v1-" + "a" * 40, "", [], 1000)

    def test_symlink_context_is_rejected(self):
        target = self.root / "target.py"
        target.write_text("hello", encoding="utf-8")
        link = self.root / "link.py"
        try:
            link.symlink_to(target)
        except OSError:
            self.skipTest("Symlink creation is unavailable on this host.")
        with self.assertRaisesRegex(ValueError, "Symlink"):
            jobs.prompt_with_context("Review", str(self.root), ["link.py"], 1000)

    def test_refresh_diff_and_preserve_good_snapshot_on_empty(self):
        record = {"id": "vendor/code:free", "description": "Code", "pricing": {"prompt": "0", "completion": "0"}}
        with patch.object(jobs.client, "free_models", return_value=[record]):
            first = jobs.refresh_models()
            second = jobs.refresh_models()
        self.assertEqual(first["added"], [record["id"]])
        self.assertEqual(second["added"], [])
        self.assertEqual(second["changed"], [])
        with patch.object(jobs.client, "free_models", return_value=[]):
            with self.assertRaises(ValueError):
                jobs.refresh_models()
        self.assertEqual(json.loads((jobs.STATE / "free-models.json").read_text())["models"], [record])

    def test_model_preferences_and_routing_failure_are_visible(self):
        self.config.write_text('enabled = true\n[model_weights]\n"vendor/code:free" = 90\n', encoding="utf-8")
        task_id = self.start()
        error = OpenRouterError("http_404", "HTTP 404", details={
            "routing_failure": "no_provider_matching_data_policy"})
        with patch.object(jobs.client, "generate", side_effect=error):
            jobs.run_task(task_id)
        records = [{"id": "vendor/code:free"}, {"id": "vendor/new:free"}]
        with patch.object(jobs.client, "free_models", return_value=records):
            models = jobs.models()
        self.assertEqual((models[0]["weight"], models[0]["weight_source"]), (90, "configured"))
        self.assertEqual(models[0]["last_local_result"]["routing_failure"],
                         "no_provider_matching_data_policy")
        self.assertEqual((models[1]["weight"], models[1]["weight_source"]), (50, "default"))
        self.assertIsNone(models[1]["last_local_result"])

    def test_default_zero_allows_only_explicit_models(self):
        self.config.write_text('enabled = true\n[model_weights]\n"*" = 0\n'
                               '"vendor/code:free" = 100\n', encoding="utf-8")
        records = [{"id": "vendor/code:free"}, {"id": "vendor/new:free"}]
        with patch.object(jobs.client, "free_models", return_value=records):
            models = jobs.models()
        self.assertEqual([(m["weight"], m["weight_source"]) for m in models],
                         [(100, "configured"), (0, "configured_default")])
        with self.assertRaisesRegex(ValueError, "disabled"):
            jobs.start_task("Write a function", "vendor/new:free")
        jobs.load_key.assert_not_called()
        jobs.subprocess.Popen.assert_not_called()
        task_id = self.start()
        response = {"content": "def add(a, b): return a + b"}
        with patch.object(jobs.client, "generate", return_value=response) as generate:
            jobs.run_task(task_id)
        generate.assert_called_once()
        self.assertEqual(jobs.read_task(task_id)["status"], "succeeded")

    def test_queued_model_is_rechecked_before_external_dispatch(self):
        task_id = self.start()
        self.config.write_text('enabled = true\n[model_weights]\n"*" = 0\n'
                               '"vendor/other:free" = 100\n', encoding="utf-8")
        jobs.load_key.reset_mock()
        with patch.object(jobs.client, "generate") as generate:
            jobs.run_task(task_id)
        generate.assert_not_called()
        jobs.load_key.assert_not_called()
        result = jobs.read_task(task_id)
        self.assertEqual((result["status"], result["code"]), ("failed", "model_disabled"))
        self.assertFalse((jobs.task_dir(task_id) / "request.json").exists())

    def allow_project(self, root):
        self.config.write_text('enabled = true\n[project_data_collection]\n'
                               + json.dumps(root.as_posix()) + ' = "allow"\n', encoding="utf-8")

    def test_project_policy_defaults_and_directory_boundaries(self):
        project = self.root / "game"
        child = project / "src"
        private = project / "private"
        sibling = self.root / "game-client"
        for path in (child, private, sibling):
            path.mkdir(parents=True)
        self.allow_project(project)
        with self.config.open("a", encoding="utf-8") as f:
            f.write(json.dumps(private.as_posix()) + ' = "deny"\n')
        self.assertEqual(jobs.project_policy()["data_collection"], "deny")
        self.assertEqual(jobs.project_policy(str(child))["data_collection"], "allow")
        self.assertEqual(jobs.project_policy(str(private))["data_collection"], "deny")
        self.assertEqual(jobs.project_policy(str(sibling))["data_collection"], "deny")
        self.assertEqual(jobs.project_policy(str(project / ".." / "game-client"))["data_collection"], "deny")
        for workspace in ("relative", str(self.root / "missing")):
            with self.assertRaises(ValueError):
                jobs.project_policy(workspace)

    def test_only_local_config_can_authorize_data_collection(self):
        (self.root / ".ntc-openrouter.toml").write_text('data_collection = "allow"', encoding="utf-8")
        self.assertEqual(jobs.project_policy(str(self.root))["data_collection"], "deny")
        for setting in ('project_data_collection = true',
                        '[project_data_collection]\n"relative" = "allow"',
                        '[project_data_collection]\n' + json.dumps(self.root.as_posix()) + ' = "invalid"'):
            self.config.write_text(setting, encoding="utf-8")
            with self.assertRaises(ValueError):
                jobs.settings()

    def test_project_permission_applies_and_cannot_cross_context_boundary(self):
        project = self.root / "game"
        project.mkdir()
        self.allow_project(project)
        (self.root / "private.py").write_text("private code", encoding="utf-8")
        with self.assertRaises(ValueError):
            jobs.start_task("Review", "vendor/code:free", str(project), ["../private.py"])
        task_id = jobs.start_task("Write a function", "vendor/code:free", str(project))["task_id"]
        error = OpenRouterError("http_404", "HTTP 404", details={
            "routing_failure": "no_provider_matching_data_policy"})
        with patch.object(jobs.client, "generate", side_effect=error) as generate:
            jobs.run_task(task_id)
        self.assertEqual(generate.call_args.kwargs["data_collection"], "allow")
        self.assertNotIn("workspace", generate.call_args.kwargs)
        self.assertEqual(jobs.read_task(task_id)["data_collection"], "allow")
        with patch.object(jobs.client, "free_models", return_value=[{"id": "vendor/code:free"}]):
            self.assertIsNone(jobs.models()[0]["last_local_result"])
            self.assertEqual(jobs.models(str(project))[0]["last_local_result"]["code"], "http_404")

    def test_queued_project_permission_can_only_become_stricter(self):
        self.allow_project(self.root)
        task_id = jobs.start_task("Write a function", "vendor/code:free", str(self.root))["task_id"]
        self.config.write_text("enabled = true\n", encoding="utf-8")
        with patch.object(jobs.client, "generate", side_effect=OpenRouterError("http_404", "HTTP 404")) as generate:
            jobs.run_task(task_id)
        self.assertEqual(generate.call_args.kwargs["data_collection"], "deny")
        task_id = jobs.start_task("Write a function", "vendor/code:free", str(self.root))["task_id"]
        self.allow_project(self.root)
        with patch.object(jobs.client, "generate", side_effect=OpenRouterError("http_404", "HTTP 404")) as generate:
            jobs.run_task(task_id)
        self.assertEqual(generate.call_args.kwargs["data_collection"], "deny")


if __name__ == "__main__":
    unittest.main()
