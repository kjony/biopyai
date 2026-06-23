# 🧬 BioPyAI

**A local, hybrid AI application for computational biology — combining deterministic sequence analysis with (locally-run) language model reasoning to assist life science researchers.**

BioPyAI keeps facts and interpretation in separate lanes. [Biopython](https://biopython.org/) computes exact, reproducible metrics over a nucleotide sequence; [Phi-4](https://ollama.com/library/phi4), running locally through [Ollama](https://ollama.com/), then reasons over those verified numbers and explains them. The model never invents or recomputes a quantity — it only interprets values the deterministic layer has already established. Everything runs on your machine.

> **This is a research and learning aid, not a clinical or therapeutic decision tool.**

---

## Why this design

Biological sequence analysis requires precision. GC content, sequence length, and base-composition checks are deterministic by nature — they have exact, reproducible answers. Delegating this computation to an LLM risks hallucination and numerical error. BioPyAI uses Biopython for all structured analysis, ensuring results are exact and reproducible. Once that ground truth is established, Phi-4 — a capable language model running entirely on local hardware — reasons over the verified facts to provide biological interpretations, research suggestions, and plain-language summaries. The model interprets facts rather than computing them. This separation of concerns produces reliable, interpretable output.

The workflow:

1. **Input** — load a sequence by FASTA/GenBank upload or NCBI accession.
2. **Processing** — Biopython computes deterministic, reproducible metrics (GC content, duplex melting temperature, thermodynamic end-asymmetry, sequence-rule flags, quality checks).
3. **Interpretation** — Phi-4 reasons over those verified facts in a grounded, multi-turn conversation, with the human choosing what to analyze and asking follow-ups.

---

## Features

- **Two input paths** — upload a FASTA (or GenBank) file, or fetch directly from NCBI by accession number. Fetched records carry their organism and molecule-type annotations into the summary.
- **Whole-sequence metrics** — a small, deliberately curated menu (GC content, non-standard / ambiguous-base quality check). Every metric is a fact a researcher would actually act on; each carries a method tooltip describing *how* it's computed, not what it means biologically.
- **siRNA candidate scan** — a sliding-window scan along the target produces a sortable table of per-candidate metrics: GC content, duplex Tm (RNA nearest-neighbor thermodynamics), 5′-end thermodynamic asymmetry, and a set of rule flags drawn from the rational-design literature (Reynolds 2004, Ui-Tei 2004, Khvorova/Schwarz 2003). Individual flags are presented for the researcher to weigh — not collapsed into a single opaque score.
- **Shortlist builder** — filter the full scan by required rules and rank by any metric, entirely in deterministic code.
- **Grounded interpretation** — open a multi-turn conversation about the whole-sequence metrics, a single candidate, or the shortlist. The opening turn carries the verified facts, so follow-ups stay anchored to real numbers.
- **Workflow persistence (full CRUD)** — save a session as a *workflow* (sequence + metadata + interpretation thread), reopen it later, extend the conversation (auto-saved as it grows), and delete it when obsolete. Each saved interpretation records the **analysis recipe** behind it — the exact choices (window, position, filters, sort) that produced what was interpreted — so the deterministic results are trivial to reproduce on reopen.

---

## Requirements

| | |
|---|---|
| **OS** | Developed on Linux (Ubuntu) |
| **Environment manager** | Conda |
| **Python** | 3.11, managed via Conda |
| **Local AI runtime** | [Ollama](https://ollama.com/) installed and running |
| **Model & GPU** | Developed with [Phi-4](https://ollama.com/library/phi4) (by Microsoft) using an 11 GB GPU" |

---

## Installation

```bash
# 1. Clone
git clone <your-repo-url>          # ← replace with your repository URL
cd biopyai

# 2. Create and activate the environment
conda env create -f environment.yml
conda activate biopyai

# 3. Install the local model (Ollama must be installed first — see ollama.com)
ollama pull phi4
```

Make sure the Ollama service is running (`ollama serve`, or as a background service) before launching the app — the app checks for it and will tell you if it isn't reachable.

---

## Running

```bash
conda activate biopyai
streamlit run app.py
```

Then open the URL Streamlit prints (typically `http://localhost:8501`).

---

## Using BioPyAI

1. **Provide a sequence** — upload a FASTA/GenBank file or enter an NCBI accession (e.g. `NM_000546`, human TP53 mRNA).
2. **Run whole-sequence metrics** — pick from the analysis menu to see GC content and the non-standard-base quality check.
3. **Scan for candidates** — choose a window length and scan the target to produce the per-candidate table; click any column header to sort.
4. **Build a shortlist** *(optional)* — narrow the scan by required rules and rank it.
5. **Interpret** — choose a subject (whole-sequence metrics, a single candidate, or the shortlist), optionally add a question, and start a grounded conversation with Phi-4. Ask follow-ups; the thread stays anchored to the verified facts.
6. **Save your work** — save the session as a workflow, reopen it any time, and pick up the conversation where you left off.

---

## What to trust, and what to check

- **The metrics are computed and reproducible.** GC content, Tm, asymmetry, and the rule flags come from deterministic code; the same input gives the same output every time.
- **The biology the model wraps around them is its trained knowledge** (e.g — why an asymmetry value favors guide-strand loading, what a GC window implies) and can be incomplete or dated. Treat interpretations as a knowledgeable second opinion to verify, not a verdict.
- **The rule flags are empirical correlates, not laws.** They reflect early-2000s rational-design heuristics and are presented as individual signals for a researcher to weigh, deliberately *not* summed into a single efficacy score.
- **Off-target / seed-region effects are out of scope.** Assessing those requires a transcriptome-wide search, which this tool does not perform.

In short: BioPyAI is a transparent, interpretable tool for understanding and reasoning about sequences — not a state-of-the-art potency model, and not a substitute for experimental validation.

---

## Privacy

Everything runs on your machine. Sequences and conversations are never sent to an external AI service. The only outbound network call the app makes is the optional NCBI fetch, when you choose to use it.

---

## Project structure

```
biopyai/
├── app.py                  # Streamlit UI and orchestration
├── core/
│   ├── input.py            # FASTA/GenBank upload + NCBI fetch
│   ├── analysis.py         # deterministic metrics + siRNA candidate scan
│   ├── llm.py              # local Phi-4 interpretation layer
│   └── storage.py          # SQLite workflow persistence (CRUD)
├── environment.yml
├── .streamlit/config.toml
└── README.md
```

The deterministic core (`input.py`, `analysis.py`, `storage.py`) is light and has no dependency on the model. 
The intelligence layer (`llm.py`) is isolated behind a small interface, so the two halves stay cleanly separable.

---

## Roadmap

Parked, in rough priority order:

- **Packaging for two audiences** — a light, deterministic-only distribution (no model) for reproducible analysis and teaching, alongside the full local-LLM build.
- **Sequence viewer** — a positional overview (GC profile, candidate hits, annotated features on one axis) as the coherent home for visualization.
- **Recipe auto-replay** — reopening a workflow could re-drive the analysis controls to their saved settings, not just display them.
- **Multiple interpretation threads per workflow** — if the single-thread model proves limiting in real use.

---

## Acknowledgments & references

The siRNA rule heuristics draw on the rational-design literature, including Reynolds et al. (2004), Ui-Tei et al. (2004), and the strand-selection work of Khvorova et al. and Schwarz et al. (2003). RNA nearest-neighbor thermodynamics use the parameters of Freier et al. (1986) via Biopython's `MeltingTemp` module.

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

<!-- Optional: add screenshots or a short demo GIF near the top — for a portfolio piece, a visual of the grounded interpretation in action is worth a lot. -->
