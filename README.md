# NTC Agent Router

NeaTech skill for deciding when to delegate work and which model and effort to
use for each subtask. It works with native agents in Codex and Claude Code.

A small fix is handled by the main agent. Two independent modules can be
worked on in parallel. A diagnosis with contradictory evidence may need more
reasoning and a review. The router makes these decisions based on the task and
the controls available in the session.

## Installation

Requires Python 3.11 or later only for installation. The skill needs no
dependencies, API keys, or background process.

```sh
git clone https://github.com/ntc-ar/ntc-agent-router.git
cd ntc-agent-router
python install.py --target all --dry-run
python install.py --target all
```

On Windows, you can also use `py -3` instead of `python`. To install for a
single tool, choose `--target codex` or `--target claude`.

| Target | Files |
| --- | --- |
| Codex | `~/.codex/skills/ntc-agent-router/` |
| Claude Code | `~/.claude/skills/ntc-agent-router/` and `~/.claude/agents/ntc-effort-*.md` |

The installer respects `CODEX_HOME` and `CLAUDE_CONFIG_DIR`. `--home PATH` lets
you test with another user directory and ignores those variables. If your
Codex distribution discovers skills in `~/.agents/skills`, you can copy the
`skills/ntc-agent-router` folder there; avoid keeping two copies with the same
name.

A reinstallation preserves a copy of replaced files in
`backups/ntc-agent-router/` inside each tool's configuration directory.
Identical files are left as they are. If a replacement fails, the installer
tries to restore the previous destinations and keeps the backups. It does not
modify configuration, authentication, or general instructions.

Open a new session after installing, especially in Claude Code, to load the
profiles. Codex may detect changes automatically; if the skill does not appear
in the selector, restart the application.

## Usage

In Codex:

```text
$ntc-agent-router status
$ntc-agent-router Review this project and fix any errors you find.
$ntc-agent-router economy Compare these logs and return the differences.
$ntc-agent-router quality Investigate this race condition.
```

In Claude Code:

```text
/ntc-agent-router status
/ntc-agent-router Review this project and fix any errors you find.
```

It can also activate automatically when delegation is appropriate. `status`
reports what it can control without launching test agents. `off` stops applying
this policy in the conversation.

You can adjust the criteria in natural language:

```text
Use at most two agents, prioritize time, and choose the effort for each case.
Keep this model for all agents, with automatic effort up to high.
Delegate the documentation and handle the main implementation.
```

## Configuration and model weights

The default mode is **economy**. It starts clear work on a suitable light model,
considers a balanced model for everyday implementation, and requires a concrete
reason to use Astra or another flagship. Model and effort are selected separately;
an Astra/Ultra parent does not make its children Astra/Ultra.

The bundled Codex priorities are Luna **90**, Terra **80**, Sol **50**, GPT-5.5
**40**, and Astra **10**. Claude aliases start at Haiku **90**, Sonnet **80**,
and Opus **10**. These are configurable selection weights, not prices, traffic
percentages, or promised token savings. Higher wins among available, adequate
candidates; capability requirements still take priority. Unlisted exposed
models remain candidates with weight 50, using their actual capability metadata.

You can change settings in the conversation:

```text
$ntc-agent-router Prefer Luna for straightforward implementation work.
$ntc-agent-router off
$ntc-agent-router on
```

To save preferences across sessions, ask the agent to save them or create
`~/.config/ntc-agent-router/config.toml`. On Windows, `~` means `%USERPROFILE%`.
For project settings, use `.ntc-agent-router.toml` at the repository root.

```toml
enabled = true
mode = "economy" # "balanced" (or "auto") and "quality" are also available

# Optional overrides; omitted model weights keep their packaged/user values.
[model_weights]
"gpt-5.6-terra" = 95
"gpt-6-astra" = 5
```

Set the top-level `enabled = false` to stop the router policy. This switch does
not cancel active agents or change native host settings.

Settings merge by key: packaged defaults, user file, project file, then current
conversation instructions. Updates leave personal and project settings alone.
`status` reports the mode, effective weights, available controls, their sources,
and the chosen action. Weight zero excludes a model from automatic selection;
an explicit request for that model can override the weight. A custom weight only
applies to an exact model ID or accepted alias. It does not make a picker-only
model spawnable.

See the [configuration reference](skills/ntc-agent-router/references/configuration.md)
for exact precedence, validation, and selection behavior.

## How it decides

The router separates three decisions: which part of the work is independent,
what model capability it needs, and how much reasoning is appropriate. It
considers uncertainty, dependencies, the consequences of an error, and ease of
verification. File size alone does not determine difficulty.

Roles are assigned according to the work. The preference table is editable and
does not limit the runtime model roster or tie models to effort levels. Agents
can implement authorized changes to assigned files, as well as investigate or
review. "Reviewer" and "security" are not automatic reasons to use a flagship:
the router separates routine evidence gathering from consequential judgment.

`economy` favors adequate lighter models, compact context and targeted checks.
`balanced` (also `auto`) gives more weight to avoiding likely rework and delay;
`quality` allows deeper work or a useful review when it improves the result.
All modes respect weights among suitable candidates. None requires creating
agents or always using the largest model. More effort is not a substitute for
missing evidence, permissions or tools.

Each delegation wave states the assignment, model, effort and reason. A departure
from a higher-weight suitable candidate needs an explanation, as does escalation
to a flagship or maximum effort. Confirmed settings and fallbacks are reported
when the runtime exposes them. This leaves evidence in the conversation without
adding a background process or collecting telemetry.

The router has no default numerical cap on agents or attempts. It continues in
waves while each child has a distinct useful deliverable whose expected value
exceeds the coordination, integration, and verification cost. Explicit user and
host limits still apply; idle slots alone are not a reason to create agents.

## Differences between tools

**Codex:** uses the model and effort parameters exposed by its agent tool. If
the environment requires separate context to change those values, it sends a
self-contained assignment. It does not install profiles with fixed models.

**Claude Code:** can select a model per call. For versions that configure effort
through frontmatter, it includes five effort profiles: `low`, `medium`, `high`,
`xhigh`, and `max`. The router chooses the profile when delegating and selects
the model separately. It uses only combinations compatible with the model and
the running version. Profiles inherit tools and permissions.

The main model and its effort remain as you configured them. Preferences or
environment variables may override a router request; the skill distinguishes
what was requested from what the runtime confirmed.

**ChatGPT web:** the skill file can guide decisions if the interface allows it
to be loaded. It does not install local agents or enable controls that the
interface does not expose. The local version is verified separately.

## Verification

```sh
python -m unittest discover -s tests -v
```

The tests check installation, reinstallation, backups, and recovery from
errors in temporary directories. They do not call models. The decision cases
and scope of the tests performed are documented in [VALIDATION.md](VALIDATION.md).

The router is a policy executed by the model. File tests do not demonstrate
that it will always choose correctly, and no savings percentage is promised.
To measure it, compare equivalent tasks and include context, coordination,
verification, and retries.

## Files

- `skills/ntc-agent-router/`: common policy and tool adapters.
- `claude-agents/`: native profiles that allow choosing effort in Claude Code.
- `install.py`: installer for Windows, Linux, and macOS.
- `tests/`: local tests without external services.

Each adapter's references link to the official documentation. Parameters
available in the session take priority over any example.

NeaTech · NTC
