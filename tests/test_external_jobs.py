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
        self.root = Path(self.temp.name)
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


if __name__ == "__main__":
    unittest.main()
