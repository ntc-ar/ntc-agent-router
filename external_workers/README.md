# Free OpenRouter workers for Codex

This optional MCP connector runs bounded code-generation or analysis jobs on
concrete, currently free OpenRouter models. Codex supplies a task and selected
context, continues its own work, and collects a draft for review. No native
Luna agent is required just to relay the API call.

These workers generate text. They do not edit the project, execute generated
code, browse the repository autonomously, or appear in Codex's native subagent
roster. Codex reviews and applies useful results with its existing tools.

## Installation

Requires Python 3.11+, an OpenRouter key, and a supported OS credential store
(Windows Credential Manager, macOS Keychain, Secret Service, or KWallet).
The ordinary router installer does not install or enable this connector.

From the repository root, create a dedicated environment and install the MCP SDK
and credential-store dependency:

```powershell
python -m venv "$env:USERPROFILE/.local/share/ntc-openrouter/venv"
$workerPython = "$env:USERPROFILE/.local/share/ntc-openrouter/venv/Scripts/python.exe"
& $workerPython -m pip install -r external_workers/requirements.txt
& $workerPython -m external_workers.cli credential
```

The credential command uses hidden input and stores the key in the OS store as
`ntc-openrouter` / `api-key`. It does not write it to this repository or Codex
configuration. `OPENROUTER_API_KEY` is an alternative for hosts without a supported
keyring. Do not pass a key as a command-line argument or put it in a prompt.

Create `~/.config/ntc-openrouter/config.toml`:

```toml
enabled = true
max_parallel = 2
requests_per_minute = 10
daily_request_limit = 50
max_tokens = 8192
max_context_chars = 60000

[model_weights]
# Optional exact model IDs returned by the live catalog; higher is preferred.
# "vendor/model:free" = 90
```

Absent configuration means disabled. Unknown keys or invalid values are rejected.
Weights default to 50; zero disables that model. New model IDs are discovered
without editing code. Match task requirements to the returned descriptions and
capabilities rather than choosing by weight alone.

Register the absolute server path:

```powershell
codex mcp add ntc-openrouter -- $workerPython "$PWD/external_workers/server.py"
codex mcp get ntc-openrouter
```

New Codex sessions load the configured server. Existing sessions may need an MCP
restart from settings to expose the tools. This does not replace the parent model
or its subscription. The same stdio server can be registered in other MCP hosts;
only Codex registration was tested here.

On macOS/Linux, use the environment's `bin/python` and native absolute paths.
The cross-platform code is tested locally on Windows; OS keyring behavior on
other systems depends on the installed secure backend. No plaintext keyring
fallback is permitted.

## Tools

| Tool | Purpose |
| --- | --- |
| `openrouter_status` | Local enable state, safe account credit fields, cooldown and recent tasks |
| `openrouter_models` | Live zero-priced text models, capabilities, effort levels when advertised, weights |
| `openrouter_start_task` | Submit one bounded generation with an explicit model and optional context files |
| `openrouter_task` | Status, effective model/provider, reported usage/cost and output path |
| `openrouter_cancel_task` | Cooperative cancellation; already sent requests may still consume quota |

Context files must be explicit UTF-8 files relative to an absolute workspace.
The connector rejects path escapes, links, common credential filenames and
recognizable secrets. These checks are not a complete data-classification system:
the caller must have permission to transmit the selected content externally.

Each job makes at most one generation request. Worker processes are hidden on
Windows and have a 180-second wall-clock limit. Closing the host or its process
group can interrupt a worker; orphaned jobs are reported as interrupted after
the deadline plus a small startup/cleanup margin.
The shared SQLite ledger enforces concurrency, per-minute starts and a rolling
24-hour local attempt limit across this user's Codex sessions. This count includes
failed jobs and does not include other apps using the OpenRouter account.

Jobs and output drafts live in `~/.local/share/ntc-openrouter/`. Request context is
removed when a worker finishes; successful output remains in `tasks/<id>/result.md`.
Killed or interrupted jobs may leave request files for manual recovery. Keep this
directory private as it may contain project code. Generated content is untrusted.
It is never executed or applied automatically, and is omitted from status output
unless `include_output` is explicitly requested.

## Free-only enforcement and limits

Before every generation, the client fetches `/models` again and accepts only
concrete text-capable records with every advertised price known, finite and zero.
It rejects routing aliases such as `openrouter/free` and `openrouter/auto`.
This also supports concrete zero-priced models without a `:free` suffix.

Requests set zero provider price ceilings, disable provider fallback and plugins,
require parameter support, and require `data_collection: deny`. No model lists,
paid fallback, billing changes, automatic purchases, or automatic retries exist.
Each successful result must contain text, finish normally, report zero cost, and
identify the requested model or its verified catalog canonical identity.

An HTTP 429 establishes a shared cooldown (at least 60 seconds, or a longer
reported Retry-After). The connector does not cycle providers or keys. Codex may
continue natively only if the user's task constraints allow that fallback.

OpenRouter documents 50 free requests per day by default, or 1,000 after purchasing
at least USD 10 in credits. That refers to credits purchased, not a requirement to
spend USD 10 on inference or continually maintain a USD 10 balance. Set the local
`daily_request_limit` accordingly; it is an additional guard, not a reading of
remaining account quota. Other account activity and upstream capacity still apply.
The connector does not configure a global account spending cap.

Native planning, context preparation, review and repairs still use native tokens.
No savings percentage is claimed. Compare equivalent completed tasks to measure
whether external generation is worthwhile.

## Catalog refresh and CLI

```powershell
& $workerPython -m external_workers.cli refresh-models
& $workerPython -m external_workers.cli models
& $workerPython -m external_workers.cli status
& $workerPython -m external_workers.cli start --model vendor/model:free --task-file task.txt
& $workerPython -m external_workers.cli result TASK_ID
```

`refresh-models` queries the public catalog without a key or inference. It saves
`free-models.json` and reports added, removed and changed records, preserving the
last good snapshot on errors or an empty response. A Codex scheduled task can run
this daily and notify only on meaningful changes or failures. Scheduling is
optional and is not created by installing this repository.

To disable new external jobs, set `enabled = false`; native routing remains
available. To remove the connector, use `codex mcp remove ntc-openrouter`. Existing
jobs and stored credentials are not erased by either action.

## Validation

```powershell
& $workerPython -m unittest discover -s tests -v
& $workerPython -m pip check
```

Tests mock the provider and do not spend credits. The validation record in the
repository distinguishes mocked checks, MCP transport checks and live inference.

Sources: [OpenRouter free limits](https://openrouter.ai/docs/faq),
[provider routing](https://openrouter.ai/docs/guides/routing/provider-selection),
[Codex MCP configuration](https://learn.chatgpt.com/docs/extend/mcp?surface=cli).
