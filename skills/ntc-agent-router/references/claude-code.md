# Claude Code adapter

Keep this skill in the main conversation without `model`, `effort`, or
`context: fork` frontmatter. Invoke `/ntc-agent-router` or use normal discovery.
See [skills](https://code.claude.com/docs/en/skills).

## Discover and dispatch

Inspect the live `Agent` schema (older hosts may call it `Task`), available
subagents, accepted model values, and installed `ntc-effort-*` profiles.
`claude --version` and `claude --help` check local features without model calls.
Picker, CLI, and frontmatter values do not necessarily fit the Agent schema.

Choose model and reasoning depth using the shared policy. Pass a model only
through an exposed field accepting that value. If per-call effort is absent and
the chosen model supports effort, select the installed `ntc-effort-<level>`
profile with matching frontmatter and pass the model independently. These
profiles inherit models; roles do not determine their level. Haiku 4.5 does not
support effort, so dispatch it without an effort profile and report that effort
is not selectable. Use only levels the chosen model supports.

If a control or profile is unavailable, inherit only within the user's explicit
choices and effort ceiling; otherwise finish locally or report the blocker.
Disclose inherited settings.
Do not manufacture fields or rewrite profiles during routing.
Use ordinary subagent dispatch: forks may ignore model overrides.
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

On the Anthropic API, current aliases resolve to Sonnet 5.5 (Claude Code
2.1.284+), Opus 5.5 (2.1.280+) and Fable 5.1 (2.1.257+). Provider pins,
allowlists and same-family parent inheritance can resolve an alias differently.
Confirm the effective model; use a verified, accepted full ID when an exact
generation is required. An alias alone is not proof of the latest version.
Sonnet 5.5 and Opus 5.5 default to medium effort. Reassess effort on upgrade
rather than carrying an older model's high setting into every assignment.

Pass the selected model even when using an `ntc-effort-*` profile: its
`model: inherit` is a fallback, not an economy setting. Do not copy an Opus
parent or maximum effort into routine work by omission. Explain unavailable or
forced controls; a missing model selector does not authorize a CLI/API workaround.

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

Reviewed 2026-10-05. The running tool schema takes precedence over examples.
