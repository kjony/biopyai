#!/usr/bin/env python3
"""Main entry point for the BioPyAI application."""

import streamlit as st

from core.input import parse_fasta_file, fetch_from_ncbi
from core.analysis import ANALYSES
from core.llm import interpret


# Maps the intelligence layer's error codes to user-facing messages.
# Keeping this in the UI layer means llm.py stays free of presentation
# concerns — it reports what failed, app.py decides how to say it.
LLM_ERROR_MESSAGES = {
    "service_down": (
        "Could not reach the local AI service. Make sure Ollama is "
        "running (try `ollama serve` in a terminal)."
    ),
    "model_missing": (
        "The Phi-4 model isn't available. Download it with "
        "`ollama pull phi4`."
    ),
    "request_failed": (
        "The interpretation request failed. Please try again — if the "
        "sequence is very long, it may have timed out."
    ),
}


def load_sequence(record):
    """Populate session state from a parsed SeqRecord.

    Stores two collections, deliberately shaped so that future metadata
    fields and additional analyses extend them rather than restructure
    them:

      - sequence_meta: descriptive identity of the loaded sequence
      - analyses:      a label -> value map of computed results

    Only GC content is computed today, but the collection shape means a
    second or third analysis is an added entry, not a rewrite.
    """
    st.session_state["sequence_meta"] = {
        "id": record.id,
        "description": record.description,
        "length": len(record.seq),
    }
    st.session_state["analyses"] = {
        label: fn(record) for label, fn in ANALYSES.items()
    }


# Page configuration — must be the first Streamlit command
st.set_page_config(
    page_title="BioPyAI",
    page_icon="🧬",
    layout="wide"
)

# Application header
st.title("🧬 BioPyAI")
st.markdown(
    "A hybrid AI application for computational biology, combining "
    "deterministic sequence analysis with language model reasoning to "
    "assist life science researchers."
)

# Whether a sequence is loaded as this run begins. Computed here so the
# reset control and the input/results sections below all read a single,
# consistent value.
sequence_loaded = "analyses" in st.session_state

# --- Input stage ------------------------------------------------------
# The "Sequence Input" heading carries a Reset button on its right, shown
# only when a sequence is loaded. Reset clears state before the input and
# results sections run below, so a single pass reflects it — no rerun.
# The input itself lives in an expander that defaults open when nothing is
# loaded and recedes once a sequence is loaded.
title_col, reset_col = st.columns([6, 1], vertical_alignment="bottom")

with title_col:
    st.subheader("Sequence Input")

with reset_col:
    if sequence_loaded and st.button("Reset"):
        for key in ("analyses", "sequence_meta"):
            st.session_state.pop(key, None)
        # Bump the input generation so the uploader/accession box
        # re-instantiate empty (session-state alone can't clear a
        # lingering upload).
        st.session_state["input_gen"] = (
            st.session_state.get("input_gen", 0) + 1
        )
        sequence_loaded = False

input_label = (
    "Load a different sequence" if sequence_loaded
    else "Provide a sequence"
)

# Generation counter — changing it re-instantiates the input widgets as
# empty, which is how Reset clears a lingering upload.
input_gen = st.session_state.get("input_gen", 0)

with st.expander(input_label, expanded=not sequence_loaded):
    upload_col, fetch_col = st.columns(2)

    with upload_col:
        st.markdown("**Upload a FASTA file**")
        uploaded_file = st.file_uploader(
            "Choose a FASTA file",
            type=["fasta", "fa", "txt"],
            label_visibility="collapsed",
            key=f"upload_{input_gen}",
        )

    with fetch_col:
        st.markdown("**Fetch from NCBI**")
        accession_number = st.text_input(
            "Enter an accession number",
            placeholder="e.g. NM_000546",
            label_visibility="collapsed",
            key=f"accession_{input_gen}",
        )
        fetch_button = st.button("Fetch Sequence")

# --- Input handling ---------------------------------------------------
# When a sequence is loaded, store its metadata and computed analyses in
# session state (via load_sequence) so they survive later re-runs.

# Normalize the typed accession once, so stray whitespace neither passes
# the fetch guard nor gets sent to NCBI.
accession = accession_number.strip()

if uploaded_file is not None:
    records = parse_fasta_file(uploaded_file)
    if records is None:
        st.error(
            "Could not parse the uploaded file. "
            "Please upload a valid FASTA file."
        )
    else:
        load_sequence(records[0])

elif fetch_button and accession:
    records = fetch_from_ncbi(accession)
    if records is None:
        st.error(
            "Could not fetch sequence. Please check the "
            "accession number and try again."
        )
    else:
        load_sequence(records[0])

# --- Results and interpretation ---------------------------------------

if "analyses" in st.session_state:
    meta = st.session_state["sequence_meta"]

    # Sequence summary card — renders the identity metadata stored on
    # load. Purely presentational: no new extraction logic, it reads
    # what load_sequence() already placed in session state.
    with st.container(border=True):
        st.markdown("**Sequence summary**")

        # The FASTA description includes the ID as its first token; trim
        # it so the ID isn't shown twice.
        description = meta["description"]
        if description.startswith(meta["id"]):
            description = description[len(meta["id"]):].strip()

        for label, value in (
            ("ID", meta["id"]),
            ("Description", description or "—"),
            ("Length", f"{meta['length']} bp"),
        ):
            label_col, value_col = st.columns([1, 4])
            label_col.markdown(f"**{label}**")
            value_col.write(value)

   # All computed analyses for this sequence.
    analyses = st.session_state["analyses"]

    # Analysis (left) and AI interpretation (right), side by side —
    # deterministic result paired with language-model reasoning.
    analysis_col, interp_col = st.columns(2)

    with analysis_col:
        st.subheader("Analysis")
        st.caption("Deterministic sequence metrics")
        for label, value in analyses.items():
            st.success(f"{label}: {value}")

    with interp_col:
        st.subheader("AI Interpretation")
        st.caption("Ask Phi-4 to interpret the result (optional)")

        # Optional question. Label collapsed so the input aligns with the
        # Analysis panel; guidance sits in the caption above.
        user_question = st.text_input(
            "Question for Phi-4",
            placeholder="e.g. What might this GC content suggest?",
            label_visibility="collapsed",
        )

        # On-demand: only run Phi-4 when the user explicitly asks for it
        if st.button("Interpret with Phi-4"):
            with st.spinner("Phi-4 is interpreting the results..."):
                result = interpret(analyses, user_question or None)

            if result.success:
                st.markdown(result.content)
            else:
                message = LLM_ERROR_MESSAGES.get(
                    result.error, "An unexpected error occurred."
                )
                st.error(message)

else:
    st.info("Upload a FASTA file or fetch a sequence to see results here.")