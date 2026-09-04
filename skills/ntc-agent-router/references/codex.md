# Codex

Use the native subagent tool exposed in this session. Some hosts accept model
and reasoning effort per spawn; others expose configured agent types. Inspect
the actual schema rather than copying arguments from another Codex surface.

When both fields exist, select the model and its supported effort for each
assignment. If context inheritance prevents overrides, choose a supported
fresh-context invocation with a self-contained brief. Do not discard essential
context merely to select a smaller model.

Custom TOML agents and `[agents]` defaults can affect effective settings. Read
only relevant non-secret fields when needed. A configured model with omitted
effort may use its own default; an unconfigured child can inherit the parent.
Do not label an omitted effort as automatically cheap. An explicit user model
or effort preference takes precedence over the routing heuristic.

This package installs no fixed Codex model profiles. Report unsupported controls
individually and use the available subset. Use returned runtime metadata for
confirmation; a child's statement about its identity is not evidence.

## NTC preference: Spark for implementation

Prefer `gpt-5.3-codex-spark` for substantial, well-scoped code implementation
when it passes the [configuration and quota checks](configuration.md), the
runtime offers it, and it is adequate for the task. This preference
helps use a separate allowance where the account exposes one. It is not an
exclusive model assignment: user choices and actual capabilities take priority.
The user can disable it with a request such as "no preference for Spark."

Have the parent settle interfaces and acceptance criteria, then give Spark
coherent implementation chunks with file ownership and explicit checks. It can
write most of the code across independent chunks; do not restrict it to trivial
edits merely because a first pass might need corrections. Do not split a tiny
task to force its use. Keep context-dependent architecture and final integration
with the parent or another suitable agent.

Choose effort separately for each chunk from supported levels; Spark does not
always run at low or medium. Require appropriate tests/checks in the brief and
inspect the resulting diff. A draft may contain errors; the accepted result must
meet the same quality bar. Correct a local defect directly or permit one targeted
repair under the shared retry budget. Escalate if failures expose a reasoning
gap or repeated review/rework eliminates the benefit; do not repeatedly regenerate
the same code. High-consequence code still needs capable review before use.

Apply the configured reserve to every Spark window, including both five-hour
and weekly usage when exposed. Reaching either boundary is enough to stop new
Spark assignments. Follow the configured fallback or stop behavior, including
when quota is unknown. A separate allowance is not unlimited execution, and
parent coordination and corrections may still consume the main allowance.

Current model scope: [OpenAI model catalog](https://learn.chatgpt.com/docs/models).
Plan and usage details: [OpenAI pricing](https://learn.chatgpt.com/docs/pricing).

Native behavior and configuration reference:
[OpenAI subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents).
Skill discovery and reload:
[OpenAI skills](https://learn.chatgpt.com/docs/build-skills).

Reviewed 2026-09-04. The running tool schema takes precedence over examples.
