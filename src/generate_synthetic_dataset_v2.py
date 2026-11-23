"""
Synthetic training-data generator v2 (codebook v1.0).

Differences from generate_synthetic_dataset.py (Yasir's v1, left untouched):
  * Gold vocabulary is excluded: any record that contains a model code or a product
    name found in the gold set is rejected (see --gold).
  * New patterns following the codebook: applets (a) on chips, card OS (o) with chip,
    options/kits, chip revisions in the version field (D10), multilingual titles,
    long model lists, certification noise on any pattern, glued text.
  * The part letter of curated software/OS entries follows the NVD majority
    (cpe_lookup_cache.json) when the product exists there (R2).
  * Same SYSTEM_PROMPT and same record format as v1, so train_qwen.py is unchanged.

Usage (never writes into data/synthetic/):
  python src/generate_synthetic_dataset_v2.py --sample 30                 # print samples only
  python src/generate_synthetic_dataset_v2.py --out_dir data/synthetic_v2 # write train/val
"""
import argparse
import json
import os
import random
import re
from collections import Counter
from typing import Dict, List, Optional, Tuple

from cpe_resolver import ClauseGroup, CompanionComponent, ExtractedUnit, TOEExtraction
from generate_synthetic_dataset import (
    ENTERPRISE_SW_OS_EXAMPLES,
    NETWORK_APPLIANCE_FAMILIES,
    OEM_MULTI_BRAND_GROUPS,
    PRINTER_MFP_FAMILIES,
    SMARTCARD_IC_FAMILIES,
    SYSTEM_PROMPT,
    format_chatml_record,
    format_slash_or_comma_models,
    load_cpe_families,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def slug(s: str) -> str:
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9+]+", "_", s.lower())).strip("_")


# Generic component names that the codebook wants the model to learn; never blocked.
GENERIC_OK = {
    "firmware", "control_software", "controller_rom", "fax_rom", "system_software",
    "controller_firmware", "system_firmware", "system", "panel", "fax", "ios",
    "ios_xe", "nx-os", "secure_element",
    # crypto-library acronyms and generic option units: too generic to count as vocabulary leakage
    "ec", "rsa", "sha-2", "sha_2", "scl", "hsl", "acl", "ecc", "aes",
    "fax_unit", "fax_option", "fips_hard_disk_kit", "data_security_kit", "card_reader",
}

MODEL_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.+\-]*")


def model_tokens(text: str) -> set:
    """Tokens that look like model codes: letters+digits, length >= 5."""
    out = set()
    for tok in re.split(r"[\s,/;()\[\]:]+", text):
        tok = re.sub(r"[^A-Za-z0-9_.+\-]", "", tok).strip(".,-")
        for t in {tok} | set(re.split(r"[-_]", tok)):
            if re.fullmatch(r"[vV]?\d+([.\-]\d+)*", t) or t.lower().startswith(("anssi", "eucc", "bsi")):
                continue  # version numbers and certification ids are not vocabulary
            if len(t) >= 4 and len(re.findall(r"\d", t)) >= 2 and re.search(r"[A-Za-z]", t):
                out.add(t.lower())
    return out


class GoldBlocklist:
    def __init__(self, gold_path: Optional[str]):
        self.tokens, self.products = set(), set()
        if not gold_path or not os.path.exists(gold_path):
            print("[v2] WARNING: no gold file, blocklist is empty")
            return
        for row in json.load(open(gold_path, encoding="utf-8")):
            self.tokens |= model_tokens(row["input"])
            for cl in (row.get("gold") or {}).get("clauses", []):
                for u in cl.get("targets", []):
                    self._add(u["product"])
                for c in cl.get("companions", []):
                    self._add(c["product"])
        print(f"[v2] Gold blocklist: {len(self.tokens)} model tokens, {len(self.products)} product names")

    def _add(self, product: str):
        s = slug(product)
        if s and s not in GENERIC_OK:
            self.products.add(s)

    def hit(self, text: str, ext: TOEExtraction) -> Optional[str]:
        bad = model_tokens(text) & self.tokens
        if bad:
            return "token:" + sorted(bad)[0]
        ins = "_" + slug(text) + "_"
        for g in self.products:
            if len(g) >= 5 and "_" + g + "_" in ins:
                return "phrase:" + g
        for cl in ext.clauses:
            for u in list(cl.targets) + list(cl.companions):
                ps, vps = slug(u.product), slug(f"{u.vendor or ''} {u.product}")
                for g in self.products:
                    if ps == g or ps.startswith(g + "_") or vps == g or vps.startswith(g + "_"):
                        return "product:" + g
        return None


class NvdPart:
    """Majority part letter per product name from cpe_lookup_cache.json (R2)."""

    def __init__(self, cache_path: str):
        self.m: Dict[str, str] = {}
        if not os.path.exists(cache_path):
            print("[v2] WARNING: cpe_lookup_cache.json missing; curated parts kept")
            return
        p2v = json.load(open(cache_path, encoding="utf-8"))["product_to_vendors"]
        for prod, rows in p2v.items():
            cnt = Counter()
            for _vendor, part, n in rows:
                cnt[part] += n
            self.m[prod] = cnt.most_common(1)[0][0]

    def major(self, product: str) -> Optional[str]:
        return self.m.get(slug(product))


# ---------------------------------------------------------------------------
# Extra vocabulary (invented or generic; the gold blocklist rejects any collision)
# ---------------------------------------------------------------------------

CHIP_FAMILIES = SMARTCARD_IC_FAMILIES + [
    ("Infineon", "Security Controller", ["SLC37GDA", "SLJ52GLA", "SLE97CNFX", "SLE78CAFX", "SLM9670"]),
    ("NXP", "Secure Element", ["P73N2M0B0", "SN220", "P71D321", "SN110", "P5CD081"]),
    ("STMicroelectronics", "", ["ST33K1M5", "ST33G1M2", "ST54J", "ST31H320", "ST32J", "ST33H768"]),
    ("Samsung", "", ["S3FV9RR", "S3K250AF", "S3FT9MV"]),
    ("Fudan Microelectronics", "", ["FM1280", "FM1208", "FM11RF08"]),
    ("Renesas", "", ["AE57C1", "AE46C1", "RS45C"]),
    (None, "Smart Card IC", ["MN63Y1212", "MN67S160", "TC58S80"]),
]

CHIP_REV_WORDS = ["rev. {r}", "Revision {r}", "version {r}", "design step {r}", "stepping {r}", "mask {r}"]
CHIP_REV_VALUES = ["A", "B", "C", "E", "G", "A01", "B11", "T21", "T24", "r1p0", "R3", "2", "3", "5"]
CHIP_NOUNS = ["", " microcontroller", " Smart Card IC", " Secure Element", " Security Controller", " secure chip"]

APPLET_NAMES = [
    "Orion ePassport", "VeriTravel Applet", "SecureID Applet", "TravelPass ePassport", "CitizenCard Applet",
    "NovaPass ePassport", "PlatinumID Applet", "EagleID", "HorizonPass", "Atlas eID", "KeyPass Applet",
    "eMRTD Suite", "SignPro Applet", "WalletSE Applet", "ResidentID", "HealthCard Application",
]
APPLET_VENDORS = [None, None, "Thales", "IDEMIA", "Giesecke+Devrient", "Veridos", "Athena", "Eastcompeace", "Watchdata", "Oberthur"]
APPLET_VERSIONS = ["1.0", "1.1", "1.4", "2.0", "2.1", "2.3.1", "3.0", "3.2", "4.1.2", "1.0.5", "2.2 build 14", "01 revision 02 patch 01"]
APPLET_FEATURES = ["EAC", "BAC", "PACE", "AA", "CA", "EAC with PACE", "BAC and AA", "PACE-CAM", "EAC RSA or EAC ECC"]
ICAO_LEAD = ["", "", "Passeport ", "Pasaporte ", "Reisepass "]

CARD_OS = [
    ("NXP", "JCOP", ["3 J330", "4.7 P73", "5.1", "6.0 P60", "3.1 R2"]),
    ("Giesecke+Devrient", "Sm@rtCafe Expert", ["7.0", "8.0 R2"]),
    ("Atos", "CardOS", ["V5.3", "V5.4", "V6.0"]),
    ("Atos", "CardOS DI", ["V5.0"]),
    ("Gemalto", "MultiApp", ["V4.2", "V5.0"]),
    ("STARCOS", "", ["3.5", "3.7"]),
    ("Athena", "IDProtect", ["2.4", "3.1"]),
]

OPTION_UNITS = [  # (name, part)
    ("FAX Unit", "h"), ("Fax Option", "h"), ("FIPS Hard Disk Kit", "h"), ("HDD Encryption Kit", "h"),
    ("Data Security Kit", "a"), ("Network Interface Card", "h"), ("Card Reader", "h"), ("Wireless LAN Unit", "h"),
    ("Overwrite Kit", "a"), ("PKI Card System", "a"), ("Scan Extension Kit", "a"),
]

MFP_EXTRA_FAMILIES = [
    ("Kyocera", "TASKalfa", ["2554ci", "3554ci", "4054ci", "5054ci", "6054ci", "7054ci"]),
    ("Brother", "MFC-L", ["9570CDW", "8900CDW", "6900DW", "6800DW", "5900DW"]),
    ("Panasonic", "DP-MB", ["545", "536", "310"]),
    ("OKI", "MC", ["883dn", "873dnv", "853dn", "363dn"]),
    ("Epson", "WorkForce Enterprise", ["WF-C20590", "WF-C17590", "WF-C21000", "WF-M21000"]),
    ("Konica Minolta", "bizhub", ["C4050i", "C3350i", "C4000i", "C3300i", "4750i", "4050i"]),
    ("Canon", "imageRUNNER", ["2630i", "2645i", "2660i", "2625i"]),
    ("Pantum", "CM", ["9500", "8000", "7300"]),
]

SW_EXTRA = [  # vendor, product, part hint, versions
    ("Splunk", "Enterprise", "a", ["8.2.6", "9.0.1", "9.1.2"]),
    ("Elastic", "Elasticsearch", "a", ["7.17.4", "8.4.0", "8.11.1"]),
    ("Zimbra", "Collaboration Suite", "a", ["8.8.15", "9.0.0", "10.0"]),
    ("Docker", "Engine", "a", ["20.10.9", "23.0.1", "24.0.5"]),
    ("Siemens", "SIMATIC WinCC", "a", ["7.5 SP2", "8.0", "V17"]),
    ("Check Point", "Gaia", "o", ["R80.40", "R81", "R81.20"]),
    ("Arista", "EOS", "o", ["4.24.2F", "4.26.4M", "4.28.3M"]),
    ("Palo Alto Networks", "PAN-OS", "o", ["9.1.12", "10.0.8", "10.2.3"]),
    ("Debian", "Linux", "o", ["10", "11", "12"]),
    ("Apple", "iOS", "o", ["15.4", "16.1", "17.0"]),
    ("Apache", "Tomcat", "a", ["8.5.82", "9.0.65", "10.1.5"]),
    ("Okta", "Verify", "a", ["2.1", "3.0"]),
    ("Thales", "Luna Network HSM", "a", ["7.7.1", "7.8.4"]),
    ("Entrust", "nShield Connect", "a", ["12.72", "13.2"]),
    ("Trellix", "Application Control", "a", ["8.3.4", "8.3.6"]),
    ("Dell", "OpenManage Enterprise", "a", ["3.8", "4.0", "4.1"]),
    ("Veeam", "Backup and Replication", "a", ["11.0.1", "12.0"]),
    ("NetApp", "ONTAP", "o", ["9.7", "9.9.1", "9.12.1"]),
]

NETWORK_EXTRA = [
    ("Palo Alto Networks", "PA-", ["220", "820", "3220", "5220", "5450", "7080"], "PAN-OS", ["9.1.12", "10.1.6", "10.2.3-h4"]),
    ("Huawei", "S", ["5735-S", "6730-H", "12700", "7700", "9700"], "VRP", ["V200R019C10", "V200R021C00"]),
    ("Extreme Networks", "", ["X440-G2", "X460-G2", "X590", "X695", "5420M", "5520"], "ExtremeXOS", ["22.7.1", "31.1", "31.7"]),
    ("Dell", "PowerSwitch", ["S5248F-ON", "S5296F-ON", "N3248TE-ON", "Z9432F-ON"], "OS10", ["10.5.1", "10.5.3"]),
    ("HPE", "Aruba CX", ["6300M", "6405", "8325", "8360", "10000"], "AOS-CX", ["10.06", "10.09", "10.10.1010"]),
    ("Check Point", "", ["6200", "6500", "6700", "16200", "26000"], "Gaia", ["R80.40", "R81.10", "R81.20"]),
    ("WatchGuard", "Firebox", ["M290", "M390", "M590", "M690", "T45", "T85"], "Fireware", ["12.5.4", "12.8", "12.10.2"]),
    ("SonicWall", "NSa", ["2700", "3700", "4700", "5700", "6700"], "SonicOS", ["7.0.1", "7.1.1"]),
    ("Ubiquiti", "UniFi", ["USW-24-PoE", "USW-48", "USW-Pro-24", "USW-Enterprise-8-PoE"], "UniFi OS", ["3.2.7", "4.0.6"]),
]

NOISE_FUNCS = [
    lambda: f" (ANSSI-CC-{random.choice([2022, 2023, 2024, 2025, 2026])}/{random.randint(1, 60):02d}{random.choice(['', '', '-R01'])})",
    lambda: f" (EUCC-{random.randint(1000, 9999)}-{random.choice([2024, 2025])}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d})",
    lambda: f" (BSI-DSZ-CC-{random.randint(900, 1500):04d}-{random.choice([2022, 2023, 2024])})",
    lambda: " [Common Criteria EAL4+]",
    lambda: " --- The certificate comprises two configurations with different EAL levels.",
]


def add_noise(text: str) -> str:
    return text + random.choice(NOISE_FUNCS)() if random.random() < 0.18 else text


def glue(text: str, vendor: Optional[str]) -> str:
    """Simulate text-extraction artifacts: vendor and product run together."""
    if vendor and random.random() < 0.06:
        return text.replace(f"{vendor} ", vendor, 1)
    return text


def maybe_vendor(vendor: Optional[str], p: float = 0.7) -> Tuple[Optional[str], bool]:
    shown = bool(vendor) and random.random() < p
    return (vendor if shown else None), shown


def pick_version() -> str:
    return random.choice([
        f"{random.randint(1, 9)}.{random.randint(0, 9)}",
        f"{random.randint(1, 15)}.{random.randint(0, 20)}.{random.randint(0, 9)}",
        f"{random.randint(1, 12)}.{random.randint(0, 9)}.{random.randint(0, 9)}.{random.randint(0, 99)}",
    ])


def mk(ext_units: List[ExtractedUnit], comps: Optional[List[CompanionComponent]] = None) -> TOEExtraction:
    return TOEExtraction(clauses=[ClauseGroup(targets=ext_units, companions=comps or [])])


# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

def p_mfp(long_list: bool = False):
    """Printers/MFPs: shared prefix expansion, ROM/firmware companions, optional kits (D5)."""
    vendor, prefix, pool = random.choice(PRINTER_MFP_FAMILIES + MFP_EXTRA_FAMILIES)
    if long_list:  # synthesize extra codes to reach 8-16 models
        base = [c for c in pool]
        while len(base) < 12:
            base.append(f"{random.choice(['C', 'M', 'B', ''])}{random.randint(300, 9999)}{random.choice(['', 'i', 'a', 'e'])}")
        k = random.randint(8, min(16, len(base)))
        codes = random.sample(base, k)
    else:
        codes = random.sample(pool, random.randint(2, min(7, len(pool))))
    ven, shown = maybe_vendor(vendor, 0.85)
    text, units = format_slash_or_comma_models(
        vendor, prefix, codes, include_vendor=shown,
        repeat_prefix_mode=random.choice(["first_only", "all", "some"]),
        sep=random.choice(["/", ",_and", ","]),
    )
    # device-class words are noise (R5): they appear in the text, never in the output
    text += random.choice(["", " Series", " Multifunction Systems", " Multi-Function Printers", " Single Function Printers",
                           " multifunction printers (MFPs)", " Diskless models", " for Asia Pacific"])
    comps, ctext = [], []
    style = random.choice(["rom_pair", "fw", "sys", "kit_fw", "kit_fw"])
    if style == "rom_pair":
        cv = f"{random.randint(1, 21)}.{random.randint(0, 120)}.{random.randint(1, 45)}"
        comps.append(CompanionComponent(vendor=None, product="Controller ROM", part="o", versions=[cv]))
        if random.random() < 0.5:
            fv = f"{random.randint(1, 5)}.{random.randint(0, 15)}.{random.randint(1, 20)}"
            comps.append(CompanionComponent(vendor=None, product="FAX ROM", part="o", versions=[fv]))
            ctext.append(f"Controller ROM Ver. {cv}, FAX ROM Ver. {fv}")
        else:
            ctext.append(f"Controller ROM Ver. {cv}")
    elif style == "fw":
        fv = random.choice(["G00-10", "E-1.00", "J-1.00", f"{random.randint(1, 9)}.{random.randint(0, 99)}",
                            f"{random.randint(1000, 4999)}", f"{random.randint(1, 9)}.{random.randint(10, 99)}.{random.randint(1, 20)}"])
        comps.append(CompanionComponent(vendor=None, product="Firmware", part="o", versions=[fv]))
        ctext.append(random.choice([f"Firmware Version {fv}", f"firmware {fv}", f"Version: {fv}", f"Ver. {fv}"]))
    elif style == "sys":
        sv = f"{random.randint(1, 25)}.{random.randint(10, 199)}.{random.randint(0, 20)}"
        comps.append(CompanionComponent(vendor=None, product="System Software", part="o", versions=[sv]))
        ctext.append(f"System Software Version {sv}")
    else:  # options/kits are companions; part numbers and cert ids are noise (D5)
        kits = random.sample(OPTION_UNITS, random.randint(1, 3))
        for name, part in kits:
            comps.append(CompanionComponent(vendor=None, product=name, part=part, versions=["-"]))
        fv = f"{random.randint(1, 9)}.{random.randint(0, 99)}.{random.randint(0, 9)}"
        comps.append(CompanionComponent(vendor=None, product="Firmware", part="o", versions=[fv]))
        names = [k[0] for k in kits]
        kit_txt = ", ".join(names[:-1]) + (" and " if len(names) > 1 else "") + names[-1]
        ctext.append(random.choice([f"with {kit_txt} Firmware {fv}", f"all of the above with {kit_txt}, Firmware Version: {fv}"]))
    out = glue(f"{text} {' '.join(ctext)}".strip(), vendor if shown else None)
    return add_noise(out), mk(units, comps)


def p_oem():
    group = random.choice(OEM_MULTI_BRAND_GROUPS)
    units, segs = [], []
    n = random.randint(2, 3)
    for vd, prefix, pool in group:
        codes = random.sample(pool, min(n, len(pool)))
        seg = []
        for i, c in enumerate(codes):
            name = f"{prefix} {c}".strip() if prefix else c
            units.append(ExtractedUnit(vendor=vd, product=name, part="h", version="-"))
            seg.append((f"{vd} {name}".strip() if vd else name) if i == 0 else (name if random.random() < 0.7 else c))
        segs.append(random.choice(["/", " / "]).join(seg))
    fw = random.choice(["A2X00Y0-0100-G00-53", "G00-11", "G00-45", "E-1.00", "V1.00E", "A55V0Y0-0100-G00-10pki"])
    label = random.choice(["Control Software Version:", "Firmware", "Control Software, version:"])
    comps = [CompanionComponent(vendor=None, product="Control Software" if "Control" in label else "Firmware", part="o", versions=[fw])]
    text = f"{random.choice([' / ', ', ']).join(segs)} {label} {fw}"
    return add_noise(text), mk(units, comps)


def p_network():
    n = random.choice([1, 2])
    clauses, texts = [], []
    pool_fams = NETWORK_APPLIANCE_FAMILIES + NETWORK_EXTRA * 2
    for vd, prefix, hw_pool, os_name, vers_pool in random.sample(pool_fams, n):
        if not prefix:  # bare numbers without a family word are not usable products (D7)
            hw_pool = [m for m in hw_pool if re.search(r"[A-Za-z]", m)]
            if len(hw_pool) < 2:
                continue
        models = random.sample(hw_pool, random.randint(2, min(6, len(hw_pool))))
        ven, shown = maybe_vendor(vd, 0.85)
        hw_text, units = format_slash_or_comma_models(vd, prefix, models, include_vendor=shown, repeat_prefix_mode="first_only", sep=",_and")
        noun = random.choice(["", " Series Switches", " Routers", " Appliances", " Ethernet Switches", " Platforms"])  # R5: text only
        vers = random.sample(vers_pool, min(2 if (n == 1 and random.random() < 0.4) else 1, len(vers_pool)))
        part = "o"
        comps = [CompanionComponent(vendor=ven if random.random() < 0.5 else None, product=os_name, part=part, versions=vers)]
        verb = random.choice(["running", "operating with", "with", "running Software version"])
        texts.append(f"{hw_text}{noun} {verb} {os_name} {random.choice(['version ', 'v', ''])}{' and '.join(vers)}")
        clauses.append(ClauseGroup(targets=units, companions=comps))
    if not clauses:
        return p_mfp()
    return add_noise(" and ".join(texts)), TOEExtraction(clauses=clauses)


def _chips(k_max: int):
    vendor, noun, pool = random.choice(CHIP_FAMILIES)
    chips = random.sample(pool, random.randint(1, min(k_max, len(pool))))
    ven, shown = maybe_vendor(vendor, 0.6)
    return vendor, noun, chips, ven, shown


def p_chip_libs():
    """IC with optional libraries (libraries are `a` companions)."""
    vendor, noun, chips, ven, shown = _chips(4)
    units = [ExtractedUnit(vendor=ven, product=c, part="h", version="-") for c in chips]
    cs = chips[0] if len(chips) == 1 else ", ".join(chips[:-1]) + " and " + chips[-1]
    libs = random.sample([
        ("RSA", ["1.02.013", "2.07.003"]), ("EC", ["1.02.013", "2.07.003"]), ("SHA-2", ["1.01", "1.03.006"]),
        ("SCL", ["2.02.012"]), ("Toolbox", ["1.02.013", "1.03.006"]), ("Crypto Library", ["2.1", "3.0"]),
        ("HSL", ["2.0", "3.03.006"]), ("ACL", ["3.33.003"]),
    ], random.randint(1, 4))
    comps, lt = [], []
    for name, vs in libs:
        use = vs[: random.choice([1, 1, 2])]
        comps.append(CompanionComponent(vendor=None, product=name, part="a", versions=use))
        lt.append(f"{name} v{' or v'.join(use)}")
    lj = lt[0] if len(lt) == 1 else ", ".join(lt[:-1]) + " and " + lt[-1]
    text = f"{(vendor + ' ') if shown else ''}{noun + ' ' if noun else ''}{cs} with optional {lj} libraries and with specific IC dedicated software"
    return add_noise(glue(text.strip(), vendor if shown else None)), mk(units, comps)


def p_chip_rev():
    """Chip revisions go in the hardware version (D10)."""
    vendor, noun, chips, ven, shown = _chips(3)
    rev = random.choice(CHIP_REV_VALUES)
    units = [ExtractedUnit(vendor=ven, product=c, part="h", version=rev) for c in chips]
    cs = " and ".join(chips) if len(chips) <= 2 else ", ".join(chips[:-1]) + " and " + chips[-1]
    word = random.choice(CHIP_REV_WORDS).format(r=rev)
    form = random.choice(["a", "b", "c"])
    if form == "a":
        text = f"{(vendor + ' ') if shown else ''}{cs} {word}{random.choice(CHIP_NOUNS)}"
    elif form == "b":
        text = f"{(vendor + ' ') if shown else ''}{cs}{random.choice(CHIP_NOUNS)} {word[0].upper() + word[1:]}"
    else:
        text = f"{(vendor + ' ') if shown else ''}{random.choice(CHIP_NOUNS).strip() or 'Smart Card IC'} {cs}, {word}"
    return add_noise(text.strip()), mk(units)


def p_applet():
    """Applet (a) running on a chip (h) or card OS (o)."""
    applet = random.choice(APPLET_NAMES)
    avendor = random.choice(APPLET_VENDORS)
    ver = random.choice(APPLET_VERSIONS)
    feats = random.sample(APPLET_FEATURES, random.randint(0, 2))  # features are noise (R5)
    lang = random.choice(["en", "en", "fr", "es", "de"])
    on = {"en": random.choice(["on", "embedded in", "running on"]), "fr": random.choice(["sur composant", "sur"]),
          "es": "sobre", "de": "auf"}[lang]
    verw = {"en": random.choice(["version", "v", "V", "Version"]), "fr": random.choice(["version", "révision"]),
            "es": "versión", "de": "Version"}[lang]
    lead = random.choice(ICAO_LEAD) if lang in ("fr", "es", "de") else ""
    if random.random() < 0.55:
        vendor, noun, chips, cv, cshown = _chips(2)
        rev = random.choice([None, None, random.choice(CHIP_REV_VALUES)])
        comp = [CompanionComponent(vendor=cv, product=c, part="h", versions=[rev or "-"]) for c in chips]
        chip_txt = "/".join(chips) + (f"/{rev}" if rev and random.random() < 0.3 else "")
        tail = f"{on} {(vendor + ' ') if cshown else ''}{chip_txt}"
    else:
        osv, osn, osvers = random.choice(CARD_OS)
        v_os = random.choice(osvers)
        osname = osn or osv
        comp = [CompanionComponent(vendor=osv if osn else None, product=osname, part="o", versions=[v_os])]
        tail = f"{on} {osv + ' ' if osn else ''}{osname} {v_os}"
    ven, shown = maybe_vendor(avendor, 0.7)
    unit = ExtractedUnit(vendor=ven, product=applet, part="a", version=ver)
    feat_txt = (" " + " ".join(f"{f}" for f in feats)) if feats else ""
    cfg = random.choice(["", "", f" [{random.choice(['EAC', 'PACE', 'BAC'])} configuration]"])
    vsep = "" if verw in ("v", "V") else " "
    text = f"{lead}{(avendor + ' ') if shown else ''}{applet}{feat_txt}{cfg} {verw}{vsep}{ver} {tail}".replace("  ", " ")
    return add_noise(glue(text.strip(), avendor if shown else None)), mk([unit], comp)


def p_card_os():
    osv, osn, vers = random.choice(CARD_OS)
    v = random.choice(vers)
    name = osn or osv
    ven = osv if osn else None
    unit = ExtractedUnit(vendor=ven, product=name, part="o", version=v)
    if random.random() < 0.5:
        vendor, noun, chips, cv, cshown = _chips(1)
        comp = [CompanionComponent(vendor=cv, product=chips[0], part="h", versions=["-"])]
        text = f"{(ven + ' ') if ven else ''}{name} {v} on {(vendor + ' ') if cshown else ''}{chips[0]}{random.choice(['', ' Secure Element', ' Smart Card IC'])}"
        return add_noise(text), mk([unit], comp)
    return add_noise(f"{(ven + ' ') if ven else ''}{name} {v}"), mk([unit])


def p_multilingual(nvd: NvdPart):
    """French / German / Spanish certificate titles for chips + library."""
    vendor, noun, chips, ven, shown = _chips(6)
    lang = random.choice(["fr", "de", "es"])
    lib, lv = random.choice([("SCL", "2.02"), ("Crypto Library", "3.1"), ("Toolbox", "1.3"), ("HSL", "2.0"), ("ACL", "3.33")])
    tpl = {
        "fr": ("Microcontrôleurs sécurisés", "incluant optionnellement la librairie cryptographique {l} {w} {v}", ["révision", "version"]),
        "de": ("Sichere Mikrocontroller", "einschließlich optionaler kryptographischer Bibliothek {l} {w} {v}", ["Version"]),
        "es": ("Microcontroladores seguros", "incluyendo la biblioteca criptográfica opcional {l} {w} {v}", ["versión"]),
    }[lang]
    units = [ExtractedUnit(vendor=ven, product=c, part="h", version="-") for c in chips]
    cs = ", ".join(chips[:-1]) + {"fr": " et ", "de": " und ", "es": " y "}[lang] + chips[-1] if len(chips) > 1 else chips[0]
    comp = [CompanionComponent(vendor=None, product=lib, part="a", versions=[lv])]
    lib_txt = tpl[1].format(l=lib, w=random.choice(tpl[2]), v=lv)
    text = f"{tpl[0]} {(vendor + ' ') if shown else ''}{cs} {lib_txt}"
    return add_noise(text), mk(units, comp)


def p_inline_versions():
    models = ["MS431", "MS531", "MS632", "M3250", "M5255", "CS431", "CX431", "MX431de", "MX532adwe", "B2338dw"]
    fws = ["LW20.PR4.P235", "LW20.DN4.P231", "LW30.VY2.P120", "LW50.PR2.P120", "LW40.TL4.P310"]
    chosen = random.sample(models, random.randint(3, 6))
    clauses, parts = [], []
    for m in chosen:
        fw = random.choice(fws)
        clauses.append(ClauseGroup(targets=[ExtractedUnit(vendor="Lexmark", product=m, part="h", version="-")],
                                   companions=[CompanionComponent(vendor="Lexmark", product="Firmware", part="o", versions=[fw])]))
        parts.append(f"{m}({fw})")
    joined = ", ".join(parts[:-1]) + ", and " + parts[-1]
    return add_noise(f"Lexmark {joined} {random.choice(['Single Function Printers', 'Printers', 'Multifunction Printers'])}"), TOEExtraction(clauses=clauses)


def p_standalone(multi_fams, apps, oss, nvd: NvdPart, stats: Counter):
    mode = random.choice(["curated", "curated", "extra", "nvd_app_os", "nvd_dual", "nvd_hw_fw"])
    if mode in ("curated", "extra"):
        if mode == "curated":
            vd, pn, part, vers, sub = random.choice(ENTERPRISE_SW_OS_EXAMPLES)
        else:
            vd, pn, part, vers = random.choice(SW_EXTRA)
            sub = ""
        maj = nvd.major(pn)
        if maj in ("a", "o") and maj != part:
            stats["part_fixed_to_nvd_majority"] += 1
            part = maj
        ver = random.choice(vers)
        # editions / LTS / architecture are dropped from the version (D4)
        ver_out = re.sub(r"\s*(Platinum Edition|LTS|LTSR)$", "", ver).strip()
        kw = random.choice(["v", "V", "Version ", "Version: ", ", Version ", "Release ", ""])
        dec = lambda s: s + random.choice(["", "", "®", "™"])
        text = f"{dec(vd)} {dec(pn)}{(' ' + sub) if sub and random.random() < 0.7 else ''} {kw}{ver}".strip()
        return add_noise(text), mk([ExtractedUnit(vendor=vd, product=pn, part=part, version=ver_out)])
    if mode == "nvd_dual" and len(apps) >= 2:
        (v1, p1, r1), (v2, p2, r2) = random.sample(apps, 2)
        return (f"{v1} {p1} v{r1} and {v2} {p2} v{r2}",
                TOEExtraction(clauses=[ClauseGroup(targets=[ExtractedUnit(vendor=v1, product=p1, part="a", version=r1)], companions=[]),
                                       ClauseGroup(targets=[ExtractedUnit(vendor=v2, product=p2, part="a", version=r2)], companions=[])]))
    if mode == "nvd_hw_fw" and multi_fams:
        vs, prefix, sibs = random.choice(multi_fams)
        picked = random.sample(sibs, random.randint(2, min(5, len(sibs))))
        vd = picked[0][2]
        codes = []
        for _, pd, _ in picked:
            suf = pd[len(prefix):].strip() if pd.startswith(prefix) else pd
            codes.append(suf or pd)
        text, units = format_slash_or_comma_models(vd, prefix, codes, include_vendor=True,
                                                   repeat_prefix_mode=random.choice(["first_only", "all"]), sep=random.choice(["/", ",_and"]))
        fv = f"{random.randint(1, 9)}.{random.randint(0, 20)}.{random.randint(1, 50)}"
        fn = random.choice(["Firmware", "System Firmware", "Controller Firmware"])
        return (f"{text} {fn} Version {fv}",
                mk(units, [CompanionComponent(vendor=None, product=fn, part="o", versions=[fv])]))
    use_app = random.random() < 0.65 and apps
    pool = apps if use_app else oss
    vd, pn, ver = random.choice(pool)
    part = "a" if use_app else "o"
    if random.random() < 0.25:
        ver += random.choice([" Update 2", " SP1", " Service Pack 3", " Patch 2"])
    fmt = random.choice([f"v{ver}", f"V{ver}", f"Version {ver}", f", Version {ver}", f"Release {ver}", f"{ver}"])
    return add_noise(f"{vd} {pn} {fmt}".strip()), mk([ExtractedUnit(vendor=vd, product=pn, part=part, version=ver)])


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def build_records(n_total: int, seed: int, gold_path: str, cache_path: str, cpe_path: str):
    random.seed(seed)
    block = GoldBlocklist(gold_path)
    nvd = NvdPart(cache_path)
    multi_fams, apps, oss = load_cpe_families(cpe_path)
    stats: Counter = Counter()
    weights = [
        ("mfp", 0.11), ("mfp_long", 0.05), ("oem", 0.06), ("network", 0.13), ("chip_libs", 0.06), ("inline", 0.03),
        ("standalone", 0.20), ("applet", 0.12), ("card_os", 0.04), ("chip_rev", 0.05), ("multilingual", 0.07), ("mfp_kit", 0.08),
    ]
    names, ws = zip(*weights)
    recs, seen = [], set()
    attempts = 0
    while len(recs) < n_total and attempts < n_total * 20:
        attempts += 1
        kind = random.choices(names, ws)[0]
        if kind == "mfp":
            inp, ext = p_mfp()
        elif kind == "mfp_kit":
            inp, ext = p_mfp()
        elif kind == "mfp_long":
            inp, ext = p_mfp(long_list=True)
        elif kind == "oem":
            inp, ext = p_oem()
        elif kind == "network":
            inp, ext = p_network()
        elif kind == "chip_libs":
            inp, ext = p_chip_libs()
        elif kind == "inline":
            inp, ext = p_inline_versions()
        elif kind == "applet":
            inp, ext = p_applet()
        elif kind == "card_os":
            inp, ext = p_card_os()
        elif kind == "chip_rev":
            inp, ext = p_chip_rev()
        elif kind == "multilingual":
            inp, ext = p_multilingual(nvd)
        else:
            inp, ext = p_standalone(multi_fams, apps, oss, nvd, stats)
        why = block.hit(inp, ext)
        if why:
            stats["rejected_gold_overlap"] += 1
            continue
        if inp in seen:
            stats["rejected_duplicate"] += 1
            continue
        seen.add(inp)
        r = format_chatml_record(inp, ext)
        r["kind"] = kind
        recs.append(r)
        stats["kind:" + kind] += 1
    return recs, stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold", default="data/gold/gold_template.json")
    ap.add_argument("--cache", default="data/cpe_index/cpe_lookup_cache.json")
    ap.add_argument("--cpe", default="data/cpe_index/extracted_cpe_targets.json")
    ap.add_argument("--n_train", type=int, default=2200)
    ap.add_argument("--n_val", type=int, default=200)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--sample", type=int, default=0, help="print N samples and write nothing")
    ap.add_argument("--out_dir", default=None, help="folder for synthetic_train.jsonl / synthetic_val.jsonl")
    a = ap.parse_args()

    n = a.sample if a.sample else a.n_train + a.n_val
    recs, stats = build_records(n, a.seed, a.gold, a.cache, a.cpe)
    if a.sample:
        for i, r in enumerate(recs, 1):
            print(f"--- {i} [{r['kind']}]")
            print("IN :", r["input"])
            print("OUT:", r["output_json"])
        print("\nstats:", dict(stats))
        return
    if not a.out_dir:
        raise SystemExit("give --out_dir (never data/synthetic/) or use --sample N")
    if os.path.abspath(a.out_dir).rstrip("/").endswith("data/synthetic"):
        raise SystemExit("refusing to write into data/synthetic/ (baseline files)")
    os.makedirs(a.out_dir, exist_ok=True)
    clean = [{k: v for k, v in r.items() if k != "kind"} for r in recs]
    for name, part in (("synthetic_train.jsonl", clean[: a.n_train]), ("synthetic_val.jsonl", clean[a.n_train: a.n_train + a.n_val])):
        with open(os.path.join(a.out_dir, name), "w", encoding="utf-8") as f:
            for r in part:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"[v2] wrote {min(a.n_train, len(clean))} train + {max(0, len(clean) - a.n_train)} val -> {a.out_dir}")
    print("[v2] stats:", dict(stats))


if __name__ == "__main__":
    main()
