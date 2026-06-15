#!/usr/bin/env python3
"""Main entry point for the BioPyAI application."""

import streamlit as st

from core.input import parse_fasta_file, fetch_from_ncbi
from core.analysis import calculate_gc_content
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
        "GC content": calculate_gc_content(record),
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

st.divider()

# Two input methods presented side by side
col1, col2 = st.columns(2)

# Left column — local FASTA file upload
with col1:
    st.subheader("Upload a FASTA File")
    uploaded_file = st.file_uploader(
        "Choose a FASTA file",
        type=["fasta", "fa", "txt"]
    )

# Right column — remote NCBI sequence fetch
with col2:
    st.subheader("Fetch from NCBI")
    accession_number = st.text_input(
        "Enter an accession number",
        placeholder="e.g. NM_000546"
    )
    fetch_button = st.button("Fetch Sequence")

st.divider()

# --- Input handling ---------------------------------------------------
# When a sequence is loaded, store its metadata and computed analyses in
# session state (via load_sequence) so they survive the re-runs triggered
# by later button clicks.

if uploaded_file is not None:
    records = parse_fasta_file(uploaded_file)
    if records is None:
        st.error(
            "Could not parse the uploaded file. "
            "Please upload a valid FASTA file."
        )
    else:
        load_sequence(records[0])

elif fetch_button and accession_number:
    records = fetch_from_ncbi(accession_number)
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

    # Computed analyses
    st.subheader("Analysis")
    gc = st.session_state["analyses"]["GC content"]
    st.success(f"GC Content: {gc}%")

    st.divider()
    st.subheader("AI Interpretation")

    # Optional question from the researcher
    user_question = st.text_input(
        "Ask a question about this sequence (optional)",
        placeholder="e.g. What might this GC content suggest?"
    )

    # On-demand: only run Phi-4 when the user explicitly asks for it
    if st.button("Interpret with Phi-4"):
        with st.spinner("Phi-4 is interpreting the result..."):
            result = interpret(gc, user_question or None)

        if result.success:
            st.markdown(result.content)
        else:
            message = LLM_ERROR_MESSAGES.get(
                result.error, "An unexpected error occurred."
            )
            st.error(message)

else:
    st.info("Upload a FASTA file or fetch a sequence to see results here.")