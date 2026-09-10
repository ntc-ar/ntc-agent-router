# Validation

Initial review: September 4, 2026.

## Design review

The original kit was usable as a delegation policy. Its capability checks and
distinction between requested and confirmed models were useful. Routing was
limited by four fixed model/effort combinations, read-only agents, and support
for OpenAI only.

This version keeps capability checks and selects settings per subtask. Agents
can implement changes within a defined scope. Codex favors Spark for verifiable
implementation work; Claude Code uses effort profiles that allow independent
model selection. The Spark preference can be disabled and does not require an
unavailable model.

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
- Ran native implementation requesting GPT-5.3-Codex-Spark with medium effort:
  the CI workflow and a test adjustment for macOS temporary directories.
  Reviewed the changes and passed all thirteen tests.

The two delegated runs checked execution and results. The control accepted the
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
| Two attempts allowed, one completed and one failed | Finish locally within the user's constraints |
| Claude has no per-call effort control | Select a compatible profile without inventing parameters |
| Environment forces the model | Distinguish the request from effective configuration |
| Spark available for bounded implementation | Prefer it and review the resulting code |
| Spark quota exhausted or repeated errors | Fix the cause or choose another route within the budget |

The evaluation found ambiguities in effort inheritance and fallback to the
parent. The policy was updated so these paths always respect exact user choices
and limits, even when those constraints prevent completion.

## Configurable quota checks

An additional instruction-level evaluation covered ten quota/configuration
scenarios: a low five-hour window, a low weekly window despite a five-hour reset,
exact reserve equality, missing weekly telemetry, known exhaustion with unknown
quota allowed, enable-switch precedence, per-key project/conversation overrides,
partial edits after throttling, exact-model constraints, and invalid settings.

The evaluated policy excludes Spark at or below the reserve in either window,
honors fallback/stop settings, and does not treat unknown quota as unlimited.
Packaged and local TOML settings were parsed, and local preferences were checked
for preservation across installation. These checks do not enforce a platform
quota or predict the consumption of an active agent.

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
| Spark would win, weekly reserve reached, stop configured | Stop before replacement work |
| Spark disabled with stop configured | Ordinary non-Spark routing, Terra/medium |
| Project overrides one user model weight | Merge per key; preserve other user weights |
| Terra fails a cross-module concurrency acceptance check | One targeted escalation to Sol/high |
| Adequate Terra outranks exhausted Spark with stop configured | Terra; Spark's stop rule does not trigger |
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
was economy and the existing 20% Spark reserve/fallback policy was preserved.
Reinstalled in Codex and Claude Code, verified both copies against the source,
confirmed an identical dry run made no changes, and checked that the personal
configuration file retained its SHA-256 hash.

## Other validation limits

Claude Code 2.1.195 was installed without active authentication. Files, locally
accepted fields, and installation were checked; running the profiles in an
authenticated Claude Code session remains pending.

Skill discovery alone does not establish automatic selection in every
conversation. Money, token, and quota savings were not measured. Routing
quality should continue to be assessed through real work and result checks.
