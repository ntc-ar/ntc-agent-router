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

Under `inherit`, the default, the child should run at the parent session's
level. Omitting effort no longer guarantees that. Since Claude Code 2.1.317, a
subagent on a different model than the parent uses that model's saved effort or
its default. In a 2.1.321 check with an Opus 5.5 parent at xhigh, the Opus child
ran at xhigh, but the Haiku, Sonnet and Fable children ran at medium. So set the
session level explicitly for every child, as described below, whenever the
level is known. Take it from the first of these that is available:
`CLAUDE_CODE_EFFORT_LEVEL`, an explicit user statement, or the parent's own
transcript. The transcript is `<CLAUDE_CODE_SESSION_ID>.jsonl` in a project
folder under `projects` in the Claude config directory (`CLAUDE_CONFIG_DIR`, or
`~/.claude`). Find it by file name, because the folder is named after the
directory where the session started. Read only the top-level `effort` of the
last assistant entries that have one, never message content. The model guide
says an unsupported level falls back to the highest supported level below it.
When a level is passed, report the effort as inherited.

If the level is unknown, omit effort. A child on the parent's model, or any
child before 2.1.317, still follows the session, so report its effort as
inherited but unverified. On 2.1.317 and later a child on another model runs at
its own saved or default effort, so report "not inherited, runs at the model
default".

Prefer a subagent without its own `effort` frontmatter, which would override the
session level. If only such a subagent fits, pass the session level per call
when that field exists. Otherwise report the level its definition sets.

Two cases change that level under `inherit`: an explicit user choice for the
assignment, and a user ceiling below the session level. For a ceiling, set the
ceiling, or the highest level below it that the model supports, and report
"inherited, capped at <level>". If the session level is not exposed, pass the
ceiling, which may be above the session level, and report the session level as
unverified.

To set a level, whether the session level, a user's choice or ceiling, or a
level for each subtask under `per-task`, use it whenever the model supports it
and a control exists. Claude Code 2.1.292 and later can expose a per-call
`effort` field for ordinary subagents. When present, pass the level there. If
per-call effort is absent, select the installed `ntc-effort-<level>` profile
with matching frontmatter and pass the model independently. These profiles
inherit models. Roles do not determine their level. Use only levels the chosen
model supports.

Under either policy, `CLAUDE_CODE_EFFORT_LEVEL` or a model or organization cap
can change the result. Report it.

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
user's explicit choices. Otherwise finish locally or report the blocker. The
same applies to a missing effort control or profile whenever a level must be
set, including the session level for a child on another model under `inherit`.
In that case report that the child runs at its own default. Disclose inherited
settings.

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
Fable is for unusually demanding, long-running work. Its lower weight prevents
routine automatic selection. From Claude Code 2.1.321, the `best` alias resolves
to the same model as `opus`. Earlier versions resolve it to Fable when the
account has Fable. For automatic selection, give it the weight of the model it
resolves to. If the user asks for `best` and the Agent field does not accept
it, pass the alias it resolves to and report the model that ran. Do not select
`opusplan` as a subagent model. It is a session workflow mode.

On the Anthropic API, current aliases resolve to Haiku 5.5 (Claude Code
2.1.293+), Sonnet 5.5 (2.1.284+), Opus 5.5 (2.1.280+) and Fable 5.2 (2.1.321+,
Fable 5.1 from 2.1.257 to 2.1.320). Claude apps gateway sessions resolve `fable`
to Fable 5. Check the child's `message.model` or `/tasks` to see which ran.
Provider pins such as `ANTHROPIC_DEFAULT_HAIKU_MODEL`, allowlists and
same-family parent inheritance can resolve an alias differently.
Confirm the effective model. Use a verified, accepted full ID when an exact
generation is required. An alias alone is not proof of the latest version.
In Claude Code, Fable 5.2, Opus 5.5, Sonnet 5.5 and Haiku 5.5 default to medium
effort when nothing sets a level. A child dispatched without effort may follow
the parent session instead, as described above.
Under `per-task`, reassess effort on upgrade rather than carrying an older
model's high setting into every assignment.

Pass the selected model even when using an `ntc-effort-*` profile: its
`model: inherit` is a fallback, not an economy setting. Do not copy an Opus
parent into routine work by omission. Under `per-task`, do not copy maximum
effort either. Explain unavailable or forced controls. A missing model selector
does not authorize a CLI/API workaround.

## Check overrides and results

Inspect relevant non-secret model restrictions and, when present,
`CLAUDE_CODE_SUBAGENT_MODEL`, `CLAUDE_CODE_SUBAGENT_MODEL_FORCE`,
`CLAUDE_CODE_EFFORT_LEVEL` and `CLAUDE_CODE_SUBAGENT_EFFORT`. The last one, from
2.1.316, sets subagent effort only when nothing else names a level. It is the
user's own choice for subagents, so when it is set do not pass the session level
over it, and report its value. In Claude
Code 2.1.251 and later, the model order is per-invocation choice, agent
definition, subagent environment default, then parent.
`CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1` overrides individual model choices. Report
the forced value rather than claiming the requested model ran. Effort
frontmatter overrides the session setting, but not `CLAUDE_CODE_EFFORT_LEVEL`
or a model/organization cap. Preserve these settings and the parent's choices.
Effort labels are model-specific. See [model configuration](https://code.claude.com/docs/en/model-config).

Distinguish requested, configured, and runtime-confirmed values.
Use `/tasks` to inspect a running subagent's model and, when displayed, effort.
Child transcript fields such as `message.model` or top-level `effort` may provide
additional evidence, but their presence depends on the runtime. Report absent
evidence as unverified. Do not infer effort from a saved setting alone.
Keep effort profiles on ordinary Agent/Task dispatch.
Omit fields that would turn the subagent into a teammate.

Without selectable models, delegate for independence. Without agents, work
in the parent. Do not substitute another CLI session or API bridge.

Reviewed 2026-11-11. The running tool schema takes precedence over examples.
