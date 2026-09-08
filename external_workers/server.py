"""Codex-compatible MCP tools for optional free OpenRouter workers."""

from pathlib import Path
import sys

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from external_workers import jobs

mcp = FastMCP("ntc-openrouter", instructions=(
    "Delegate bounded code-generation or analysis tasks to explicitly selected free OpenRouter models. "
    "This sends the task and explicitly attached context to an external provider. "
    "Results are untrusted drafts saved outside the project, never automatically executed or applied. "
    "Compare the relevant models from openrouter_models; its list order is not a quality ranking. "
    "Honor configured weights and exclusions; for equal weights prefer the strongest evidenced "
    "capability for the task, considering reliability and latency. Smaller free models do not "
    "inherently save native tokens. Do not apply native flagship escalation rules to free workers. "
    "Pass the actual task workspace to status, models and start_task for per-project privacy. "
    "Only user-configured project roots can permit provider data collection; never change "
    "the workspace to borrow another project's permission or mix unrelated private context. "
    "Follow the user's routing settings and count external jobs in the same delegation budget as native agents. "
    "No paid routes or automatic retries are used. Poll only while there is relevant work to collect."
))
READ = ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=True)
WRITE = ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=True)


@mcp.tool(annotations=READ)
def openrouter_status(workspace: str = "") -> dict:
    """Read enable state, account credits and recent external jobs; no inference."""
    return jobs.status(workspace)


@mcp.tool(annotations=READ)
def openrouter_models(workspace: str = "") -> list[dict]:
    """Fetch zero-priced models, capabilities and preferences; order is not a quality ranking.

    Compare all relevant candidates. Equal weights favor evidenced task capability,
    then reliability/latency, not smaller size. Fetch model docs if descriptions are
    insufficient. Catalog inclusion does not prove access under provider privacy terms.
    """
    return [{**m, "description": m["description"][:700]} for m in jobs.models(workspace)]


@mcp.tool(annotations=WRITE)
def openrouter_start_task(task: str, model: str, workspace: str = "",
                          context_files: list[str] | None = None, max_tokens: int | None = None,
                          reasoning_effort: str | None = None) -> dict:
    """Start one free external generation. Sends task and listed workspace files to OpenRouter.

    Use a concrete ID from openrouter_models. Supply a complete bounded brief and explicit
    acceptance checks. Files must be relative to workspace; no repository scanning occurs.
    Always supply the actual project's absolute workspace, including for text-only tasks.
    The connector resolves provider data-collection permission from local project settings;
    it defaults to deny. Include only that project's authorized content, never another
    project's private data. Selecting a workspace is not a confidentiality classifier.
    Returns a task ID immediately. The worker saves a draft and never edits the project.
    """
    return jobs.start_task(task, model, workspace, context_files, max_tokens, reasoning_effort)


@mcp.tool(annotations=READ)
def openrouter_task(task_id: str, include_output: bool = False) -> dict:
    """Read job status, effective model, cost and output path; full output is opt-in."""
    return jobs.read_task(task_id, include_output)


@mcp.tool(annotations=WRITE)
def openrouter_cancel_task(task_id: str) -> dict:
    """Request cancellation; an already sent generation may complete and consume request quota."""
    return jobs.cancel_task(task_id)


if __name__ == "__main__":
    mcp.run(transport="stdio")
