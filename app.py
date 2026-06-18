#!/usr/bin/env python3
"""Main entry point for the BioPyAI application."""

import streamlit as st

from core.input import parse_fasta_file, fetch_from_ncbi
from core.analysis import ANALYSES, scan_sirna_candidates
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
    """Store a parsed SeqRecord in session state.

    Loading is decoupled from analysis: we keep the record itself so the
    selected analyses can be computed on demand from the menu, and the
    summary card derives its identity fields from the same record. The
    record is the single source of truth for "a sequence is loaded".
    """
    st.session_state["record"] = record
    # Drop any candidate scan from a previously loaded sequence so its
    # stale results don't show against the new one.
    st.session_state.pop("sirna_candidates", None)


# Page configuration — must be the first Streamlit command
st.set_page_config(
    page_title="BioPyAI",
    page_icon="🧬",
    layout="wide"
)


# Per-metric method notes, surfaced as tooltips. They describe what each
# value measures and how it is computed — deliberately not its biological
# meaning, which is the interpretation layer's job. Inline here for now;
# if they multiply or need to travel with the metrics, they fold into the
# ANALYSES registry (the per-metric metadata seam).
METRIC_HELP = {
    "GC content (%)": (
        "Percentage of G and C bases across the full sequence, computed "
        "from the base counts."
    ),
    "Molecular weight (g/mol)": (
        "Molecular weight assuming a single-stranded DNA molecule "
        "(Biopython's molecular_weight, seq_type='DNA')."
    ),
}

# Column tooltips for the candidate table. Position and Sequence are
# identity fields; GC and Tm are per-window metrics (the GC note here is
# window-scoped, distinct from the whole-sequence note above).
CANDIDATE_COLUMN_CONFIG = {
    "Position": st.column_config.NumberColumn(
        "Position",
        help="1-based start position of the window on the target.",
    ),
    "Sequence": st.column_config.TextColumn(
        "Sequence",
        help="The scanned target-strand window, in DNA letters.",
    ),
    "GC content (%)": st.column_config.NumberColumn(
        "GC content (%)",
        help=(
            "Percentage of G and C bases in the window, computed from "
            "the base counts."
        ),
    ),
    "Tm (°C)": st.column_config.NumberColumn(
        "Tm (°C)",
        help=(
            "Duplex melting temperature from RNA nearest-neighbor "
            "thermodynamics (RNA_NN1, Freier 1986). Comparative across "
            "candidates; the absolute value depends on salt and strand "
            "conditions."
        ),
    ),
    "5'-end asymmetry (ΔTm, °C)": st.column_config.NumberColumn(
        "5'-end asymmetry (ΔTm, °C)",
        help=(
            "Difference in RNA nearest-neighbor melting temperature "
            "between the duplex's two terminal segments (5' end minus "
            "3' end, RNA_NN1). A thermodynamic measure of end-asymmetry, "
            "comparative across candidates."
        ),
    ),
    "GC 30-52%": st.column_config.CheckboxColumn(
        "GC 30-52%",
        help=(
            "GC content is within the 30-52% window favoured by Reynolds "
            "(2004) — a duplex-stability sweet spot."
        ),
    ),
    "Guide 5' A/U": st.column_config.CheckboxColumn(
        "Guide 5' A/U",
        help=(
            "The guide's 5' base (complement of the window's 3' base) is "
            "A or U — a weak guide 5' end (Ui-Tei 2004)."
        ),
    ),
    "Sense 5' G/C": st.column_config.CheckboxColumn(
        "Sense 5' G/C",
        help=(
            "The window's 5' base is G or C — a strong sense 5' end "
            "(Ui-Tei 2004)."
        ),
    ),
    "Guide 5' AU-rich": st.column_config.CheckboxColumn(
        "Guide 5' AU-rich",
        help=(
            "At least 4 A/U among the guide's 5' 7 nt (the window's 3' "
            "7 nt) (Ui-Tei 2004)."
        ),
    ),
    "U at 10": st.column_config.CheckboxColumn(
        "U at 10",
        help=(
            "Sense position 10 is U — the cleavage-site preference "
            "(Reynolds 2004), opposite the AGO2 scissile site."
        ),
    ),
    "No 4+ run": st.column_config.CheckboxColumn(
        "No 4+ run",
        help=(
            "No run of 4 or more identical bases — guards low-complexity, "
            "structure-prone sequence (Reynolds 2004)."
        ),
    ),
}


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
sequence_loaded = "record" in st.session_state

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
        for key in ("record", "sirna_candidates"):
            st.session_state.pop(key, None)
        # Bump the input generation so the uploader, accession box,
        # analysis menu, and scan controls re-instantiate at their
        # defaults (session-state alone can't clear a lingering upload).
        st.session_state["input_gen"] = (
            st.session_state.get("input_gen", 0) + 1
        )
        sequence_loaded = False

input_label = (
    "Load a different sequence" if sequence_loaded
    else "Provide a sequence"
)

# Generation counter — changing it re-instantiates the input widgets, the
# analysis menu, and the scan controls at their defaults, which is how
# Reset clears them.
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
# When a sequence is loaded, store the record in session state (via
# load_sequence) so it survives later re-runs.

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
# Vertical flow: a full-width summary card, then Analysis (whole-sequence
# metrics held to a narrow column, site-specific scan full-width), then a
# full-width AI Interpretation section beneath.

if "record" in st.session_state:
    record = st.session_state["record"]

    # Sequence summary card — derives the identity fields straight from
    # the stored record. Purely presentational.
    with st.container(border=True):
        st.markdown("**Sequence summary**")

        # The FASTA description includes the ID as its first token; trim
        # it so the ID isn't shown twice.
        description = record.description
        if description.startswith(record.id):
            description = description[len(record.id):].strip()

        for label, value in (
            ("ID", record.id),
            ("Description", description or "—"),
            ("Length", f"{len(record.seq)} bp"),
        ):
            label_col, value_col = st.columns([1, 4])
            label_col.markdown(f"**{label}**")
            value_col.write(value)

    # ===== Analysis =====================================================
    st.subheader("Analysis")

    # --- Whole-sequence metrics: scalar properties of the full sequence.
    # Held to a narrow column so the result boxes don't stretch.
    st.markdown(
        "**Whole-sequence metrics** "
        ":gray[(computed on the full sequence)]"
    )

    ws_col, _ = st.columns([2, 3])

    # Menu of available analyses, drawn from the registry. Keyed to
    # the input generation so Reset returns it to the default.
    with ws_col:
        selected = st.multiselect(
            "Analyses",
            options=list(ANALYSES.keys()),
            label_visibility="collapsed",
            help="Metrics computed on the full loaded sequence.",
            key=f"analyses_select_{input_gen}",
        )

        analyses = {label: ANALYSES[label](record) for label in selected}

        if analyses:
            for label, value in analyses.items():
                st.metric(label, value, help=METRIC_HELP.get(label))
        else:
            st.info("Select one or more analyses to run.")

    # --- Per-candidate metrics: sliding-window scan, full-width table.
    st.markdown(
        "**Per-candidate metrics** "
        ":gray[(sliding-window scan along the target)]"
    )

    win_col, scan_col = st.columns([1, 2], vertical_alignment="bottom")

    with win_col:
        window = st.number_input(
            "Window length (nt)",
            min_value=15,
            max_value=30,
            value=21,
            step=1,
            help=(
                "Length of each candidate window in nucleotides. 21 nt "
                "is a common full-length siRNA (~19 bp duplex + 2 nt "
                "overhangs)."
            ),
            key=f"sirna_window_{input_gen}",
        )
    with scan_col:
        scan_clicked = st.button("Scan for candidates")

    # Button-triggered (heavier than the instant whole-sequence metrics),
    # so results are cached to survive later reruns. Cleared on Reset and
    # when a different sequence is loaded.
    if scan_clicked:
        with st.spinner("Scanning windows..."):
            st.session_state["sirna_candidates"] = scan_sirna_candidates(
                record, window
            )

    if "sirna_candidates" in st.session_state:
        candidates = st.session_state["sirna_candidates"]
        if candidates:
            st.caption(
                f"{len(candidates)} candidates — click a column "
                "header to sort."
            )
            st.dataframe(
                candidates,
                width='stretch',
                hide_index=True,
                column_config=CANDIDATE_COLUMN_CONFIG,
            )
        else:
            st.info(
                "The sequence is shorter than the window length — "
                "no candidates."
            )

    # ===== AI Interpretation ===========================================
    # Full-width so the model's prose reads comfortably. For now it
    # interprets the whole-sequence metrics; interpreting a selected
    # candidate is a later pass.
    st.subheader("AI Interpretation")

    # Optional question. Label collapsed; guidance sits in the caption.
    user_question = st.text_input(
        "Question for Phi-4",
        placeholder="e.g. What might these metrics suggest?",
        label_visibility="collapsed",
    )

    # Disabled until at least one whole-sequence metric is selected.
    if st.button("Interpret with Phi-4", disabled=not analyses):
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