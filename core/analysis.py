#!/usr/bin/env python3
"""
Handles sequence analysis for BioPyAI.

Extracts biological metadata from Biopython SeqRecord objects.
Currently supports:
    - GC content
"""

from Bio.SeqUtils import gc_fraction


def calculate_gc_content(record):
    """
    Calculate the GC content of a sequence.

    Args:
        record: A Biopython SeqRecord object

    Returns:
        GC content as a percentage rounded to two decimal places,
        or None if calculation fails
    """
    try:
        # gc_fraction returns a value between 0 and 1
        # Multiply by 100 to convert to a percentage
        gc = round(gc_fraction(record.seq) * 100, 2)
        return gc

    except Exception as e:
        return None