# Validation

Initial review: September 4, 2026.

## Design review

The original kit was usable as a delegation policy. Its capability checks and
distinction between requested and confirmed models were useful. Routing was
limited by a small fixed set of model/effort combinations, read-only agents,
and support for OpenAI only.

This version keeps capability checks and selects the model per subtask, and
the effort too under `per-task`. Agents can implement changes within a defined
scope. Claude Code sets effort per call when the agent tool allows it and
otherwise uses effort profiles; the model is selected independently. Delegation
continues according to the expected value of the next distinct assignment
instead of a default attempt cap.

## Completed checks

- Validated skill frontmatter and metadata.
- Validated YAML and effort levels in the five Claude profiles.
- Passed thirteen installer tests with Python 3.14 on Windows, with no failures
  or skipped tests: installation, reinstallation, preservation of unrelated
  files, idempotence, backups, copy and replacement failures, and link rejection.
- Installed into both tools and verified that a second run made no changes.
- Confirmed native discovery in Codex CLI 0.153.1 through `skills/list`: one
  enabled user skill, with no duplicates.
- Ran native delegation requesting Luna with low effort to extract the five
  profiles; the result matched the files.

The delegated run checked execution and results. The control accepted the
requested model and effort but did not return metadata that independently
confirmed the effective values.

The GitHub workflow runs the tests with Python 3.11 on Windows, Linux, and macOS.
Results for each revision are available in Actions.

## Routing scenarios

The instructions were evaluated against simulated scenarios in addition to the
execution checks above. This was not a benchmark.

| Situation | Reviewed behavior |
| --- | --- |
| Exact one-word replacement | Complete in the parent without spawning agents |
| Two independent modules | Delegate one with file ownership and work on the other |
| Per-task effort, model supports low/high but not medium | Select a supported level adequate for the task |
| Essential evidence is inaccessible | Identify the blocker; more effort does not grant access |
| Exact model and effort requested, combination unsupported | Report the blocker without substituting settings |
| Explicit two-agent limit, one completed and one failed | Finish locally within the user's constraints |
| Per-task effort, Claude has no per-call effort control | Select a compatible profile without inventing parameters |
| Per-task effort and Claude exposes per-call effort | Pass the level per call; no profile is needed |
| Environment forces the model | Distinguish the request from effective configuration |
| Four useful agents completed and a distinct regression check remains | Start another adequate agent; count alone is not a stop condition |
| Slots remain but proposed work duplicates completed review | Do not delegate |

The evaluation found ambiguities in effort inheritance and fallback to the
parent. The policy was updated so these paths always respect exact user choices
and limits, even when those constraints prevent completion.

## Weighted routing scenarios — reviewed through September 23, 2026

Real usage showed that the original "smallest adequate model" guidance did not
consistently prevent flagship selection. It also left ordinary agents open to
inheriting a flagship parent and maximum effort. The revised policy adds an
economy default, configurable selection weights, explicit model/effort dispatch
and a concrete reason for escalation. No host defaults or billing controls change.

An independent instruction-level evaluation established the original weighting
behavior on September 8. The table tracks current expected decisions, including
cases updated after that evaluation. It is not a record of one benchmark run:

| Scenario | Expected decision |
| --- | --- |
| Direct schema extraction with Astra/Ultra parent | Luna/low with explicit settings |
| One-file parser fix with interacting quoting rules and fixtures | Terra/medium |
| One README typo | Work in the parent |
| Explicit Astra/high request with Astra weight zero | Honor the explicit request |
| Four agents completed; an independent regression audit remains | Dispatch the smallest adequate agent |
| Four agents completed; the next proposal duplicates covered work | Integrate locally without another agent |
| Project overrides one user model weight | Merge per key; preserve other user weights |
| Terra fails a cross-module concurrency acceptance check | One targeted escalation to Sol/high |
| Preferred light model unavailable | Reevaluate the remaining candidates before Astra |
| Only Astra exposed for requested extraction child | Astra/low; disclose the lack of alternatives |
| Claude extraction when Haiku 4.5 is available | Haiku without an effort profile; this model does not support effort |
| Per-task effort, Claude extraction when `haiku` resolves to Haiku 5.5 | Haiku with an explicit low effort; omitting it inherits the parent's level |
| Boolean used as a model weight | Reject configuration before routing |
| Unlisted light model exposed with suitable capability metadata | Classify it as light, assign provisional weight 90, and compare it with adequate candidates |
| No model/effort controls for a requested independent child | Disclose inherited, unverified settings |
| All adequate exposed candidates have weight zero | Report the constraint without an excluded-parent fallback |

These are simulated routing decisions, not a task-quality or token benchmark.
The real policy diagnosis and evaluation runs requested Luna/medium and
Terra/medium respectively. Local child-session metadata confirmed both models
and effort levels. No flagship child was used for this validation.

The skill validator and all thirteen installer tests passed on Windows.
Packaged weights and existing user settings parsed as TOML; the effective mode
was economy. Reinstalled in Codex and Claude Code, verified both copies against
the source, confirmed an identical dry run made no changes, and checked that the
personal configuration remained valid.

## Efficient delegation evaluation — September 11, 2026

An independent read-only policy review requested Luna with low effort and
checked the revised package against six scenarios:

| Scenario | Reviewed behavior |
| --- | --- |
| Four useful agents completed and a distinct regression gap remains | Start another adequate agent; the previous count is irrelevant |
| Twelve independent mechanical modules remain | Process useful assignments in waves limited by available slots and integration capacity |
| A run fails again with the same brief, evidence, and tools | Do not repeat it without a material change |
| Astra/Ultra parent needs a simple extraction | Request Luna/low with a sufficient fresh brief |
| Luna fails: missing access versus inadequate reasoning | Repair access or report the blocker in the first case; increase effort or model capability only as needed in the second |
| User explicitly permits at most two agents | Honor two as the task limit |

The review found no implicit numerical cap, slot-filling rule, fixed model role,
or arbitrary one-retry ceiling. It found one documented runtime limitation:
when Codex cannot select child settings, the effective model or effort may be
inherited. The policy requires reporting that state as unverified rather than
claiming the requested settings ran.

## Model and runtime review — September 23, 2026

The [OpenAI model catalog](https://learn.chatgpt.com/docs/models) and
[subagent guidance](https://learn.chatgpt.com/docs/agent-configuration/subagents)
now list GPT-6 Luna for focused, repeatable work and GPT-6 Sol for more demanding
coding and agent workflows. The bundled weights
prefer them over their GPT-5.6 counterparts in the same role when the runtime
actually exposes them. GPT-5.5 was excluded from automatic routing ahead of its
announced October 14 retirement. New models receive a provisional weight from
their documented role instead of a universal neutral weight.

The [Claude model guidance](https://code.claude.com/docs/en/model-config) lists
Fable for demanding long-running work and Haiku 4.5 without effort controls.
The Claude adapter applies an effort
profile only to models that support it and reports model overrides forced by
`CLAUDE_CODE_SUBAGENT_MODEL_FORCE`. It uses `/tasks` for visible model and effort
evidence as documented in the [subagent guide](https://code.claude.com/docs/en/sub-agents),
and distinguishes runtime confirmation from a configured preference.

The local clients were Codex CLI 0.155.0-alpha.16.3 and Claude Code 2.1.275 at
the start of this review. Claude Code was updated to 2.1.280, which adds Opus
5.5 support ([release notes](https://github.com/anthropics/claude-code/releases/tag/v2.1.280)).
The desktop Codex updater reported its production app current;
model availability still depends on each running tool's exposed controls.

An independent read-only pass requested GPT-6 Luna/high and reviewed eight
current routing cases. It found no conflicting instruction: a typo stays in the
parent; separate mechanical changes can proceed in useful waves; a complex
regression can use GPT-6 Sol and a distinct review; a simple extraction does not
inherit Astra/Ultra; Claude's unforced default yields to an explicit Haiku
choice; a forced model is reported as forced; and a new flagship requires a
documented reason. These are instruction checks, not proof of live model access
or measured token savings.

## Model refresh — October 5, 2026

The [current OpenAI model guide](https://learn.chatgpt.com/docs/models) and
[subagent guide](https://learn.chatgpt.com/docs/agent-configuration/subagents)
recommend GPT-6.1 Sol for demanding work. Its packaged priority is 85, below
both Luna candidates and above earlier Sol models. The Codex adapter also
lists it for ordinary implementation when lighter candidates are inadequate.
The current session's dispatch schema exposes `gpt-6.1-sol`; availability in
other sessions is not assumed.

An independent read-only review checked the
[Claude model guide](https://code.claude.com/docs/en/model-config) and
[subagent model resolution](https://code.claude.com/docs/en/sub-agents).
The adapter now records the version floors for Sonnet 5.5, Opus 5.5 and Fable
5.1, alias resolution caveats, and the medium defaults of the two 5.5 models.
Claude Code was updated from 2.1.280 to 2.1.289 using `claude update`; the local
Codex CLI was 0.160.0. These version checks do not prove account model access.

All 13 installer tests, skill validation, TOML ordering checks, and the five
profiles' YAML checks passed. Both installed skill copies matched the source;
an identical installation preview reported no changes. `claude plugin validate`
required a plugin manifest and did not validate the standalone agent directory.

## Other validation limits

The September 23 review had no active claude.ai authentication. No live Claude
model calls were made in either model refresh; authenticated profile execution
remains unverified.

Skill discovery alone does not establish automatic selection in every
conversation. Money and token savings were not measured. Routing
quality should continue to be assessed through real work and result checks.

## Live Claude Code check — October 8, 2026

Earlier reviews could not dispatch agents from Claude Code. The desktop app ran
Claude Code 2.1.293; the `claude` command on PATH was 2.1.289 and was then
updated to 2.1.295. Five minimal subagents covering the four aliases (Haiku
twice) were dispatched through the Workflow tool from the desktop session, and
their transcripts recorded the model and effort that actually ran:

| Request | Model that ran | Effort that ran |
| --- | --- | --- |
| `haiku`, no effort | `claude-haiku-5-5` | xhigh, inherited from the parent |
| `haiku`, low | `claude-haiku-5-5` | low |
| `sonnet`, low | `claude-sonnet-5-5` | low |
| `opus`, low | `claude-opus-5-5` | low |
| `fable`, low | `claude-fable-5-1` | low |

The [model guide](https://code.claude.com/docs/en/model-config) lists Haiku 5.5
with effort from low to max, a medium default and a 2.1.293 minimum. The
[subagent guide](https://code.claude.com/docs/en/sub-agents) adds a per-call
effort parameter from 2.1.292. The adapter's rule to dispatch Haiku without
effort assumed Haiku 4.5; on 2.1.293 it let a routine Haiku child run at the
parent's xhigh. Under the default `inherit` policy described below, the adapter
passes no effort, so the child runs at the parent's level. Under `per-task` it
passes an explicit effort whenever the model supports one; Haiku 4.5, which has
no effort control, is dispatched without one.

Sonnet, Opus and Fable returned the requested one-line reply. Both Haiku
children ignored that instruction and did extra work with tools. This is one
observation, not a quality benchmark, and the weights are unchanged. The check
shows dispatch for this account and session, not for other providers.

## Inherited effort by default — October 8, 2026

After the live check, effort became a configuration choice. The new `effort`
key defaults to `"inherit"`: children keep the parent session's reasoning
effort, and the router decides only whether to delegate and which model to use.
`"per-task"` keeps the previous per-subtask selection. This default was chosen
so delegated work runs at the same reasoning effort as the session that
requested it; model weights are the remaining cost control. Effort levels in
the earlier tables, such as Luna/low or Terra/medium, describe `per-task`
behavior; under the default, read them as the model with inherited effort.
Earlier statements that effort is selected per assignment, raised after a
failure, or kept from inheriting Ultra or maximum also describe `per-task`.

A second check, on Claude Code 2.1.293, dispatched Haiku through the Agent
tool with no effort field. The transcript recorded `claude-haiku-5-5` at xhigh,
the parent session's level, matching the earlier Workflow result. Codex
documents that a configured agent with an omitted effort may use its own
default, so its adapter passes the session's level when it is known.

| Scenario | Expected behavior |
| --- | --- |
| Default policy, Claude extraction on Haiku 5.5 | Haiku with no effort field or profile; it runs at the session's level |
| Default policy, Codex child whose model does not support the session's level | The highest level that model supports below it |
| Default policy, user asks for low on one extraction | Low for that assignment only |
| Default policy, session at max, user ceiling "up to high" | High, or the highest level below it the model supports |
| Default policy, child fails for lack of reasoning | Stronger model or better brief; no higher child effort unless the user asks |
| `per-task` policy | Per-subtask selection, with Claude effort profiles as fallback |
