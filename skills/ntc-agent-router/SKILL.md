---
name: ntc-agent-router
description: >-
  Choose whether to delegate independent work, then select available models
  and reasoning effort using configurable efficiency preferences. Use before
  spawning or reassigning subagents, for delegation planning, or to balance
  quality, time and usage in Codex or Claude Code. A trivial task needs no agent.
---

# NTC Agent Router

Keep tightly coupled work in the parent. Delegate useful independent work with
the smallest adequate combination of model, effort and context. Reassess when
new evidence changes the task. This is a decision policy, not a billing limiter.

## Discover the actual controls

Load [configuration](references/configuration.md) before routing or `status`.
It defines model weights, routing mode, enable switches and Spark quota safeguards.
If the policy is disabled, report that when asked and stop applying its routing
rules; do not change the host's ordinary behavior.

Inspect the current tool schemas and available agent descriptions. Read only
the relevant adapter: [Codex](references/codex.md) or
[Claude Code](references/claude-code.md). In another host, use its exposed
controls directly; these adapters do not add capabilities to ChatGPT web.

Record separately whether delegation, model selection, effort selection and
isolated context are available. Configured profiles are candidates until the
runtime exposes them. A picker or cached model list does not prove spawn access.
Use runtime metadata first, relevant non-secret configuration second. Do not
read credentials or probe every model. Refresh after a capability failure.

When the user has enabled an external worker connector, also read
[external workers](references/external-workers.md). Route through its exposed
tools as a separate candidate pool; external jobs share the same attempt budget.
The optional connector is not installed or enabled by the skill itself.
Within a zero-priced external pool, apply that adapter's capability-first
selection instead of the native preference for smaller models.

`status` reports those controls, active preferences and limits without spawning
agents, changing files or calling models to test access. `off` stops this policy
for the conversation; it does not disable the host's agent features.

## Decide what can run independently

Inspect enough of the task to identify dependencies and an acceptance check.
Use tools or the parent for arithmetic, tiny edits, work already answered by
context, and work whose briefing would duplicate most of the conversation.
Delegate when context isolation, specialization or parallel progress is likely
to outweigh briefing, integration and verification. Do useful local work while
children run. Do not create a planner whose only output is another delegation.

Choose roles from the work: locating evidence, implementing a bounded change,
checking a hypothesis, or reviewing a consequential result. Reuse a suitable
available agent; do not require a permanent roster or a model named after a role.
Implementation children may edit within the user's authorized scope. Assign
disjoint file ownership or an available isolated worktree. Sequence overlapping
edits. Read-only briefs also forbid connector writes; a local sandbox alone
does not enforce that boundary.

Set each brief's goal, relevant inputs, allowed scope, acceptance check and
return format. Include dependencies and uncertainties that affect correctness.
Use a fresh context when supported and the brief is sufficient. Children return
evidence, changes, checks and blockers; they do not redelegate by default.

## Select model and effort independently

Honor explicit user choices and the host's allowlist. Grade the subtask before
choosing a model: required tools/context, ambiguity, interacting constraints and
an acceptance check. The parent model, its effort and the project's importance
do not establish the child's requirements. Keep the parent settings unchanged.

Use the adapter's capability guidance and [model weights](references/configuration.md#model-weights)
to compare suitable candidates. Start with the highest-weight adequate model,
not the strongest available one. For clear, verifiable work, a suitable light
model is the first attempt; hypothetical mistakes alone do not rule it out.
For ordinary implementation with several interacting steps, consider a balanced
model before a flagship. Use a stronger model directly when the task requires
it; do not burn a token trial on a candidate already known to be inadequate.

Astra or another flagship needs a concrete reason: unresolved interacting
constraints beyond the lighter candidates, consequential judgment that cannot
be separated from the work, a demonstrated capability failure, or no suitable
alternative. A role called "reviewer", "security", "planner" or "coder" is not
that reason. Split routine extraction or implementation from difficult judgment
where useful. Explicit user model requests take precedence, including a request
to use a flagship. Weights express preferences, not prices or measured savings.

Set both model and effort through the actual controls when available. Do not
inherit an Astra/Ultra parent merely by omitting fields or forking its complete
history. Prefer a sufficient brief in fresh context. Reuse an existing agent
when its relevant context saves more work than a new route would; state that
tradeoff if it bypasses the preferred model. If selection is unavailable, report
inherited/unverified settings and avoid unnecessary extra agents.

Assess uncertainty, interacting constraints, consequence of error and how well
the result can be checked. Input length and job title alone do not decide depth.

| Evidence about this subtask | Starting reasoning depth |
| --- | --- |
| Clear rules, direct extraction, deterministic acceptance check | Lowest supported depth adequate for the check |
| Several dependent steps, ordinary diagnosis or implementation | Intermediate supported depth |
| Conflicting evidence, subtle interactions, consequential interpretation | Deeper supported depth and appropriate verification |
| Exceptionally difficult unresolved reasoning with material benefit from more analysis | Highest useful supported depth, within the task budget |

Map that depth to the chosen model's actual supported effort levels. The same
label need not mean the same work across models. Select both fields per subtask
when supported; never tie one model permanently to low, medium or high. A strong
model may need little effort for extraction; a smaller one may need more for a
bounded puzzle. Higher effort does not repair missing tools, context or access.
If an intermediate level is absent, choose the lowest supported level adequate
for the required depth; do not invent a label or jump to maximum by default.

Use xhigh, max, ultra or other supported levels when evidence justifies them,
not simply because they exist. Check whether a level also enables automatic
delegation, which may conflict with the remaining agent budget. Respect an
explicit effort ceiling. If an exact requested level is unsupported, disclose
the mismatch and choose a supported alternative only if the user's constraint
allows it; otherwise keep the work local or report the blocker.
All fallbacks, including local execution, remain subject to explicit user
constraints. If an exact setting applies to the whole task, report the blocker
instead of doing the work under different settings.

For high-consequence work, separate factual extraction from consequential
interpretation. The latter needs a capable reviewer and reliable evidence;
model size or a self-reported confidence score is not validation.

## Adapt within a finite budget

Use the configured mode, `economy` by default. It favors the least total work
likely to pass the acceptance check: adequate lighter models, compact context,
reused evidence and targeted verification. `balanced` (also `auto`) gives more
weight to avoiding likely rework and delay; `quality` permits deeper analysis or
a useful independent review when it materially improves the result. All modes
apply model weights among adequate candidates. None means "always Astra", a
fixed effort, or a minimum number of children. Conversation preferences override
configuration; persist them only when requested. Do not change host settings.

Unless the user sets a total, allow at most four child attempts per user task.
This is a configurable instruction budget, not a hard token or spending cap.
Choose concurrency each wave from ready independent tasks, actual free host
slots, remaining attempts and the parent's ability to integrate results. Count
retries, replacements and routed follow-ups that start another run. Account for
agents already working on the task; do not evade the budget through nesting,
other sessions, alternate tools or subprocesses. If the host limit is unknown,
start with one child and reassess rather than assuming unlimited slots.

Check a child's result against acceptance criteria before proceeding. When it
fails, distinguish missing evidence, inadequate instructions, access failure
and insufficient reasoning. Repair the actual cause. At most one justified
retry or escalation per subtask, within the remaining budget; then integrate
what is usable and finish locally or report the concrete blocker. A reasoning
failure can justify more effort or a stronger model; it does not require both.
Avoid retrying models already found unavailable in this conversation.

## Report what happened

For each delegation wave, state the assignment, chosen model/effort and a short
task-level reason. When choosing a lower-weight model, say what ruled out the
preferred candidate; include the concrete escalation reason for a flagship or
maximum effort. For example: "Schema inventory -> Luna/low: direct extraction;
parser fix -> Terra/medium: interacting branches with fixture checks." Report
which model/effort actually ran when exposed, plus any fallback and its cause.
Keep this in the conversation; do not add telemetry files or services by default.
Verify critical findings without duplicating all work.
Report requested settings separately from configured or runtime-confirmed
settings. Mark the effective model or effort unverified when the runtime does
not expose it. Writing a model name or "think harder" in a prompt is not a
configuration change. Do not claim savings without a measured comparable run.

Keep the user's permissions, authentication and billing method. A missing
control is not a reason to add an API bridge, rewrite profiles during a task,
or change the parent session's settings. Explicitly enabled external connectors
follow their own documented controls and restrictions. With no model/effort control, delegate
only for independence and report the inherited or unverified settings. With
no applicable native or enabled external worker tool, complete the work in the parent.
