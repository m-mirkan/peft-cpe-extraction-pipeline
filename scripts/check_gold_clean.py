"""Final cleanliness gate for the gold set.

Checks every gold title and label against (a) training/validation records (jsonl) and (b) python sources
whose string literals hold the generator vocabulary. Reports:
  * product names (whole phrase, 5+ chars) that occur in the corpus
  * model codes (letters+digits, 2+ digits) that occur in the corpus
Vendor names and a short list of generic component words (Firmware, Controller ROM, IC Dedicated Software,
Crypto Library, ...) are ignored. Exit code 1 if anything is found.

python scripts/check_gold_clean.py --gold data/gold/gold_template.json \
   --records data/synthetic/synthetic_train.jsonl data/synthetic/synthetic_val.jsonl \
   --sources src/generate_synthetic_dataset.py
"""
import argparse, json, re, sys

GENERIC = {"firmware", "fax rom", "controller rom", "storage controller rom", "ic dedicated software", "system software",
           "control software", "engine", "scanner", "printer", "pcl", "fax unit", "data security kit", "card reader",
           "crypto library", "cryptographic library", "fips hard disk kit", "secure element"}
norm = lambda s: re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def codes(text):
    out = set()
    for tok in re.split(r"[\s,/;()\[\]:]+", text):
        tok = re.sub(r"[^A-Za-z0-9_.+\-]", "", tok).strip(".,-")
        for t in {tok} | set(re.split(r"[-_]", tok)):
            if re.fullmatch(r"[vV]?\d+([.\-]\d+)*", t) or t.lower().startswith(("anssi", "eucc", "bsi")):
                continue
            if len(t) >= 4 and len(re.findall(r"\d", t)) >= 2 and re.search(r"[A-Za-z]", t):
                out.add(t.lower())
    return out


ap = argparse.ArgumentParser()
ap.add_argument("--gold", required=True)
ap.add_argument("--records", nargs="*", default=[])
ap.add_argument("--sources", nargs="*", default=[])
a = ap.parse_args()

corp = {}
for p in a.records:
    txt = []
    for line in open(p, encoding="utf-8"):
        r = json.loads(line)
        txt.append(r["input"])
        txt.append(r["output_json"])
    corp[p] = "\n".join(txt)
for p in a.sources:
    corp[p] = "\n".join(re.findall(r'"([^"\n]{2,})"', open(p, encoding="utf-8").read()))
norm_corp = {p: " " + norm(t) + " " for p, t in corp.items()}
code_corp = {p: codes(t) for p, t in corp.items()}

found = []
for row in json.load(open(a.gold, encoding="utf-8")):
    prods = set()
    for cl in (row.get("gold") or {}).get("clauses", []):
        for u in cl["targets"] + cl["companions"]:
            n = norm(u["product"])
            if len(n) >= 5 and n not in GENERIC:
                prods.add(n)
    for p, c in norm_corp.items():
        for n in prods:
            if f" {n} " in c:
                found.append((row["id"], "product", n, p))
    for t in codes(row["input"]):
        for p, c in code_corp.items():
            if t in c:
                found.append((row["id"], "code", t, p))
for f in sorted(set(found)):
    print(*f)
print("RESULT:", "CLEAN (0 overlaps)" if not found else f"{len(set(found))} overlaps")
sys.exit(1 if found else 0)
