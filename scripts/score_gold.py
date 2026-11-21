"""Score one or more prediction files against the hand-labeled gold set.

Gold file : data/gold/gold_template.json (only entries with status == "labeled" are scored).
Pred file : output of src/infer_and_resolve.py (list of {input, extracted_structure | error}).

Usage:
  python scripts/score_gold.py --gold data/gold/gold_template.json \
      --pred baseline=outputs/gold_base_p1.json,outputs/gold_base_p2.json --pred codebook_v1=outputs/gold_v1.json
"""
import argparse, json, re
from collections import Counter, defaultdict

def slug(s):
    s = (s or "-").lower().replace("®", "").replace("™", "")
    s = re.sub(r"\s+", "_", s.strip())
    return s or "-"

def items_of(struct):
    """Flatten a Stage-1 structure into (part, product, version, vendor) tuples."""
    out = []
    for cl in (struct or {}).get("clauses", []):
        for t in cl.get("targets", []):
            out.append((t["part"], slug(t["product"]), slug(t.get("version", "-")), t.get("vendor")))
        for c in cl.get("companions", []):
            for v in (c.get("versions") or ["-"]):
                out.append((c["part"], slug(c["product"]), slug(v), c.get("vendor")))
    return out

def strict_key(i): return (i[0], i[1], i[2])
def loose_key(i):  return (i[1], i[2])
def prod_key(i):   return (i[0], i[1])   # part + product, version ignored (lenient metric)

def prf(tp, n_pred, n_gold):
    p = tp / n_pred if n_pred else 0.0
    r = tp / n_gold if n_gold else 0.0
    return p, r, (2 * p * r / (p + r) if p + r else 0.0)

def score(gold_rows, preds):
    agg = defaultdict(lambda: Counter())
    for g in gold_rows:
        pr = preds.get(g["input"])
        tags = g.get("tags", []) or ["untagged"]
        buckets = ["ALL"] + tags + ([f"difficulty:{g['difficulty']}"] if g.get("difficulty") else [])
        failed = pr is None or pr.get("error") or not pr.get("extracted_structure")
        gi = items_of(g["gold"])
        pi = [] if failed else items_of(pr["extracted_structure"])
        gs, ps = Counter(map(strict_key, gi)), Counter(map(strict_key, pi))
        gl, pl = Counter(map(loose_key, gi)), Counter(map(loose_key, pi))
        gp, pp = Counter(map(prod_key, gi)), Counter(map(prod_key, pi))
        tp = sum((gs & ps).values())
        prod_tp = sum((gp & pp).values())
        loose_tp = sum((gl & pl).values())
        part_ok = 0
        for k in (gl & pl):  # same product+version: did the part letter agree?
            gparts = Counter(i[0] for i in gi if loose_key(i) == k)
            pparts = Counter(i[0] for i in pi if loose_key(i) == k)
            part_ok += sum((gparts & pparts).values())
        for b in buckets:
            a = agg[b]
            a["titles"] += 1; a["failed"] += int(bool(failed))
            a["gold_items"] += len(gi); a["pred_items"] += len(pi)
            a["tp"] += tp; a["loose_tp"] += loose_tp; a["prod_tp"] += prod_tp; a["part_ok"] += part_ok
            a["exact_title"] += int((not failed) and gs == ps)
    return agg

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold", required=True)
    ap.add_argument("--pred", action="append", required=True, help="label=path/to/predictions.json")
    ap.add_argument("--json_out", default=None)
    ap.add_argument("--status", default="labeled", help="comma list of statuses to score, e.g. labeled or labeled,draft")
    a = ap.parse_args()
    gold = [g for g in json.load(open(a.gold, encoding="utf-8")) if g.get("status") in a.status.split(",")]
    if not gold:
        raise SystemExit("No entries with status == 'labeled' in the gold file yet.")
    results = {}
    for spec in a.pred:
        label, path = spec.split("=", 1)
        preds = {}
        for one in path.split(","):          # several files for one model (e.g. part1,part2) are merged
            for p in json.load(open(one.strip(), encoding="utf-8")):
                preds[p["input"]] = p
        results[label] = score(gold, preds)
    print(f"Scored titles: {len(gold)} (status={a.status}). Each title is worth {100/len(gold):.1f} points of title-exact-match.\n")
    all_buckets = {t for g in gold for t in (g.get('tags') or ['untagged'])} | {f"difficulty:{g['difficulty']}" for g in gold if g.get("difficulty")}
    for bucket in ["ALL"] + sorted(all_buckets):
        print(f"== {bucket} ==")
        print(f"{'model':14s} {'titles':>6s} {'fail':>4s} {'P':>6s} {'R':>6s} {'F1':>6s} {'partAcc':>8s} {'exactTitle':>10s} {'F1-noVer':>9s}")
        for label, agg in results.items():
            x = agg.get(bucket)
            if not x: continue
            p, r, f = prf(x["tp"], x["pred_items"], x["gold_items"])
            pacc = x["part_ok"] / x["loose_tp"] if x["loose_tp"] else 0.0
            print(f"{label:14s} {x['titles']:6d} {x['failed']:4d} {p:6.2f} {r:6.2f} {f:6.2f} {pacc:8.2f} {x['exact_title']/x['titles']:10.2f} {prf(x['prod_tp'], x['pred_items'], x['gold_items'])[2]:9.2f}")
        print()
    if a.json_out:
        json.dump({k: {b: dict(c) for b, c in v.items()} for k, v in results.items()}, open(a.json_out, "w"), indent=2)

if __name__ == "__main__":
    main()
