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


def preflight():
    """
    Cheap pre-flight check before attempting generation.

    Distinguishes the two predictable, diagnosable failures — the Ollama
    service being unreachable, and the model not being present — so the UI
    can give targeted guidance. Returns an LLMResult.
    """
    try:
        available = ollama.list()
    except Exception:
        return LLMResult(success=False, error="service_down")
    model_names = [m.model for m in available.models if m.model]
    if not any(name.startswith("phi4") for name in model_names):
        return LLMResult(success=False, error="model_missing")
    return LLMResult(success=True)
  

def _build_prompt(analyses):
    """Format a single fact set as labelled lines (data only)."""
    lines = "\n".join(
        f"- {label}: {value}" for label, value in analyses.items()
    )
    return f"Computed metrics:\n{lines}"


def _build_shortlist_prompt(candidates):
    """Format a candidate shortlist as labelled blocks (data only)."""
    blocks = []
    for candidate in candidates:
        lines = "\n".join(
            f"  - {label}: {value}"
            for label, value in candidate.items()
            if label != "Position"
        )
        blocks.append(
            f"Candidate at position {candidate['Position']}:\n{lines}"
        )
    return "Candidate metrics:\n\n" + "\n\n".join(blocks)


def build_opening_message(facts, user_question):
    """Assemble the opening message: verified facts, then the question.

    The fact builders emit only computed data; the framing and the ask
    arrive through `user_question`, so the data layer stays domain-neutral
    and the interpretive lens is supplied at the call site.
    """
    body = (
        _build_shortlist_prompt(facts) if isinstance(facts, list)
        else _build_prompt(facts)
    )
    return f"{body}\n\n{user_question}"


def stream_converse(messages):
    """Stream a grounded conversation reply, yielding text chunks.

    Assumes preflight() has already passed. The system prompt is prepended
    so its grounding and boundary clauses govern every turn. A mid-stream
    failure ends the stream rather than raising into the UI; preflight()
    covers the predictable failures up front.
    """
    try:
        stream = ollama.chat(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                *messages,
            ],
            stream=True,
        )
        for chunk in stream:
            text = chunk.message.content
            if text:
                yield text
    except Exception:
        return