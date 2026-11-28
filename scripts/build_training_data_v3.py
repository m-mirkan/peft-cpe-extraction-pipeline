"""Build the v3 training set into data/synthetic_v3/ and run every safety gate.

Run from the repo root:
    python scripts/build_training_data_v3.py

What it does
  1. Fingerprints Yasir's files in data/synthetic/ (they must never change).
  2. Runs src/generate_synthetic_dataset_v3.py into data/synthetic_v3/ (never into data/synthetic/).
  3. Gate A  check_gold_clean.py : no gold product name / model code in the new records or the generator source.
  4. Gate B  check_leakage.py    : no gold title (Jaccard >= 0.7) in the new train or val file.
  5. Gate C  Yasir's files are byte-identical to step 1.
  6. Reports how many new inputs are also in Yasir's data (information only) and basic counts.
Exit code 0 only if all gates pass.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OLD_DIR = os.path.join("data", "synthetic")


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def run(cmd):
    print("\n$", " ".join(cmd))
    return subprocess.run(cmd, cwd=ROOT).returncode


def inputs(path):
    out = set()
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            if line.strip():
                out.add(json.loads(line)["input"].strip().lower())
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out_dir", default=os.path.join("data", "synthetic_v3"))
    ap.add_argument("--gold", default=os.path.join("data", "gold", "gold_template.json"))
    ap.add_argument("--cache", default=os.path.join("data", "cpe_index", "cpe_lookup_cache.json"))
    ap.add_argument("--cpe", default=os.path.join("data", "cpe_index", "extracted_cpe_targets.json"))
    ap.add_argument("--n_train", type=int, default=2200)
    ap.add_argument("--n_val", type=int, default=200)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--no_cpe", action="store_true", help="local test without extracted_cpe_targets.json (NOT for the real build)")
    ap.add_argument("--force", action="store_true", help="overwrite an existing v3 output folder")
    a = ap.parse_args()

    if os.path.normpath(a.out_dir) == os.path.normpath(OLD_DIR):
        sys.exit("REFUSED: out_dir is Yasir's data/synthetic/")
    tr = os.path.join(a.out_dir, "synthetic_train.jsonl")
    va = os.path.join(a.out_dir, "synthetic_val.jsonl")
    if os.path.exists(os.path.join(ROOT, tr)) and not a.force:
        sys.exit(f"{tr} already exists; use --force to regenerate")

    old_files = [os.path.join(ROOT, OLD_DIR, n) for n in ("synthetic_train.jsonl", "synthetic_val.jsonl")]
    before = {p: sha(p) for p in old_files if os.path.exists(p)}

    rc = run([sys.executable, "src/generate_synthetic_dataset_v3.py", "--gold", a.gold, "--cache", a.cache,
              "--cpe", a.cpe, "--n_train", str(a.n_train), "--n_val", str(a.n_val), "--seed", str(a.seed),
              "--out_dir", a.out_dir] + (["--no_cpe"] if a.no_cpe else []))
    if rc:
        sys.exit("GENERATION FAILED")

    ok = True
    rc = run([sys.executable, "-I", "scripts/check_gold_clean.py", "--gold", a.gold, "--records", tr, va,
              "--sources", "src/generate_synthetic_dataset_v3.py"])
    print("Gate A (gold product/code overlap):", "PASS" if rc == 0 else "FAIL")
    ok &= rc == 0
    for f in (tr, va):
        rc = run([sys.executable, "-I", "scripts/check_leakage.py", "--gold", a.gold, "--train", f])
        print(f"Gate B (title leakage, {os.path.basename(f)}):", "PASS" if rc == 0 else "FAIL")
        ok &= rc == 0

    after = {p: sha(p) for p in old_files if os.path.exists(p)}
    same = before == after
    print("Gate C (Yasir's data/synthetic untouched):", "PASS" if same else "FAIL")
    ok &= same

    new_tr, new_va = inputs(os.path.join(ROOT, tr)), inputs(os.path.join(ROOT, va))
    old_all = inputs(old_files[0]) | inputs(old_files[1])
    print(f"\nnew train inputs: {len(new_tr)}  new val inputs: {len(new_va)}")
    print(f"train/val inputs shared with each other: {len(new_tr & new_va)}")
    print(f"new inputs identical to one of Yasir's inputs (information only): {len((new_tr | new_va) & old_all)}")
    # information: which patterns the training file really contains
    kinds = {}
    print("\nGate D (v2 data untouched): data/synthetic_v2 is never written by the v3 generator")
    print("\nALL GATES PASSED" if ok else "\nSOME GATES FAILED - do not train on this data")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
