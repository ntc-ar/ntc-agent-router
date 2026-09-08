"""Small, fail-closed client for zero-cost OpenRouter text completions.

This module deliberately has no configuration discovery or command-line entrypoint:
the caller supplies an API key for each operation and remains responsible for
deciding whether external work is allowed.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from email.utils import parsedate_to_datetime
import json
import re
import urllib.error
import urllib.request


BASE_URL = "https://openrouter.ai/api/v1"
TIMEOUT_SECONDS = 120
MAX_PROMPT_CHARS = 60_000
MAX_OUTPUT_TOKENS = 32_768
MAX_RETRY_AFTER_SECONDS = 3_600
_REQUIRED_PRICE_FIELDS = frozenset(("prompt", "completion"))
_SAFE_KEY_FIELDS = frozenset(("limit", "limit_remaining", "usage", "is_free_tier"))
_SAFE_CREDIT_FIELDS = frozenset(("total_credits", "total_usage", "remaining_credits"))
_EFFORTS = frozenset(("max", "xhigh", "high", "medium", "low", "minimal", "none"))
_USAGE_FIELDS = frozenset(("prompt_tokens", "completion_tokens", "total_tokens", "reasoning_tokens", "cost"))
_SECRET_PATTERNS = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----", re.I),
    re.compile(r"\b(?:api[_-]?key|password|secret|token)\s*[:=]\s*(?:['\"][^'\"]{12,}['\"]|[A-Za-z0-9._~-]{20,})", re.I),
    re.compile(r"\b(?:sk|rk)-[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._~-]{12,}\b", re.I),
)


class OpenRouterError(Exception):
    """A safe error which never includes an API key, prompt, or response body."""

    def __init__(self, code: str, message: str, retry_after: int | None = None, details: dict | None = None):
        self.code = code
        self.message = message
        self.retry_after = retry_after
        self.details = details or {}
        super().__init__(message)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _retry_after(headers) -> int | None:
    value = headers.get("Retry-After") if headers else None
    if not value:
        return None
    try:
        seconds = int(value)
    except (TypeError, ValueError):
        try:
            seconds = int((parsedate_to_datetime(value).astimezone(timezone.utc) - datetime.now(timezone.utc)).total_seconds())
        except (TypeError, ValueError, IndexError, OverflowError):
            return None
    return max(0, min(seconds, MAX_RETRY_AFTER_SECONDS))


def _number(value) -> Decimal | None:
    if isinstance(value, bool):
        return None
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return result if result.is_finite() else None


def _zero(value) -> bool:
    amount = _number(value)
    return amount is not None and amount == 0


def _request_json(endpoint: str, *, key: str | None = None, payload: dict | None = None) -> dict:
    if endpoint not in {"models", "key", "credits", "chat/completions"}:
        raise OpenRouterError("invalid_endpoint", "Invalid OpenRouter endpoint.")
    headers = {"Accept": "application/json"}
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    if key:
        headers["Authorization"] = "Bearer " + key
    request = urllib.request.Request(f"{BASE_URL}/{endpoint}", data=data, headers=headers,
                                     method="POST" if data is not None else "GET")
    try:
        opener = urllib.request.build_opener(_NoRedirect())
        with opener.open(request, timeout=TIMEOUT_SECONDS) as response:
            if response.geturl() != request.full_url:
                raise OpenRouterError("redirect", "OpenRouter redirected the request.")
            parsed = json.load(response)
    except OpenRouterError:
        raise
    except urllib.error.HTTPError as error:
        # Classify only known routing failures; never expose remote error text.
        details = {}
        try:
            message = json.loads(error.read(8192)).get("error", {}).get("message", "")
            if isinstance(message, str):
                lower = message.lower()
                if "data policy" in lower:
                    details["routing_failure"] = "no_provider_matching_data_policy"
                elif "no endpoints" in lower:
                    details["routing_failure"] = "no_eligible_endpoint"
        except (OSError, ValueError, TypeError, AttributeError):
            pass
        code = "rate_limited" if error.code == 429 else f"http_{error.code}"
        raise OpenRouterError(code, f"OpenRouter request failed with HTTP {error.code}.",
                              _retry_after(error.headers), details=details) from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise OpenRouterError("network_error", "OpenRouter network request failed.") from None
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
        raise OpenRouterError("invalid_response", "OpenRouter returned an invalid response.") from None
    if not isinstance(parsed, dict):
        raise OpenRouterError("invalid_response", "OpenRouter returned an unexpected response.")
    return parsed


def _model_record(item: object) -> dict | None:
    if not isinstance(item, dict):
        return None
    model_id = item.get("id")
    pricing = item.get("pricing")
    supported = item.get("supported_parameters")
    architecture = item.get("architecture")
    reasoning = item.get("reasoning")
    if (not isinstance(model_id, str) or not model_id or model_id.startswith("openrouter/")
            or (":" in model_id and not model_id.endswith(":free")) or not isinstance(pricing, dict)
            or not _REQUIRED_PRICE_FIELDS.issubset(pricing) or not all(_zero(value) for value in pricing.values())
            or not isinstance(supported, list) or not all(isinstance(value, str) for value in supported)
            or not isinstance(architecture, dict)):
        return None
    outputs = architecture.get("output_modalities")
    if not isinstance(outputs, list) or "text" not in outputs:
        return None
    context_length = item.get("context_length")
    if not isinstance(context_length, int) or isinstance(context_length, bool) or context_length <= 0:
        return None
    canonical_slug = item.get("canonical_slug")
    expected_canonical = model_id.removesuffix(":free")
    if canonical_slug != expected_canonical:
        canonical_slug = model_id
    efforts = None
    mandatory_reasoning = False
    if isinstance(reasoning, dict):
        advertised = reasoning.get("supported_efforts")
        if advertised is None:
            efforts = _EFFORTS
        elif isinstance(advertised, list) and all(isinstance(value, str) and value in _EFFORTS for value in advertised):
            efforts = frozenset(advertised)
        else:
            return None
        mandatory_reasoning = reasoning.get("mandatory") is True
    return {
        "id": model_id,
        "name": item.get("name") if isinstance(item.get("name"), str) else model_id,
        "description": item.get("description") if isinstance(item.get("description"), str) else "",
        "context_length": context_length,
        "supported_parameters": list(supported),
        "pricing": dict(pricing),
        "_canonical_slug": canonical_slug,
        "_reasoning_efforts": efforts,
        "_mandatory_reasoning": mandatory_reasoning,
    }


def _catalog() -> list[dict]:
    response = _request_json("models")
    data = response.get("data")
    if not isinstance(data, list):
        raise OpenRouterError("invalid_response", "OpenRouter returned an unexpected model catalog.")
    return [record for item in data if (record := _model_record(item)) is not None]


def free_models() -> list[dict]:
    """Return currently free, concrete, text-capable model records from `/models`."""
    fields = ("id", "name", "description", "context_length", "supported_parameters", "pricing")
    return [{**{field: record[field] for field in fields},
             "reasoning_efforts": sorted(record["_reasoning_efforts"]) if record["_reasoning_efforts"] is not None else None,
             "mandatory_reasoning": record["_mandatory_reasoning"]} for record in _catalog()]


def _safe_fields(source: object, names: frozenset[str], *, allow_boolean: frozenset[str] = frozenset(),
                 allow_null: frozenset[str] = frozenset()) -> dict:
    if not isinstance(source, dict):
        return {}
    result = {}
    for name in names:
        value = source.get(name)
        if name in allow_boolean and isinstance(value, bool):
            result[name] = value
        elif name in allow_null and name in source and value is None:
            result[name] = None
        elif isinstance(value, bool) or _number(value) is None:
            continue
        else:
            result[name] = value
    return result


def account_status(key: str) -> dict:
    """Return only non-sensitive quota and credit facts; credits may be unavailable."""
    _check_key(key)
    key_data = _request_json("key", key=key).get("data")
    result = {"quota": _safe_fields(key_data, _SAFE_KEY_FIELDS,
                                     allow_boolean=frozenset(("is_free_tier",)),
                                     allow_null=frozenset(("limit", "limit_remaining"))),
              "credits": {}, "credits_available": False}
    try:
        credits_data = _request_json("credits", key=key).get("data")
    except OpenRouterError as error:
        if error.code.startswith("http_") and error.code in {"http_401", "http_403", "http_404"}:
            return result
        raise
    result["credits"] = _safe_fields(credits_data, _SAFE_CREDIT_FIELDS)
    result["credits_available"] = True
    return result


def _check_key(key: str) -> None:
    if not isinstance(key, str) or not key.strip():
        raise OpenRouterError("invalid_key", "An OpenRouter API key is required.")


def _validate_prompt(prompt: str, max_tokens: int, record: dict, key: str) -> None:
    if not isinstance(prompt, str) or not prompt.strip():
        raise OpenRouterError("invalid_prompt", "Prompt must contain text.")
    if (not isinstance(max_tokens, int) or isinstance(max_tokens, bool) or max_tokens < 1
            or max_tokens > MAX_OUTPUT_TOKENS):
        raise OpenRouterError("invalid_max_tokens", "max_tokens is outside the allowed model limit.")
    if len(prompt) > MAX_PROMPT_CHARS:
        raise OpenRouterError("prompt_too_large", "Prompt exceeds the model input limit.")
    # Use a conservative UTF-8 byte bound; no provider tokenizer is installed.
    estimated_input_tokens = len(prompt.encode("utf-8")) + 512
    if estimated_input_tokens + max_tokens > record["context_length"]:
        raise OpenRouterError("prompt_too_large", "Prompt and requested output exceed the model context limit.")
    if key in prompt or any(pattern.search(prompt) for pattern in _SECRET_PATTERNS):
        raise OpenRouterError("sensitive_prompt", "Prompt appears to contain a secret.")


def generate(key: str, model: str, prompt: str, max_tokens: int = 8192,
             reasoning_effort: str | None = None) -> dict:
    """Generate exactly one completion after fresh free-model verification."""
    _check_key(key)
    if (not isinstance(model, str) or not model or model.startswith("openrouter/")
            or (":" in model and not model.endswith(":free"))):
        raise OpenRouterError("invalid_model", "Model must be a concrete catalog model.")
    records = _catalog()  # Always fresh: prices and availability can change.
    record = next((item for item in records if item["id"] == model), None)
    if record is None:
        raise OpenRouterError("nonfree_model", "Model is not a verified free text model.")
    _validate_prompt(prompt, max_tokens, record, key)
    if reasoning_effort is not None:
        supported_efforts = record["_reasoning_efforts"]
        if (not isinstance(reasoning_effort, str) or reasoning_effort not in _EFFORTS
                or supported_efforts is None or reasoning_effort not in supported_efforts
                or (reasoning_effort == "none" and record["_mandatory_reasoning"])):
            raise OpenRouterError("unsupported_reasoning", "Model does not support reasoning effort.")
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "stream": False,
        "plugins": [],
        "provider": {
            "max_price": {"prompt": 0, "completion": 0, "request": 0, "image": 0},
            "allow_fallbacks": False,
            "require_parameters": True,
            "data_collection": "deny",
        },
    }
    if reasoning_effort is not None:
        payload["reasoning"] = {"effort": reasoning_effort}
    response = _request_json("chat/completions", key=key, payload=payload)
    try:
        choice = response["choices"][0]
        content = choice["message"]["content"]
        finish_reason = choice["finish_reason"]
        actual_model = response["model"]
        provider = response["provider"]
        usage = response["usage"]
        cost = usage["cost"]
    except (KeyError, IndexError, TypeError):
        raise OpenRouterError("invalid_response", "OpenRouter returned an unexpected response.") from None
    accepted_models = {model, record["_canonical_slug"]}
    if actual_model not in accepted_models:
        raise OpenRouterError("model_mismatch", "OpenRouter returned a different model.")
    if not isinstance(provider, str) or not provider:
        raise OpenRouterError("invalid_response", "OpenRouter returned an unexpected response.")
    receipt = {"actual_model": actual_model, "provider": provider.replace(key, "[REDACTED]"),
               "usage": _sanitize_usage(usage), "finish_reason": finish_reason}
    if isinstance(content, str) and key in content:
        raise OpenRouterError("sensitive_response", "Provider response contained a credential.")
    if not isinstance(content, str) or not content.strip():
        raise OpenRouterError("empty_response", "OpenRouter returned no completion text.", details=receipt)
    if finish_reason != "stop":
        raise OpenRouterError("partial_response", "OpenRouter returned a truncated or incomplete completion.", details=receipt)
    if not _zero(cost):
        raise OpenRouterError("nonzero_cost", "OpenRouter reported a nonzero or unknown cost.")
    safe_usage = _sanitize_usage(usage)
    return {"content": content, "actual_model": actual_model, "provider": provider,
            "usage": safe_usage, "finish_reason": finish_reason, "reported_cost_usd": 0.0}


def _sanitize_usage(usage: object) -> dict:
    if not isinstance(usage, dict):
        raise OpenRouterError("invalid_response", "OpenRouter returned an unexpected response.")
    result = {}
    for name in _USAGE_FIELDS:
        value = _number(usage.get(name))
        if value is None or value < 0:
            continue
        if name == "cost":
            result[name] = float(value)
        elif value == value.to_integral_value():
            result[name] = int(value)
    return result
