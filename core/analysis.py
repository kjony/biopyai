#!/usr/bin/env python3
"""
Handles sequence analysis for BioPyAI.

Computes deterministic metrics from Biopython SeqRecord objects. Each
metric is a small function taking a SeqRecord and returning a numeric
value (or None on failure). The ANALYSES registry maps a display label
to its function, so adding a metric is a new function plus one registry
entry — not a change to the callers that render or interpret results.
"""

from Bio.SeqUtils import gc_fraction, molecular_weight
from Bio.SeqUtils import MeltingTemp as mt


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
        return round(gc_fraction(record.seq) * 100, 2)

    except Exception:
        return None


def calculate_molecular_weight(record):
    """
    Calculate the molecular weight of a sequence.

    Treats the sequence as single-stranded DNA (FASTA nucleotide records
    use DNA letters). A general whole-sequence property, included to
    exercise the multi-metric path; the siRNA-specific, per-candidate
    metrics arrive with the windowing slice later.

    Args:
        record: A Biopython SeqRecord object

    Returns:
        Molecular weight in g/mol rounded to two decimal places,
        or None if calculation fails
    """
    try:
        return round(molecular_weight(record.seq, seq_type="DNA"), 2)

    except Exception:
        return None


def scan_sirna_candidates(record, window=21):
    """Slide a window along the sequence, one candidate per position.

    Returns a list of flat dicts — one per window — each carrying the
    window's position and target-strand sequence plus its computed
    metrics. "Position" and "Sequence" are identity fields; every other
    key is a metric, so a selected candidate's metrics map directly onto
    the interpretation layer later.

    Only GC content is computed for now; the duplex-thermodynamic metrics
    (Tm, end-asymmetry) arrive in the next pass.

    Args:
        record: A Biopython SeqRecord object
        window: candidate length in nucleotides (default 21)

    Returns:
        A list of candidate dicts (empty if the sequence is shorter than
        the window).
    """
    seq = str(record.seq).upper()
    candidates = []

    for start in range(len(seq) - window + 1):
        sub = seq[start:start + window]
        candidates.append({
            "Position": start + 1,
            "Sequence": sub,
            "GC content (%)": round(gc_fraction(sub) * 100, 2),
            "Tm (°C)": _duplex_tm(sub),
        })

    return candidates


def _duplex_tm(seq):
    """Melting temperature (°C) of the RNA duplex for a candidate window.

    Uses RNA nearest-neighbor thermodynamics (RNA_NN1, Freier 1986).
    Biopython normalizes the sequence internally, so passing the
    DNA-lettered window is fine. Default salt/strand concentrations are
    used: absolute Tm depends on those conditions, but the relative
    ordering across candidates — which is what ranking needs — is robust.
    Returns None if the window can't be scored (e.g. ambiguous bases).
    """
    try:
        return round(mt.Tm_NN(seq, nn_table=mt.RNA_NN1), 1)
    except Exception:
        return None


# Registry of available analyses: display label -> function. The label
# carries its unit so the rendering and interpretation layers stay generic
# (every entry is formatted the same way). Adding an analysis is a new
# function plus one entry here — the seam the menu and siRNA panel build on.
ANALYSES = {
    "GC content (%)": calculate_gc_content,
    "Molecular weight (g/mol)": calculate_molecular_weight,
}