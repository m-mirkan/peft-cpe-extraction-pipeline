# Qwen 2.5 3B — Compound TOE-to-CPE Extraction

A two-stage pipeline for extracting **CPE 2.3** (`part:vendor:product:version`) entries from complex Common Criteria / Target of Evaluation (TOE) titles using a **QLoRA fine-tuned `Qwen/Qwen2.5-3B-Instruct`** model + a deterministic **NVD CPE Dictionary Resolver**.

---

## Why 2 Stages? (Qwen Does Not Output Final CPE Strings)

Real TOE titles routinely combine shorthand model lists (`C7771/C6671/C5571`), omitted OEM vendors (`bizhub C754 / ineo+ 754`), multi-clause version bindings (`C160 running AsyncOS 7.1 and C670 running AsyncOS 7.3`), multi-ROM versions, and certificate noise (`ANSSI-CC-...`).

**Important:** `Qwen2.5-3B` does **not** output final `cpe:2.3:...` strings directly. Instead, it extracts a clean intermediate JSON structure, and Python converts that JSON into official CPE strings:

1. **Stage 1 — `Qwen2.5-3B` (QLoRA + Outlines JSON):** Expands shorthand prefixes, separates base `targets` from shared `companions` (firmware/OS/ROMs/kits), splits independent `clauses`, and strips noise.
2. **Stage 2 — `CPEDictionaryResolver` (`src/cpe_resolver.py`):** Looks up missing/alias vendors in the standalone 142k-product NVD CPE cache (`cpe_lookup_cache.json`) and programmatically builds the final `cpe:2.3:...` strings.

### Example (Input → Stage 1 JSON → Stage 2 CPEs)

**Raw Input:**
> `"Fuji Xerox DocuCentre-IV C2265/C2263 Series Controller Software Version: Controller ROM Ver. 1.101.12"`

**Stage 1 — Annotated Qwen Output (JSON):**
```json
{
  "clauses": [
    {
      "targets": [
        {"vendor": "Fuji Xerox", "product": "DocuCentre-IV C2265", "part": "h", "version": "-"},
        {"vendor": "Fuji Xerox", "product": "DocuCentre-IV C2263", "part": "h", "version": "-"}
      ],
      "companions": [
        {"vendor": null, "product": "Controller ROM", "part": "o", "versions": ["1.101.12"]}
      ]
    }
  ]
}
```

**Stage 2 — Programmatic CPE Output (`cpe_resolver.py`):**
```text
cpe:2.3:h:fujixerox:docucentre-iv_c2265:-:*:*:*:*:*:*:*
cpe:2.3:h:fujixerox:docucentre-iv_c2263:-:*:*:*:*:*:*:*
cpe:2.3:o:fujixerox:controller_rom:1.101.12:*:*:*:*:*:*:*
```

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

1. **Write an Annotation Codebook:** Define clear rules for tricky edge cases (e.g., when a component is `h` vs `o` vs `a`, how to handle sub-versions like Service Packs/ROMs, and what text counts as noise).
2. **Create a Small Hand-Labeled Test Set:** Manually annotate 50–100 entries from `data/benchmarks/` using the codebook so you can measure real accuracy before and after every change.
3. **Expand the Synthetic Training Data (`src/generate_synthetic_dataset.py`):** Inspect where the model makes mistakes on `data/benchmarks/` (such as multi-module firmware lists, French/German titles, or missing spaces like `TOSHIBAe-STUDIO...`) and add matching synthetic patterns.
4. **Tune Training Settings (`src/train_qwen.py`):** Test different LoRA ranks (`r=8, 16, 32`), learning rates, epoch counts (`1–2`), or larger synthetic datasets (`5,000+` examples) and compare scores on your hand-labeled test set.
5. **Improve Vendor & Product Matching (`src/cpe_resolver.py`):** Add missing vendor/chip rules or improve fuzzy matching against `cpe_lookup_cache.json` for product names that don't match exactly.
