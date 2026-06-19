#!/usr/bin/env python3
"""
Handles the intelligence layer for BioPyAI.

Sends verified sequence metadata to a local Phi-4 model via Ollama and
returns a biological interpretation. The model interprets facts that have
already been computed deterministically by the analysis layer — it never
performs calculations itself.
"""

from dataclasses import dataclass
import ollama


# The model to use. Kept as a constant so swapping models later is a
# one-line change rather than a hunt through the code.
MODEL_NAME = "phi4"

# Sets the model's role and, critically, its boundaries. The closing
# instructions enforce the grounding principle at the instruction level:
# interpret the given values, do not recompute them, and do not assert
# domain facts that cannot be derived from the data provided.
SYSTEM_PROMPT = (
    "You are a computational biology assistant specializing in "
    "immuno-oncology, helping a researcher interpret sequence analysis "
    "results. You explain the biological significance of metrics you are "
    "given through an immuno-oncology lens. The values provided to you are "
    "authoritative and were computed by dedicated bioinformatics tools — "
    "treat them as correct and do not recalculate them. Be explicit about "
    "the limits of what a given metric can tell us on its own, and do not "
    "assert specific gene functions or clinical claims that cannot be "
    "derived from the data you are given."
)


@dataclass
class LLMResult:
    """
    Uniform return type for the intelligence layer.

    success: whether an interpretation was produced
    content: the model's text response (populated on success)
    error:   a short machine-readable failure code (populated on failure),
             one of: "service_down", "model_missing", "request_failed".
             app.py maps these to user-facing messages.
    """
    success: bool
    content: str = ""
    error: str = ""


def _preflight():
    """
    Cheap pre-flight check before attempting generation.

    Distinguishes the two predictable, diagnosable failures — the Ollama
    service being unreachable, and the model not being present — so the UI
    can give targeted guidance. Returns an LLMResult.
    """
    try:
        available = ollama.list()
    except Exception:
        # Could not reach the Ollama service at all.
        return LLMResult(success=False, error="service_down")

    # ollama-python 0.6.2 returns a list under .models, each entry exposing
    # a .model attribute holding a name like "phi4:latest". The trailing
    # filter guards against any entry with a missing name.
    model_names = [m.model for m in available.models if m.model]
    if not any(name.startswith("phi4") for name in model_names):
        return LLMResult(success=False, error="model_missing")

    return LLMResult(success=True)


def _build_prompt(analyses, user_question=None):
    """
    Construct the user-role prompt from verified metrics.

    The computed metrics are listed as established facts. If the
    researcher asked a question, it is appended; otherwise we request a
    brief interpretation. Kept separate so the future streaming version
    can reuse it unchanged.
    """
    lines = "\n".join(
        f"- {label}: {value}" for label, value in analyses.items()
    )
    facts = f"The sequence has the following computed metrics:\n{lines}"

    if user_question:
        return f"{facts}\n\nThe researcher asks: {user_question}"

    return (
        f"{facts}\n\nProvide a brief biological interpretation of these "
        "results."
    )


def interpret(analyses, user_question=None):
    """
    Produce a biological interpretation of verified metrics via Phi-4.

    Args:
        analyses: a label -> value map of metrics computed by the
                  analysis layer (treated as authoritative facts)
        user_question: optional question from the researcher

    Returns:
        LLMResult — success with content, or failure with an error code
    """
    if not analyses:
        return LLMResult(success=False, error="request_failed")

    # Pre-flight first: fail fast and specifically if the service or model
    # isn't ready, before spending time on a generation call.
    check = _preflight()
    if not check.success:
        return check
    prompt = _build_prompt(analyses, user_question)

    try:
        response = ollama.chat(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )
        # Attribute access is the current idiom in the 0.6.x client;
        # dict-style response["message"]["content"] also works.
        # ollama types content as str | None — a message can legitimately
        # carry no text (e.g. a tool-call-only reply). Guard it: an empty
        # or missing generation is surfaced as a failed request, not a
        # blank "success". The guard also narrows content to str, which is
        # what satisfies the type checker.
        content = response.message.content
        if not content:
            return LLMResult(success=False, error="request_failed")
        return LLMResult(success=True, content=content)

    except Exception:
        # Service was up at pre-flight but the generation call still failed
        # (e.g. timeout, model unloaded mid-request).
        return LLMResult(success=False, error="request_failed")