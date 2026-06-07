# BioPyAI 🧬

A hybrid AI application for computational biology, combining deterministic sequence analysis with language model reasoning to assist life science researchers.

---

## Overview

BioPyAI is built on a deliberate architectural philosophy: **let each tool do what it does best.**

Biological sequence analysis requires precision. GC content, ORF detection, sequence length, and molecular metadata are deterministic by nature — they have exact, reproducible answers. Delegating this computation to an LLM risks hallucination and numerical error. BioPyAI uses **Biopython** for all structured analysis, ensuring results are verifiable and scientifically sound.

Once that ground truth is established, **Phi-4** — a capable small language model running entirely on local hardware — reasons over the verified metadata to provide biological interpretations, research suggestions, and plain-language summaries. The model interprets facts rather than computing them, which significantly reduces hallucination risk and produces more reliable, meaningful output.

This separation of concerns — deterministic computation feeding into language model reasoning — is what distinguishes BioPyAI from applications that use LLMs as general-purpose scientific calculators.

---

## Features

### Current
- FASTA file upload and parsing
- Sequence retrieval from NCBI via accession number (Entrez API)
- GC content analysis

### Roadmap
- Extended metadata extraction — sequence length, organism, coding/non-coding classification, ORF detection, protein vs. nucleotide identification
- Phi-4 intelligence layer via Ollama — biological interpretation, research suggestions, plain-language summaries
- Interactive researcher Q&A grounded in verified sequence metadata
- Support for additional sequence formats (GenBank, EMBL)

---

## Tech Stack

| Layer | Technology |
|---|---|
| UI | Streamlit |
| Sequence Analysis | Biopython |
| NCBI API | Entrez (via Biopython) |
| Intelligence | Phi-4 via Ollama (planned) |
| Language | Python 3.11 |
| Environment | Conda |

---

## Installation

### Prerequisites
- [Conda](https://docs.conda.io/en/latest/) installed on your system
- [Ollama](https://ollama.com/) installed locally (required for the intelligence layer — planned)

### Setup

**1. Clone the repository**
```bash
git clone <repository-url>
cd biopyai
```

**2. Create and activate the Conda environment**
```bash
conda env create -f environment.yml
conda activate biopyai
```

**3. Run the application**
```bash
streamlit run app.py
```

The application will open automatically in your default browser.

---

## Usage

BioPyAI offers two ways to provide a sequence:

- **Upload a FASTA file** — drag and drop or browse for a local `.fasta`, `.fa`, or `.txt` file
- **Fetch from NCBI** — enter a valid accession number (e.g. `NM_000546`) and click **Fetch Sequence**

Once a sequence is loaded, BioPyAI extracts and displays metadata automatically.

---

## Project Structure

```
biopyai/
├── app.py               # Streamlit entry point
├── environment.yml      # Conda environment and dependencies
├── core/
│   ├── __init__.py
│   ├── input.py         # FASTA parsing and NCBI sequence fetching
│   └── analysis.py      # Biopython sequence analysis and metadata extraction
└── ui/
    ├── __init__.py
    └── components.py    # Reusable Streamlit UI components
```

---

## License

MIT License — see `LICENSE` for details.