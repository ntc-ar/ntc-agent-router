import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch
import urllib.error


SPEC = importlib.util.spec_from_file_location(
    "openrouter_client", Path(__file__).parents[1] / "external_workers" / "openrouter_client.py")
client = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(client)


MODEL = {
    "id": "acme/free-text",
    "name": "Free Text",
    "description": "A test model",
    "context_length": 8192,
    "supported_parameters": ["max_tokens", "reasoning_effort"],
    "canonical_slug": "acme/free-text",
    "reasoning": {"supported_efforts": ["high", "low"], "mandatory": False},
    "architecture": {"output_modalities": ["text"]},
    "pricing": {"prompt": "0", "completion": "0", "request": "0", "image": "0"},
}


class OpenRouterClientTests(unittest.TestCase):
    def test_unknown_or_nonfinite_prices_never_reach_generation(self):
        for value in (None, True, "NaN", "Infinity", "-1", "0.001", "unknown"):
            record = {**MODEL, "pricing": {"prompt": "0", "completion": value}}
            with self.subTest(value=value), patch.object(client, "_request_json", return_value={"data": [record]}) as request:
                with self.assertRaises(client.OpenRouterError):
                    client.generate("credential", MODEL["id"], "Produce a short function", 64)
                self.assertEqual(request.call_count, 1)
                self.assertEqual(request.call_args.args, ("models",))

    def test_free_models_filters_aliases_paid_and_non_text_entries(self):
        paid = {**MODEL, "id": "acme/paid", "pricing": {**MODEL["pricing"], "completion": "0.1"}}
        alias = {**MODEL, "id": "openrouter/free"}
        image = {**MODEL, "id": "acme/image", "architecture": {"output_modalities": ["image"]}}
        with patch.object(client, "_request_json", return_value={"data": [MODEL, paid, alias, image]}):
            self.assertEqual([item["id"] for item in client.free_models()], ["acme/free-text"])

    def test_concrete_free_suffix_is_allowed_but_router_alias_is_not(self):
        free_variant = {**MODEL, "id": "acme/free-text:free"}
        with patch.object(client, "_request_json", return_value={"data": [free_variant]}):
            self.assertEqual(client.free_models()[0]["id"], "acme/free-text:free")

    def test_generate_defaults_to_deny_and_sends_locked_zero_cost_payload(self):
        response = {"model": "acme/free-text", "provider": "acme", "choices": [{"finish_reason": "stop", "message": {"content": "done"}}], "usage": {"cost": "0", "prompt_tokens": 2}}
        with patch.object(client, "_request_json", side_effect=[{"data": [MODEL]}, response]) as request:
            result = client.generate("key", "acme/free-text", "safe request", 32, "low")
        self.assertEqual(result["content"], "done")
        payload = request.call_args_list[1].kwargs["payload"]
        self.assertEqual(payload["provider"]["max_price"], {"prompt": 0, "completion": 0, "request": 0, "image": 0})
        self.assertFalse(payload["provider"]["allow_fallbacks"])
        self.assertEqual(payload["provider"]["data_collection"], "deny")
        self.assertEqual(payload["plugins"], [])
        self.assertEqual(payload["reasoning"], {"effort": "low"})
        self.assertEqual(result["usage"], {"cost": 0.0, "prompt_tokens": 2})
        self.assertEqual(result["data_collection"], "deny")

    def test_generate_allows_explicit_data_collection_without_relaxing_price_restrictions(self):
        response = {"model": "acme/free-text", "provider": "acme", "choices": [{"finish_reason": "stop", "message": {"content": "done"}}], "usage": {"cost": 0}}
        with patch.object(client, "_request_json", side_effect=[{"data": [MODEL]}, response]) as request:
            result = client.generate("key", "acme/free-text", "safe request", 32, data_collection="allow")
        provider = request.call_args_list[1].kwargs["payload"]["provider"]
        self.assertEqual(provider["data_collection"], "allow")
        self.assertEqual(provider["max_price"], {"prompt": 0, "completion": 0, "request": 0, "image": 0})
        self.assertFalse(provider["allow_fallbacks"])
        self.assertEqual(request.call_args_list[1].kwargs["payload"]["plugins"], [])
        self.assertEqual(result["data_collection"], "allow")

    def test_generate_rejects_invalid_data_collection_before_network(self):
        with patch.object(client, "_request_json") as request:
            with self.assertRaises(client.OpenRouterError) as caught:
                client.generate("key", "acme/free-text", "safe request", 32, data_collection="maybe")
        self.assertEqual(caught.exception.code, "invalid_data_collection")
        request.assert_not_called()

    def test_generate_rejects_partial_and_nonzero_results(self):
        partial = {"model": "acme/free-text", "provider": "acme", "choices": [{"finish_reason": "length", "message": {"content": "part"}}], "usage": {"cost": 0}}
        with patch.object(client, "_request_json", side_effect=[{"data": [MODEL]}, partial]):
            with self.assertRaisesRegex(client.OpenRouterError, "incomplete") as caught:
                client.generate("key", "acme/free-text", "safe request", 32)
        self.assertEqual(caught.exception.code, "partial_response")
        self.assertEqual(caught.exception.details["finish_reason"], "length")
        self.assertEqual(caught.exception.details["usage"]["cost"], 0)

        charged = {**partial, "choices": [{"finish_reason": "stop", "message": {"content": "done"}}],
                   "usage": {"cost": "0.0001"}}
        with patch.object(client, "_request_json", side_effect=[{"data": [MODEL]}, charged]):
            with self.assertRaises(client.OpenRouterError) as caught:
                client.generate("key", "acme/free-text", "safe request", 32)
        self.assertEqual(caught.exception.code, "nonzero_cost")
        self.assertEqual(caught.exception.details["data_collection"], "deny")

    def test_http_error_is_safe_and_has_bounded_retry_after(self):
        error = urllib.error.HTTPError("https://openrouter.ai/api/v1/models", 429, "bad", {"Retry-After": "999999"}, None)
        class Opener:
            def open(self, request, timeout):
                raise error
        with patch.object(client.urllib.request, "build_opener", return_value=Opener()):
            with self.assertRaises(client.OpenRouterError) as caught:
                client._request_json("models", key="super-secret")
        self.assertEqual(caught.exception.code, "rate_limited")
        self.assertEqual(caught.exception.retry_after, client.MAX_RETRY_AFTER_SECONDS)
        self.assertNotIn("super-secret", str(caught.exception))
        error.close()

    def test_redirect_is_not_followed(self):
        self.assertIsNone(client._NoRedirect().redirect_request(None, None, 302, "", {}, "https://evil.invalid"))

    def test_credits_access_failure_is_unavailable_not_quota(self):
        denied = client.OpenRouterError("http_403", "OpenRouter request failed with HTTP 403.")
        with patch.object(client, "_request_json", side_effect=[{"data": {"limit_remaining": 4, "label": "nope"}}, denied]):
            status = client.account_status("key")
        self.assertEqual(status, {"quota": {"limit_remaining": 4}, "credits": {}, "credits_available": False})

    def test_limits_effort_and_secret_detection_are_precise(self):
        ordinary_code = "def f(token: str, password=value): return token"
        with patch.object(client, "_request_json", side_effect=[{"data": [MODEL]},
              {"model": "acme/free-text", "provider": "acme", "choices": [{"finish_reason": "stop", "message": {"content": "ok"}}], "usage": {"cost": 0}}]):
            client.generate("real-key-not-in-prompt", "acme/free-text", ordinary_code, 32)
        with patch.object(client, "_request_json", return_value={"data": [MODEL]}):
            with self.assertRaisesRegex(client.OpenRouterError, "secret"):
                client.generate("real-key-not-in-prompt", "acme/free-text", "sk-or-v1-abcdefghijklmnopqrstuvwxyz", 32)
            with self.assertRaises(client.OpenRouterError) as caught:
                client.generate("real-key-not-in-prompt", "acme/free-text", "safe", 32, "invented")
        self.assertEqual(caught.exception.code, "unsupported_reasoning")

    def test_context_budget_and_canonical_response_are_validated(self):
        variant = {**MODEL, "id": "acme/free-text:free", "canonical_slug": "acme/free-text", "context_length": 60_000}
        response = {"model": "acme/free-text", "provider": "acme", "choices": [{"finish_reason": "stop", "message": {"content": "ok"}}], "usage": {"cost": 0, "remote_debug": "discard"}}
        with patch.object(client, "_request_json", side_effect=[{"data": [variant]}, response]):
            client.generate("key-value", "acme/free-text:free", "x" * 21_000, 32_768)
        with patch.object(client, "_request_json", return_value={"data": [variant]}):
            with self.assertRaises(client.OpenRouterError) as caught:
                client.generate("key-value", "acme/free-text:free", "x" * 30_000, 32_768)
        self.assertEqual(caught.exception.code, "prompt_too_large")

    def test_account_status_keeps_boolean_and_unknown_limits(self):
        with patch.object(client, "_request_json", side_effect=[
                {"data": {"limit": None, "limit_remaining": None, "is_free_tier": True, "label": "hidden"}},
                {"data": {"total_credits": 4}},
        ]):
            status = client.account_status("key")
        self.assertEqual(status["quota"], {"limit": None, "limit_remaining": None, "is_free_tier": True})


if __name__ == "__main__":
    unittest.main()
