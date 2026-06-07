#!/usr/bin/env python3
"""Main entry point for the AI Biopython GUI application."""

import streamlit as st
from core.input import parse_fasta_file, fetch_from_ncbi
from core.analysis import calculate_gc_content


# Page configuration — must be the first Streamlit command
st.set_page_config(
    page_title="AI Biopython GUI",
    page_icon="🧬",
    layout="wide"
)

# Application header
st.title("🧬 BioPyAI")
st.markdown("A hybrid AI application for computational biology, combining deterministic sequence analysis with language model reasoning to assist life science researchers.")

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


# Results section — displays metadata extracted from the sequence
st.subheader("Results")

if uploaded_file is not None:
    records = parse_fasta_file(uploaded_file)
    if records is None:
        st.error("Could not parse the uploaded file. Please upload a valid FASTA file.")
    else:
        gc = calculate_gc_content(records[0])
        st.success(f"GC Content: {gc}%")

elif fetch_button and accession_number:
    records = fetch_from_ncbi(accession_number)
    if records is None:
        st.error("Could not fetch sequence. Please check the accession number and try again.")
    else:
        gc = calculate_gc_content(records[0])
        st.success(f"GC Content: {gc}%")

else:
    st.info("Upload a FASTA file or fetch a sequence to see results here.")