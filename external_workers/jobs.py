"""Bounded, durable text-generation jobs shared by local MCP sessions."""

import json
from contextlib import contextmanager
import os
from pathlib import Path
import re
import sqlite3
import stat
import subprocess
import sys
import threading
import time
import tomllib
import uuid

from .credentials import load_key
from . import openrouter_client as client

CONFIG = Path.home() / ".config/ntc-openrouter/config.toml"
STATE = Path.home() / ".local/share/ntc-openrouter"
DEFAULTS = dict(enabled=False, max_parallel=2, requests_per_minute=10,
                daily_request_limit=50, max_tokens=8192, max_context_chars=60000,
                model_weights={}, project_data_collection={})
SECRET = re.compile(r"sk-[A-Za-z0-9_-]{12,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|"
                    r"(?i:Bearer\s+[A-Za-z0-9_.-]{16,})")


def settings():
    data = tomllib.loads(CONFIG.read_text(encoding="utf-8")) if CONFIG.exists() else {}
    if set(data) - DEFAULTS.keys():
        raise ValueError("Unknown external worker configuration key.")
    result = DEFAULTS | data
    if type(result["enabled"]) is not bool:
        raise ValueError("enabled must be a boolean.")
    for name, maximum in (("max_parallel", 4), ("requests_per_minute", 20),
                          ("daily_request_limit", 1000), ("max_tokens", 32768),
                          ("max_context_chars", 60000)):
        if type(result[name]) is not int or not 1 <= result[name] <= maximum:
            raise ValueError(f"Invalid {name}.")
    weights = result["model_weights"]
    if not isinstance(weights, dict) or any(
        not isinstance(k, str) or not k or type(v) is not int or not 0 <= v <= 100
        for k, v in weights.items()
    ):
        raise ValueError("model_weights must map model IDs to integer priorities from 0 to 100.")
    policies = result["project_data_collection"]
    if not isinstance(policies, dict) or any(
        not isinstance(k, str) or not Path(k).is_absolute() or ".." in Path(k).parts
        or v not in ("allow", "deny") for k, v in policies.items()
    ):
        raise ValueError("project_data_collection must map absolute project paths to allow or deny.")
    return result


def workspace_root(workspace):
    root = Path(workspace)
    if not root.is_absolute() or not root.is_dir():
        raise ValueError("Workspace must be an existing absolute directory.")
    for part in (root, *root.parents):
        info = part.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ValueError("Symlink and junction workspaces are not supported.")
    return root.resolve()


def project_policy(workspace="", config=None):
    config = settings() if config is None else config
    if not workspace:
        return {"workspace": "", "project_root": None, "data_collection": "deny"}
    root = workspace_root(workspace)
    matches = [(Path(path), policy) for path, policy in config["project_data_collection"].items()
               if root.is_relative_to(Path(path))]
    # A more specific project rule wins; deny wins duplicate/case-equivalent paths.
    match = max(matches, key=lambda m: (len(m[0].parts), m[1] == "deny"), default=None)
    return {"workspace": str(root), "project_root": str(match[0]) if match else None,
            "data_collection": match[1] if match else "deny"}


@contextmanager
def database():
    STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    db = sqlite3.connect(STATE / "jobs.sqlite3", timeout=15)
    db.row_factory = sqlite3.Row
    db.execute("CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, created REAL, updated REAL, "
               "status TEXT, model TEXT, metadata TEXT)")
    db.execute("CREATE TABLE IF NOT EXISTS control (name TEXT PRIMARY KEY, value REAL)")
    try:
        with db:
            yield db
    finally:
        db.close()


def expire_stale(db):
    # Includes a small startup/cleanup margin beyond the worker's wall-clock limit.
    db.execute("UPDATE jobs SET status='interrupted', updated=? "
               "WHERE status IN ('queued','running','cancelling') AND updated<?",
               (time.time(), time.time() - 195))


def task_dir(task_id):
    if not isinstance(task_id, str) or not re.fullmatch(r"[0-9a-f]{32}", task_id):
        raise ValueError("Invalid task ID.")
    return STATE / "tasks" / task_id


def prompt_with_context(task, workspace, files, limit):
    if not isinstance(task, str) or not task.strip():
        raise ValueError("A non-empty task is required.")
    if len(files) > 20:
        raise ValueError("At most 20 explicit context files are allowed.")
    chunks = [task]
    if files:
        root = workspace_root(workspace or "")
        for name in files:
            relative = Path(name)
            if relative.is_absolute() or not relative.parts or any(p in ("..", ".git", ".env", ".ssh") for p in relative.parts):
                raise ValueError("Context files must be explicit relative paths within the workspace.")
            path = root / relative
            for part in (path, *path.parents):
                if part == root:
                    break
                info = part.lstat()
                if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                    raise ValueError("Symlink and junction context paths are not supported.")
            path.resolve().relative_to(root)
            low = path.name.lower()
            if low.startswith(".env") or low in {"auth.json", "credentials.json", "id_rsa", "id_ed25519"} or path.suffix.lower() in {".pem", ".key", ".pfx", ".p12"}:
                raise ValueError("Credential files cannot be sent as task context.")
            if not path.is_file() or path.stat().st_size > limit * 4:
                raise ValueError("Context must be a small regular text file.")
            content = path.read_text(encoding="utf-8")
            if "\x00" in content:
                raise ValueError("Binary context is not supported.")
            chunks.append(f"\n--- Context file: {relative.as_posix()} ---\n{content}")
    prompt = "\n".join(chunks)
    if len(prompt) > limit:
        raise ValueError("Task context exceeds the configured character limit.")
    if SECRET.search(prompt):
        raise ValueError("Task context appears to contain credentials; remove them before submitting.")
    return prompt


def models(workspace=""):
    config = settings()
    policy = project_policy(workspace, config)
    weights = config["model_weights"]
    candidates = [m | {"weight": weights.get(m["id"], 50),
                       "weight_source": "configured" if m["id"] in weights else "default",
                       "data_collection": policy["data_collection"]}
                  for m in client.free_models()]
    with database() as db:
        rows = db.execute("SELECT model,status,created,updated,metadata FROM jobs "
                          "WHERE status IN ('succeeded','failed') AND created>? ORDER BY created DESC",
                          (time.time() - 86400,)).fetchall()
    recent = {}
    for row in rows:
        metadata = json.loads(row["metadata"])
        if metadata.get("data_collection", "deny") != policy["data_collection"]:
            continue
        recent.setdefault(row["model"], {"status": row["status"],
                          "code": metadata.get("code"),
                          "routing_failure": metadata.get("routing_failure"),
                          "elapsed_seconds": round(row["updated"] - row["created"], 1)})
    for model in candidates:
        model["last_local_result"] = recent.get(model["id"])
    return sorted(candidates, key=lambda m: (-m["weight"], m["id"]))


def start_task(task, model, workspace="", context_files=None, max_tokens=None, reasoning_effort=None):
    config = settings()
    if not config["enabled"]:
        raise ValueError("External workers are disabled in the local configuration.")
    if config["model_weights"].get(model, 50) == 0:
        raise ValueError("This model is disabled by its local weight.")
    policy = project_policy(workspace, config)
    cap = max_tokens if max_tokens is not None else config["max_tokens"]
    if type(cap) is not int or not 1 <= cap <= config["max_tokens"]:
        raise ValueError("Output cap exceeds the configured limit.")
    prompt = prompt_with_context(task, policy["workspace"], context_files or [], config["max_context_chars"])
    load_key()  # Fail before creating a job when setup is incomplete.
    task_id = uuid.uuid4().hex
    folder = task_dir(task_id)
    now = time.time()
    with database() as db:
        db.execute("BEGIN IMMEDIATE")
        expire_stale(db)
        cooldown = db.execute("SELECT value FROM control WHERE name='cooldown'").fetchone()
        if cooldown and cooldown[0] > now:
            raise ValueError("OpenRouter is cooling down after a rate limit; check status before retrying.")
        active = db.execute("SELECT COUNT(*) FROM jobs WHERE status IN ('queued','running','cancelling')").fetchone()[0]
        recent = db.execute("SELECT COUNT(*) FROM jobs WHERE created>?", (now - 60,)).fetchone()[0]
        daily = db.execute("SELECT COUNT(*) FROM jobs WHERE created>?", (now - 86400,)).fetchone()[0]
        if active >= config["max_parallel"] or recent >= config["requests_per_minute"] or daily >= config["daily_request_limit"]:
            raise ValueError("A local worker concurrency or request limit has been reached.")
        folder.mkdir(parents=True, mode=0o700)
        spec = dict(model=model, prompt=prompt, max_tokens=cap, reasoning_effort=reasoning_effort,
                    workspace=policy["workspace"], data_collection=policy["data_collection"])
        (folder / "request.json").write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
        db.execute("INSERT INTO jobs VALUES (?,?,?,?,?,?)",
                   (task_id, now, now, "queued", model, json.dumps(policy)))
    try:
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        subprocess.Popen([sys.executable, "-m", "external_workers.cli", "worker", task_id],
                         cwd=Path(__file__).resolve().parents[1], stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         creationflags=flags, start_new_session=os.name != "nt")
    except OSError:
        with database() as db:
            db.execute("UPDATE jobs SET status='failed',updated=?,metadata=? WHERE id=?",
                       (time.time(), '{"error":"Worker process could not start."}', task_id))
        raise ValueError("Worker process could not start.") from None
    return dict(task_id=task_id, status="queued", requested_model=model, **policy)


def read_task(task_id, include_output=False):
    folder = task_dir(task_id)
    with database() as db:
        expire_stale(db)
        row = db.execute("SELECT * FROM jobs WHERE id=?", (task_id,)).fetchone()
    if not row:
        raise ValueError("Unknown task ID.")
    result = dict(task_id=row["id"], status=row["status"], requested_model=row["model"],
                  created_at=row["created"], **json.loads(row["metadata"]))
    if row["status"] == "succeeded":
        result["output_path"] = str(folder / "result.md")
        result["output_is_untrusted"] = True
        if include_output:
            result["content"] = (folder / "result.md").read_text(encoding="utf-8")
    return result


def cancel_task(task_id):
    read_task(task_id)
    with database() as db:
        db.execute("UPDATE jobs SET status='cancelling',updated=? WHERE id=? AND status IN ('queued','running')",
                   (time.time(), task_id))
    return {"task_id": task_id, "status": read_task(task_id)["status"],
            "note": "Cooperative cancellation; an already transmitted API request cannot be refunded."}


def run_task(task_id):
    folder = task_dir(task_id)
    with database() as db:
        changed = db.execute("UPDATE jobs SET status='running',updated=? WHERE id=? AND status='queued'",
                             (time.time(), task_id)).rowcount
    if not changed:
        with database() as db:
            db.execute("UPDATE jobs SET status='cancelled' WHERE id=? AND status='cancelling'", (task_id,))
        (folder / "request.json").unlink(missing_ok=True)
        return
    metadata = {}
    try:
        config = settings()
        if not config["enabled"]:
            raise ValueError("External workers were disabled before dispatch.")
        spec = json.loads((folder / "request.json").read_text(encoding="utf-8"))
        policy = project_policy(spec.pop("workspace", ""), config)
        if spec.get("data_collection", "deny") != "allow":
            policy["data_collection"] = "deny"
        spec["data_collection"] = policy["data_collection"]
        metadata = policy
        response = client.generate(load_key(), **spec)
        content = response.pop("content")
        metadata.update(response)
        outcome = "succeeded"
    except client.OpenRouterError as error:
        outcome = "failed"
        metadata.update({"error": str(error), "code": error.code, "retry_after": error.retry_after,
                         **error.details})
        if str(error.code) in {"429", "http_429", "rate_limit", "rate_limited"}:
            wait = error.retry_after if isinstance(error.retry_after, (int, float)) else 60
            with database() as db:
                db.execute("INSERT OR REPLACE INTO control VALUES ('cooldown',?)", (time.time() + max(60, wait),))
    except Exception:
        outcome = "failed"
        metadata["error"] = "Local worker error; no request contents or credentials are included."
    with database() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT status FROM jobs WHERE id=?", (task_id,)).fetchone()
        if row[0] in {"cancelling", "cancelled", "interrupted"}:
            outcome = "cancelled" if row[0] != "interrupted" else "interrupted"
        elif outcome == "succeeded":
            (folder / "result.md").write_text(content, encoding="utf-8")
        db.execute("UPDATE jobs SET status=?,updated=?,metadata=? WHERE id=?",
                   (outcome, time.time(), json.dumps(metadata), task_id))
    (folder / "request.json").unlink(missing_ok=True)


def run_worker(task_id):
    """The subprocess has a wall-clock deadline even if HTTP keepalives continue."""
    def deadline():
        with database() as db:
            db.execute("UPDATE jobs SET status='failed',updated=?,metadata=? WHERE id=? "
                       "AND status IN ('queued','running','cancelling')",
                       (time.time(), '{"code":"deadline","error":"Worker exceeded 180 seconds."}', task_id))
        (task_dir(task_id) / "request.json").unlink(missing_ok=True)
        os._exit(1)

    timer = threading.Timer(180, deadline)
    timer.daemon = True
    timer.start()
    try:
        run_task(task_id)
    finally:
        timer.cancel()


def status(workspace=""):
    config = settings()
    policy = project_policy(workspace, config)
    with database() as db:
        expire_stale(db)
        rows = db.execute("SELECT id,status,model FROM jobs ORDER BY created DESC LIMIT 20").fetchall()
        cooldown = db.execute("SELECT value FROM control WHERE name='cooldown'").fetchone()
        count = db.execute("SELECT COUNT(*) FROM jobs WHERE created>?", (time.time() - 86400,)).fetchone()[0]
    try:
        account = client.account_status(load_key())
    except (ValueError, client.OpenRouterError):
        account = {"status": "unavailable"}
    return dict(config=config, project_policy=policy, account=account, local_attempts_last_24h=count,
                cooldown_until=cooldown[0] if cooldown else None,
                recent_tasks=[dict(row) for row in rows],
                note="Local counts cover this integration only; remaining OpenRouter requests are not exposed.")


def refresh_models():
    """Refresh a public catalog snapshot, without credentials or model inference."""
    records = sorted(client.free_models(), key=lambda m: m["id"])
    if not records:
        raise ValueError("No verified free models returned; the previous catalog is preserved.")
    STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = STATE / "free-models.json"
    previous = json.loads(path.read_text(encoding="utf-8")).get("models", []) if path.exists() else []
    old = {m["id"]: m for m in previous}
    new = {m["id"]: m for m in records}
    snapshot = {"checked_at": time.time(), "models": records}
    temporary = STATE / f"catalog-{uuid.uuid4().hex}.tmp"
    temporary.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, path)
    return dict(count=len(records), added=sorted(new.keys() - old.keys()),
                removed=sorted(old.keys() - new.keys()),
                changed=sorted(k for k in old.keys() & new.keys() if old[k] != new[k]),
                catalog_path=str(path), inference_requests=0)
