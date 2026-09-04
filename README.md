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

## How it decides

The router separates three decisions: which part of the work is independent,
what model capability it needs, and how much reasoning is appropriate. It
considers uncertainty, dependencies, the consequences of an error, and ease of
verification. File size alone does not determine difficulty.

Roles are assigned according to the work. There is no fixed list of models or
permanent association between model and effort. Agents can implement authorized
changes to assigned files, as well as investigate or review.

In Codex, there is a deliberate preference for **GPT-5.3-Codex-Spark for most
of the implementation**, when available and when the work can be scoped. The
main agent defines interfaces, integrates, and reviews; Spark produces code in
coherent parts, with tests specified in the assignment. Its effort is also
decided per subtask. A first version may need corrections, but the final result
must pass the same checks.

This preference makes it possible to use a separate quota when the account
offers one. The router checks native limits when they are exposed; it does not
assume access or unlimited quota. Coordination and corrections may consume the
main quota. If Spark is unavailable or rework stops being worthwhile, it
chooses another route. You can ask for “no preference for Spark” or choose
another model.

The default mode is `auto`. `economy` favors fewer calls and reusing results;
`balanced` balances quality and time; `quality` allows deeper work or adding a
useful review. No mode requires creating agents or always using the largest
model.

Without a user-specified limit, the policy allows four agent attempts per task,
including retries and continuations. Concurrency is decided from the ready
subtasks and the environment's available slots. These limits are instructions;
they are not a billing cap imposed by the program.

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
