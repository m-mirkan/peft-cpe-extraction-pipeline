# Qwen 2.5 3B — Compound TOE-to-CPE Extraction

A two-stage pipeline for extracting **CPE 2.3** (`part:vendor:product:version`) entries from complex Common Criteria / Target of Evaluation (TOE) titles using a **QLoRA fine-tuned `Qwen/Qwen2.5-3B-Instruct`** model + a deterministic **NVD CPE Dictionary Resolver**.

---

## Why 2 Stages?

Real TOE titles routinely combine shorthand model lists (`C7771/C6671/C5571`), omitted OEM vendors (`bizhub C754 / ineo+ 754`), multi-clause version bindings (`C160 running AsyncOS 7.1 and C670 running AsyncOS 7.3`), multi-ROM versions, and certificate noise (`ANSSI-CC-...`).

1. **Stage 1 — `Qwen2.5-3B` (QLoRA + Outlines JSON):** Expands prefixes, separates base `targets` from shared `companions` (firmware/OS/ROMs/kits), splits independent `clauses`, and strips noise.
2. **Stage 2 — `CPEDictionaryResolver` (`src/cpe_resolver.py`):** Resolves missing/alias vendors against a standalone 142k-product NVD CPE cache (`cpe_lookup_cache.json`), guards against vendor hallucinations, and outputs `cpe:2.3:...` strings.

---

## Project Layout

```text
├── src/
│   ├── cpe_resolver.py               # Pydantic schema + standalone 142k CPE lookup & builder
│   ├── generate_synthetic_dataset.py # Synthetic compound TOE generator
│   ├── train_qwen.py                 # 4-bit NF4 QLoRA trainer (assistant-only loss masking)
│   ├── infer_and_resolve.py          # Batch evaluation + `--reprocess_only` mode
│   └── interactive_cpe_shell.py      # Interactive REPL with live Baseline vs. LoRA diff
├── notebooks/
│   └── colab_quickstart.ipynb        # Ready-to-run Google Colab / Kaggle T4 GPU notebook
├── data/
│   ├── benchmarks/                   # 595 untouched real TOE titles (eval ONLY — never trained on)
│   ├── synthetic/                    # 2,200 train / 200 val synthetic ChatML examples
│   └── cpe_index/cpe_lookup_cache.json # Precomputed NVD CPE index (142,735 products)
└── requirements.txt
```

---

## Quick Start

### 1. Setup (Local CUDA GPU >= 8 GB VRAM — or Free Google Colab / Kaggle T4)

* **No local GPU?** Open `notebooks/colab_quickstart.ipynb` directly in [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/yasirdemircan/peft-cpe-extraction-pipeline/blob/main/notebooks/colab_quickstart.ipynb) (`Runtime → Change runtime type → T4 GPU`, 15 GB VRAM) or **Kaggle Notebooks** (30 free GPU hrs/week).
* **Local setup:**

```bash
python -m venv .venv
.venv\Scripts\activate  # Linux/macOS: source .venv/bin/activate

pip install torch --index-url https://download.pytorch.org/whl/cu124
pip install -r requirements.txt
```
*(The base `Qwen/Qwen2.5-3B-Instruct` model downloads automatically from Hugging Face on first run.)*

### 2. Get the LoRA Adapter (Option A: Pre-Trained, Option B: Train Yourself)

* **Option A — Use Pre-Trained Baseline LoRA (~120 MB):**
  Download from [Google Drive](https://drive.google.com/file/d/1eKyqTdDT36zPEpi6y62kZg9V8vTmJVaX/view?usp=sharing) and extract into `checkpoints/qwen25_3b_cpe_lora/` (`adapter_config.json`, `adapter_model.safetensors`, tokenizer files).

* **Option B — Fine-Tune from Scratch (~12–18 min for 1 epoch on 8 GB GPU):**
  ```bash
  python src/train_qwen.py \
    --train_file data/synthetic/synthetic_train.jsonl \
    --val_file data/synthetic/synthetic_val.jsonl \
    --output_dir checkpoints/qwen25_3b_cpe_lora \
    --epochs 1 --batch_size 2 --grad_accum 8
  ```

### 3. Run Interactive Shell (Live Baseline vs. Fine-Tuned Comparison)

```bash
python src/interactive_cpe_shell.py --lora_dir checkpoints/qwen25_3b_cpe_lora
```

Shell commands: `:model` (cycle `LORA` / `BASE` / `COMPARE`), `:compare` (re-run last input side-by-side), `:mode` (toggle decoupled vs. model-bound `_firmware`), `:lookup <name>` (query CPE index), `:sample` (random benchmark entry).

### 4. Batch Evaluation

```bash
python src/infer_and_resolve.py \
  --lora_dir checkpoints/qwen25_3b_cpe_lora \
  --input_file data/benchmarks/names.json \
  --limit 20 --output_file outputs/names_predictions.json

# Fast CPE re-generation after editing src/cpe_resolver.py (no GPU needed):
python src/infer_and_resolve.py --reprocess_only outputs/names_predictions.json
```

---

## Suggestions for Improvement

1. **Evaluation Metrics:** Annotate a 50–100 entry gold subset from `data/benchmarks/` and measure exact/fuzzy `(part, vendor, product, version)` F1 and multi-clause pairing accuracy.
2. **Synthetic Data Coverage (`src/generate_synthetic_dataset.py`):** Add extreme multi-module firmware lists (15+ modules), French/German Common Criteria phrasing, OS-on-Hardware stacking, and missing-space typos (`TOSHIBAe-STUDIO...`).
3. **Fine-Tuning Experiments (`src/train_qwen.py`):** Tune LoRA rank (`r=8/16/32`), epochs (`1–2`), dataset size (`5k–10k`), compare `Qwen2.5-1.5B/7B` or `Qwen3`, or explore GRPO/DPO with CPE validity rewards.
4. **CPE Linking (`src/cpe_resolver.py`):** Upgrade prefix lookup to BM25 or dense embedding retrieval over the 142k CPE dictionary. *(To regenerate synthetic data from raw NVD entries, place `extracted_cpe_targets.json` in `data/cpe_index/`.)*
