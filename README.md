# 🧬 BioPyAI

**A local-first, hybrid AI application for computational biology — combining deterministic sequence analysis with (locally-run) language model reasoning to assist life science researchers.**

## Why this design

Many sequence metrics are deterministic by nature. Delegating that computation to an LLM directly risks hallucination and numerical error. BioPyAI keeps facts and interpretation in separate lanes — [Biopython](https://biopython.org/) computes exact, reproducible metrics over a nucleotide sequence; [Phi-4](https://ollama.com/library/phi4), running locally through [Ollama](https://ollama.com/), then reasons over those verified numbers to provide biological interpretations, research suggestions, and plain-language summaries. The model interprets facts rather than computing them. This separation of concerns promotes reliable, interpretable output. Everything runs on your machine.

> **This is a research and learning aid, not a clinical or therapeutic decision tool.**

---

## Using BioPyAI

1. **Input** — load a sequence by FASTA/GenBank file upload or fetch directly from NCBI by accession number. Fetched records carry their organism and molecule-type annotations into the summary.

2. **Run a deterministic analysis** — compute using Biopython:
 - *Whole-sequence metrics* — pick from a small, deliberately curated menu to see GC content and the non-standard-base quality check. Each carries a tooltip describing *how* it's computed, not what it means biologically.
 - *Scan for siRNA candidates* — choose a window length from a sliding-window scan along the target to produce a sortable table of per-candidate metrics: GC content, duplex Tm (RNA nearest-neighbor thermodynamics), 5′-end thermodynamic asymmetry, and a set of rule flags drawn from the rational-design literature (Reynolds 2004, Ui-Tei 2004, Khvorova/Schwarz 2003).
 - *Build a shortlist* (optional) — filter the full scan by required rules and rank by any metric.

3. **Interpret with AI** — choose a subject (whole-sequence metrics, a single candidate, or the shortlist), optionally add a question, and start a multi-turn conversation with Phi-4. Choose what to analyze and ask for follow-ups. The thread stays anchored to the verified facts.

4. **Save your work (full CRUD)** — save the research session as a *workflow* (sequence + metadata + interpretation thread), reopen it later, extend the conversation (auto-saved as it grows), and delete it when obsolete. Each saved interpretation records the analysis behind it — the exact choices (window, position, filters, sort) that produced what was interpreted — so the deterministic results are easy to reproduce on reopen.

---

## Requirements

| | |
|---|---|
| **OS** | Developed on Linux (Ubuntu) |
| **Environment manager** | Conda |
| **Python** | 3.11, managed via Conda |
| **Local AI runtime** | [Ollama](https://ollama.com/) installed and running |
| **Model & GPU** | Developed with [Phi-4](https://ollama.com/library/phi4) (by Microsoft) using an 11 GB GPU |

---

## Installation

```bash
# 1. Clone
git clone https://github.com/kjony/biopyai
cd biopyai

# 2. Create and activate the environment
conda env create -f environment.yml
conda activate biopyai

# 3. Install the local model (Ollama must be installed first — see ollama.com)
ollama pull phi4
```

Make sure the Ollama service is running before launching the app — the app checks and will notify if it isn't reachable.

---

## Running

```bash
conda activate biopyai
streamlit run app.py
```

---

## What to trust, and what to check

- **The metrics are computed and reproducible.** GC content, Tm, asymmetry, and the rule flags come from deterministic code; the same input gives the same output every time.
- **The biology the model wraps around them is its trained knowledge** (e.g. why an asymmetry value favors guide-strand loading, what a GC window implies) and can be incomplete or dated. Treat interpretations as a knowledgeable second opinion to verify, not a verdict.
- **The rule flags are empirical correlates, not laws.** They reflect early-2000s rational-design heuristics and are presented as individual signals for a researcher to weigh, deliberately *not* summed into a single efficacy score.
- **Off-target / seed-region effects are out of scope.** Assessing those requires a transcriptome-wide search, which this tool does not perform.

In short: BioPyAI is a transparent, interpretable tool for understanding and reasoning about sequences — not a state-of-the-art potency model, and not a substitute for experimental validation.

---

## Privacy

Everything runs on your machine. Sequences and conversations are not sent to an external AI service. The only outbound network call the app makes is the optional NCBI fetch, when you choose to use it.

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

The deterministic core (`input.py`, `analysis.py`, `storage.py`) is light and has no dependency on the model. The intelligence layer (`llm.py`) is isolated behind a small interface, so the two halves stay cleanly separable.

---

## Roadmap

Parked, in rough priority order:

- **Packaging for two audiences** — a light, deterministic-only distribution (no model) for reproducible analysis and teaching, alongside the full local-LLM build.
- **LAN exposure** — serve the app to other machines on the local network via browser (nothing to install on clients), so it can run on the GPU host and be reached from any laptop. Cheap and independent of the items below; note that with the current schema all connected users share one workflow pool.
- **Multi-user workflows** — give each workflow an owner so a shared deployment partitions saved work per user. The live per-session state is already isolated; only the persistent layer needs identity. Prerequisite for true concurrency — and even then, the single GPU serializes interpretation across users. 
- **Sequence viewer** — a positional overview (GC profile, candidate hits, annotated features on one axis) as the coherent home for visualization.
- **Recipe auto-replay** — reopening a workflow could re-drive the analysis controls to their saved settings, not just display them.
- **Multiple interpretation threads per workflow** — if the single-thread model proves limiting in real use.

---

## Acknowledgments & references

The siRNA rule heuristics draw on the rational-design literature, including Reynolds et al. (2004), Ui-Tei et al. (2004), and the strand-selection work of Khvorova et al. and Schwarz et al. (2003). RNA nearest-neighbor thermodynamics use the parameters of Freier et al. (1986) via Biopython's `MeltingTemp` module.

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
