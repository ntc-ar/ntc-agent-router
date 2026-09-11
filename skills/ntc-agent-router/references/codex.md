# Codex

Use the native subagent tool exposed in this session. Some hosts accept model
and reasoning effort per spawn; others expose configured agent types. Inspect
the actual schema rather than copying arguments from another Codex surface.

When both fields exist, select the model and its supported effort for each
assignment. If context inheritance prevents overrides, choose a supported
fresh-context invocation with a self-contained brief. Do not discard essential
context merely to select a smaller model.

In hosts with `fork_turns`, a full-history fork may reject model/effort overrides.
Use `fork_turns: "none"` with sufficient inputs, or a supported partial fork,
and set both fields. Do not omit them just to retain a full-history fork. A
parent selected as Astra/Ultra does not ask for Astra/Ultra children.

Custom TOML agents and `[agents]` defaults can affect effective settings. Read
only relevant non-secret fields when needed. A configured model with omitted
effort may use its own default; an unconfigured child can inherit the parent.
Do not label an omitted effort as automatically cheap. An explicit user model
or effort preference takes precedence over the routing heuristic.

This package installs no fixed Codex model profiles. Report unsupported controls
individually and use the available subset. Use returned runtime metadata for
confirmation; a child's statement about its identity is not evidence.

## Start with the work, then the model

The [packaged weights](../defaults.toml) prefer efficient candidates. These are
starting preferences, not a closed roster or permanent roles. Match only models
the current subagent tool accepts; the task picker can expose a different set.

| Work and acceptance check | Candidates to consider first, when exposed |
| --- | --- |
| Clear extraction, classification, mechanical edits, repeatable checks | Luna or another documented light model |
| Everyday implementation, tool use, file review, diagnosis with a few interacting steps | Terra or another balanced model |
| Ambiguous changes across components with substantial analysis | Sol or a comparable capable model |
| Hard unresolved reasoning across many constraints, after considering whether parts can be separated | Astra or another flagship, with the concrete reason recorded |

These are adequacy guides, not model/effort pairs. A light model can use medium
or high for a bounded puzzle; a capable one may need low for a narrow check.
Classify the child's actual deliverable, not the size or risk of the entire
project. Routine evidence gathering for a security review is still routine;
consequential security judgment may need a different candidate and verification.
If a preferred model is unavailable, reevaluate the remaining candidate set and
weights before selecting Astra. Use the same adequacy and escalation rules for
implementation, repairs and reviews; no model has a permanent role.

Native behavior and configuration reference:
[OpenAI subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents).
Skill discovery and reload:
[OpenAI skills](https://learn.chatgpt.com/docs/build-skills).

Reviewed 2026-09-11. The running tool schema takes precedence over examples.
