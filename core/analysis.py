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

# RNA nearest-neighbor table used for all duplex-stability metrics
# (Tm and end-asymmetry). Centralized so swapping it — e.g. to
# mt.RNA_NN3 (Chen 2012) — is a one-line change. RNA_NN1 is Freier 1986.
RNA_NN_TABLE = mt.RNA_NN1

# Terminal base pairs compared at each duplex end when scoring 5'-end
# asymmetry. Adjustable; ~4 is common siRNA-design practice.
TERMINAL_BP = 4


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
        candidate = {
            "Position": start + 1,
            "Sequence": sub,
            "GC content (%)": round(gc_fraction(sub) * 100, 2),
            "Tm (°C)": _duplex_tm(sub),
            "5'-end asymmetry (ΔTm, °C)": _end_asymmetry(sub),
        }
        candidate.update(_sequence_rules(sub))
        candidates.append(candidate)
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
        # was: nn_table=mt.RNA_NN1
        return round(mt.Tm_NN(seq, nn_table=RNA_NN_TABLE), 1)
    except Exception:
        return None
    

def _end_asymmetry(seq):
    """5'-end thermodynamic asymmetry of the candidate's siRNA duplex.

    Strand selection (Khvorova 2003, Schwarz 2003): the strand whose 5'
    end is the less stable is preferentially loaded into RISC as the
    guide. The guide is the reverse complement of this target window, so
    its 5' end pairs with the window's 3' end. We compare the stability
    of the two duplex ends over the terminal TERMINAL_BP base pairs,
    using the same RNA nearest-neighbor melting temperature as the Tm
    column:

        asymmetry = Tm(5' terminal segment) - Tm(3' terminal segment)

    A positive value means the window's 5' end (passenger 5') is more
    stable than its 3' end (guide 5') -- the arrangement that favours
    loading the intended guide. Expressed as a Tm difference (deg C),
    monotonic with the free-energy asymmetry; used comparatively across
    candidates, not as an absolute quantity. None if a segment can't be
    scored.
    """
    if len(seq) < 2 * TERMINAL_BP:
        return None
    try:
        tm_5 = mt.Tm_NN(seq[:TERMINAL_BP], nn_table=RNA_NN_TABLE)
        tm_3 = mt.Tm_NN(seq[-TERMINAL_BP:], nn_table=RNA_NN_TABLE)
        return round(tm_5 - tm_3, 1)
    except Exception:
        return None    

def _has_run(seq, n):
    """True if any base repeats n or more times consecutively."""
    run = 1
    for a, b in zip(seq, seq[1:]):
        run = run + 1 if a == b else 1
        if run >= n:
            return True
    return False


def _sequence_rules(seq):
    """Empirical siRNA design-rule flags for a target (sense) window.

    Each value is a deterministic yes/no fact drawn from the rational-
    design rule sets (Ui-Tei 2004, Reynolds 2004). They are heuristics,
    not predictions, and are presented as individual flags rather than a
    summed score, so the researcher sees which criteria a candidate meets
    and can sort or filter on the ones they trust. Positions are counted
    from the 5' end of the sense window; the rules were derived for
    ~19-21mers. A/U in the RNA duplex corresponds to A/T in the DNA-
    lettered window.
    """
    seq = seq.upper()
    gc = gc_fraction(seq) * 100
    au = set("AT")
    return {
        "GC 30-52%": 30 <= gc <= 52,
        "Guide 5' A/U": seq[-1] in au,
        "Sense 5' G/C": seq[0] in {"G", "C"},
        "Guide 5' AU-rich": sum(b in au for b in seq[-7:]) >= 4,
        "U at 10": len(seq) >= 10 and seq[9] == "T",
        "No 4+ run": not _has_run(seq, 4),
    }


# Registry of available analyses: display label -> function. The label
# carries its unit so the rendering and interpretation layers stay generic
# (every entry is formatted the same way). Adding an analysis is a new
# function plus one entry here — the seam the menu and siRNA panel build on.
ANALYSES = {
    "GC content (%)": calculate_gc_content,
    "Molecular weight (g/mol)": calculate_molecular_weight,
}