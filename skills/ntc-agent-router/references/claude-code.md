# Claude Code adapter

Keep this skill in the main conversation without `model`, `effort`, or
`context: fork` frontmatter. Invoke `/ntc-agent-router` or use normal discovery.
See [skills](https://code.claude.com/docs/en/skills).

## Discover and dispatch

Inspect the live `Agent` schema (older hosts may call it `Task`), available
subagents, accepted model values and, for setting a level, installed
`ntc-effort-*` profiles. `claude --version` and `claude --help` check local
features without model calls, but the `claude` on PATH can differ from the
running session: the desktop app bundles its own build. Prefer the running
session's version when it is exposed. Picker, CLI, and frontmatter values do not
necessarily fit the Agent schema.

Choose the model using the shared policy and pass it only through an exposed
field accepting that value, under either effort policy. Workflow `agent()`
calls, when available, take the same `model` and `effort` options.

Under `inherit`, the default, omit any per-call `effort` field and do not use
an `ntc-effort-*` profile, so the child follows the session level. In a Claude
Code 2.1.293 check, Agent and Workflow children dispatched this way ran at the
parent session's level (xhigh). The model guide says an unsupported level falls
back to the highest supported level below it. Report the effort as inherited.
Prefer a subagent without its own `effort` frontmatter, which would override the
session level. If only such a subagent fits, pass the session level per call
when that field exists; otherwise report the level its definition sets.

Two cases set a level under `inherit`: an explicit user choice for the
assignment, and a user ceiling below the session level. For a ceiling, set the
ceiling, or the highest level below it that the model supports, and report
"inherited, capped at <level>". If the session level is not exposed, pass the
ceiling and report the session level as unverified.

To set a level, for those cases or for each subtask under `per-task`, use the
level whenever the model supports it and a control exists; an omitted effort is
inherited, not the model's default. Claude Code 2.1.292 and later can expose a
per-call `effort` field for ordinary subagents; when present, pass the level
there. If per-call effort is absent, select the
installed `ntc-effort-<level>` profile with matching frontmatter and pass the
model independently. These profiles inherit models; roles do not determine
their level. Use only levels the chosen model supports.

Under either policy, `CLAUDE_CODE_EFFORT_LEVEL` or a model or organization cap
can change the result; report it.

Confirm which Haiku the alias resolves to. From Claude Code 2.1.293 on the
Anthropic API, `haiku` is Haiku 5.5, which supports low through max. Haiku 4.5,
used by earlier versions and other providers, does not support effort: dispatch
it without an effort level or profile and report effort as not applicable. If
the version, provider or an `ANTHROPIC_DEFAULT_HAIKU_MODEL` pin leaves this
unclear, check the child's model in `/tasks` or its transcript and report effort
as unverified until then. If the user chose a level that Haiku 4.5 cannot take,
apply the shared rule for unsupported exact levels: use the highest-weight
adequate model that supports it unless the user also named the model. Do not
drop the level silently.

If a model control is unavailable, inherit the parent model only within the
user's explicit choices; otherwise finish locally or report the blocker. Under
`per-task`, the same applies to a missing effort control or profile and the
user's effort ceiling. Disclose inherited settings.

Do not manufacture fields or rewrite profiles during routing.
Use ordinary subagent dispatch: forks may ignore model overrides and do not
take per-call effort.
See [subagents](https://code.claude.com/docs/en/sub-agents#choose-a-model).

## Apply efficiency preferences

Apply the shared mode and weights after checking the model's capabilities.
With exposed, documented Haiku/Sonnet/Opus/Fable aliases, consider Haiku for
clear, bounded work, Sonnet for ordinary implementation and reasoning, and Opus
for work needing deeper judgment. These are starting points, not fixed roles or
effort levels. Use runtime descriptions for other models. A configured alias
weight does not apply to an unrelated or guessed full model ID.
Fable is for unusually demanding, long-running work; its lower weight prevents
routine automatic selection. Claude Code's `best` alias can resolve to Fable,
so treat it with the same priority. Do not select `opusplan` as a subagent model;
it is a session workflow mode.

On the Anthropic API, current aliases resolve to Haiku 5.5 (Claude Code
2.1.293+), Sonnet 5.5 (2.1.284+), Opus 5.5 (2.1.280+) and Fable 5.1 (2.1.257+).
Provider pins such as `ANTHROPIC_DEFAULT_HAIKU_MODEL`, allowlists and
same-family parent inheritance can resolve an alias differently.
Confirm the effective model; use a verified, accepted full ID when an exact
generation is required. An alias alone is not proof of the latest version.
Haiku 5.5, Sonnet 5.5 and Opus 5.5 default to medium effort when nothing sets
a level; a child dispatched without effort follows the parent session instead.
Under `per-task`, reassess effort on upgrade rather than carrying an older
model's high setting into every assignment.

Pass the selected model even when using an `ntc-effort-*` profile: its
`model: inherit` is a fallback, not an economy setting. Do not copy an Opus
parent into routine work by omission; under `per-task`, do not copy maximum
effort either. Explain unavailable or forced controls; a missing model selector
does not authorize a CLI/API workaround.

## Check overrides and results

Inspect relevant non-secret model restrictions and, when present,
`CLAUDE_CODE_SUBAGENT_MODEL`, `CLAUDE_CODE_SUBAGENT_MODEL_FORCE`, and
`CLAUDE_CODE_EFFORT_LEVEL`. In Claude Code 2.1.251 and later, the model order is
per-invocation choice, agent definition, subagent environment default, then
parent. `CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1` overrides individual model choices;
report the forced value rather than claiming the requested model ran. Effort
frontmatter overrides the session setting, but not `CLAUDE_CODE_EFFORT_LEVEL`
or a model/organization cap. Preserve these settings and the parent's choices.
Effort labels are model-specific. See [model configuration](https://code.claude.com/docs/en/model-config).

Distinguish requested, configured, and runtime-confirmed values.
Use `/tasks` to inspect a running subagent's model and, when displayed, effort.
Child transcript fields such as `message.model` or top-level `effort` may provide
additional evidence, but their presence depends on the runtime. Report absent
evidence as `not verified`; do not infer effort from a saved setting alone.
Keep effort profiles on ordinary Agent/Task dispatch.
Omit fields that would turn the subagent into a teammate.

Without selectable models, delegate for independence. Without agents, work
in the parent. Do not substitute another CLI session or API bridge.

Reviewed 2026-10-08. The running tool schema takes precedence over examples.
