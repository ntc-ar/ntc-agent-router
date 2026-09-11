# Validation

Initial review: September 4, 2026.

## Design review

The original kit was usable as a delegation policy. Its capability checks and
distinction between requested and confirmed models were useful. Routing was
limited by a small fixed set of model/effort combinations, read-only agents,
and support for OpenAI only.

This version keeps capability checks and selects settings per subtask. Agents
can implement changes within a defined scope. Claude Code uses effort profiles
that allow independent model selection. Delegation continues according to the
expected value of the next distinct assignment instead of a default attempt cap.

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
| Model supports low/high but not medium | Select a supported level adequate for the task |
| Essential evidence is inaccessible | Identify the blocker; more effort does not grant access |
| Exact model and effort requested, combination unsupported | Report the blocker without substituting settings |
| Explicit two-agent limit, one completed and one failed | Finish locally within the user's constraints |
| Claude has no per-call effort control | Select a compatible profile without inventing parameters |
| Environment forces the model | Distinguish the request from effective configuration |
| Four useful agents completed and a distinct regression check remains | Start another adequate agent; count alone is not a stop condition |
| Slots remain but proposed work duplicates completed review | Do not delegate |

The evaluation found ambiguities in effort inheritance and fallback to the
parent. The policy was updated so these paths always respect exact user choices
and limits, even when those constraints prevent completion.

## Weighted routing evaluation — September 8, 2026

Real usage showed that the original "smallest adequate model" guidance did not
consistently prevent flagship selection. It also left ordinary agents open to
inheriting a flagship parent and maximum effort. The revised policy adds an
economy default, configurable selection weights, explicit model/effort dispatch
and a concrete reason for escalation. No host defaults or billing controls change.

An independent instruction-level evaluation applied the revised package to
fifteen scenarios without performing the simulated tasks or spawning children:

| Scenario | Observed decision |
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
| Claude extraction with model selector and effort profiles | Haiku with the low profile and explicit model |
| Boolean used as a model weight | Reject configuration before routing |
| Unlisted light model exposed with suitable capability metadata | Use its neutral weight; select it over Astra |
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

## Other validation limits

Claude Code 2.1.195 was installed without active authentication. Files, locally
accepted fields, and installation were checked; running the profiles in an
authenticated Claude Code session remains pending.

Skill discovery alone does not establish automatic selection in every
conversation. Money and token savings were not measured. Routing
quality should continue to be assessed through real work and result checks.
