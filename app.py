#!/usr/bin/env python3
"""Main entry point for the AI Biopython GUI application."""

import streamlit as st


# Page configuration — must be the first Streamlit command
st.set_page_config(
    page_title="AI Biopython GUI",
    page_icon="🧬",
    layout="wide"
)

# Application header
st.title("🧬 AI Biopython GUI")
st.markdown("A computational biology tool for life science researchers.")

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

# Results placeholder — replaced with actual data once input is provided
st.subheader("Results")
st.info("Upload a FASTA file or fetch a sequence to see results here.")