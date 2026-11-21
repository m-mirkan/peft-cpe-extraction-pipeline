"""Check that gold titles do NOT appear (exactly or almost) in a training file.
Run it on the ORIGINAL data and on every NEW training file you generate, before training.

Usage: python scripts/check_leakage.py --gold data/gold/gold_template.json --train data/synthetic/synthetic_train.jsonl [--threshold 0.7]
Similarity = Jaccard overlap of lower-cased word sets. >= threshold is reported as a leak.
Exit code 1 if any leak is found.
"""
import argparse, json, re, sys

def toks(s): return set(re.sub(r"[^a-z0-9]+", " ", s.lower()).split())

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold", required=True)
    ap.add_argument("--train", required=True, help="jsonl with an 'input' field per line")
    ap.add_argument("--threshold", type=float, default=0.7)
    a = ap.parse_args()
    gold = json.load(open(a.gold, encoding="utf-8"))
    train = [toks(json.loads(l)["input"]) for l in open(a.train, encoding="utf-8") if l.strip()]
    leaks = []
    for g in gold:
        tg = toks(g["input"])
        best = max((len(tg & t) / len(tg | t) for t in train if t | tg), default=0.0)
        if best >= a.threshold:
            leaks.append((best, g["id"], g["input"][:80]))
    print(f"{len(gold)} gold titles vs {len(train)} training examples (threshold {a.threshold}): {len(leaks)} leak(s)")
    for b, i, t in sorted(leaks, reverse=True): print(f"  {i} sim={b:.2f} {t}")
    sys.exit(1 if leaks else 0)

if __name__ == "__main__":
    main()
