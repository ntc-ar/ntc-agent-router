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
through an exposed field accepting that value. If per-call effort is absent,
select the installed `ntc-effort-<level>` profile with matching frontmatter and
pass the model independently. These profiles inherit models; roles do not
determine their level. Use only levels the chosen model supports.

If a control or profile is unavailable, inherit only within the user's explicit
choices and effort ceiling; otherwise finish locally or report the blocker.
Disclose inherited settings.
Do not manufacture fields or rewrite profiles during routing.
Use ordinary subagent dispatch: forks may ignore model overrides.
See [subagents](https://code.claude.com/docs/en/sub-agents#choose-a-model).

## Check overrides and results

Inspect relevant non-secret model restrictions and, when present,
`CLAUDE_CODE_SUBAGENT_MODEL`, `CLAUDE_CODE_SUBAGENT_MODEL_FORCE`, and
`CLAUDE_CODE_EFFORT_LEVEL`. Their precedence varies by version; effort environment
overrides defeat frontmatter. Preserve them and the parent's settings.
Effort labels are model-specific. See [model configuration](https://code.claude.com/docs/en/model-config).

Distinguish requested, configured, and runtime-confirmed values.
Prefer the child's transcript metadata when available: `message.model` and
top-level `effort`. Report absent evidence as `not verified`.
Do not infer child effort solely from `CLAUDE_EFFORT` or `meta.json`;
a [reproduced dispatch-path issue](https://github.com/anthropics/claude-code/issues/81677)
documents misleading readings and differences for teammates and `--agent`.
Keep effort profiles on ordinary Agent/Task dispatch.
Omit fields that would turn the subagent into a teammate.

Without selectable models, delegate for independence. Without agents, work
in the parent. Do not substitute another CLI session or API bridge.
