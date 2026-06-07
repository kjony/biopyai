#!/usr/bin/env python3
"""
Handles sequence input for BioPyAI.

Supports two input methods:
    - Local FASTA file upload via Streamlit
    - Remote sequence fetch from NCBI Entrez
"""

from Bio import SeqIO, Entrez
from io import StringIO


# NCBI Entrez retry settings for robust API compliance
Entrez.max_tries = 3
Entrez.sleep_between_tries = 15


def parse_fasta_file(uploaded_file):
    """
    Parse a FASTA file uploaded via Streamlit.

    Args:
        uploaded_file: File object returned by st.file_uploader()

    Returns:
        List of SeqRecord objects, or None if parsing fails
    """
    try:
        # Decode the uploaded bytes into a plain string
        content = uploaded_file.read().decode("utf-8")

        # Wrap the string in StringIO so SeqIO can treat it as a file
        records = list(SeqIO.parse(StringIO(content), "fasta"))

        if not records:
            return None

        return records

    except Exception as e:
        return None


def fetch_from_ncbi(accession_number):
    """
    Fetch a sequence from NCBI by accession number.

    Args:
        accession_number: A valid NCBI accession number (e.g. NM_000546)

    Returns:
        List of SeqRecord objects, or None if the request fails
    """
    try:
        # Open a handle to the NCBI Entrez API
        handle = Entrez.efetch(
            db="nucleotide",
            id=accession_number,
            rettype="fasta",
            retmode="text"
        )

        # Parse the response into SeqRecord objects
        records = list(SeqIO.parse(handle, "fasta"))

        # Always close the handle after use to free the connection
        handle.close()

        if not records:
            return None

        return records

    except Exception as e:
        return None
