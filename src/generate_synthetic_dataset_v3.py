"""
Synthetic training-data generator v3 (codebook v1.1).

Built on top of generate_synthetic_dataset_v2.py (left untouched). Same SYSTEM_PROMPT, same record
format, same gold blocklist and the same total size, so train_qwen.py and the notebooks work unchanged.

Why v3 exists: the error analysis of adapter v1 on the gold set (results/v1/, report section 7.5)
showed error classes for which v2 had no matching pattern. Each new pattern below is a GENERAL rule
written from the codebook, with invented vocabulary; no gold title, product name or model code is copied
(the gold blocklist and scripts/check_gold_clean.py enforce this).

New patterns (codebook v1.1 additions in brackets)
  chip_dedsw     IC + "IC Dedicated Software": chip is h, the software is an o companion, class words
                 ("Secure Smart Card Controller") are dropped, a trailing revision is the chip version  [D12]
  chip_ref       "chip (reference ABC rev. F)": revision goes to the chip version, the reference code is noise [D10]
  class_strip    device-class words before a model code are dropped ("Secure Flash Memory W75..." -> W75...) [D3]
  series_list    family + bare numbers + "Series Switches" + "Running the X Operating System"; also
                 "Family FW 3.1 Series E, Series E2" with plain Firmware companion                         [D3,R8]
  gateway_sw     standalone firewall / gateway / UTM software is o; NAC / management software is a;
                 "(ABC)" acronyms and trailing "Software" are dropped                                       [D2,R5]
  edition_patch  editions and patch ids are dropped; "LTS" never stays in product or version              [D4,D5]
  func_rom       "with Copy, Print, Fax, Scan and StorageController ROM Ver. x": the function list is noise,
                 the ROMs are o companions ("Storage Controller ROM", "Fax ROM")                           [R3,R5]
  module_table   printer family + a table of 5-10 firmware modules (o) and hardware modules (h), each with a version
  acronym_suite  suite title listing acronym products, each its own `a` item with its own version                 [R7]
  brand_version  "Brand v8.1": brand is the product, v-number is the version                              [R4]
  multiword_vendor vendor stays out of the product for multi-word vendors                                  [R9]
Existing v2 patterns are kept; chip_libs now also emits "IC Dedicated Software" as an o companion
when the title mentions it (v2 ignored it).

Usage (never writes into data/synthetic/ or data/synthetic_v2/):
  python src/generate_synthetic_dataset_v3.py --sample 40
  python src/generate_synthetic_dataset_v3.py --out_dir data/synthetic_v3
"""
import argparse
import json
import os
import random
import re
import string
from collections import Counter
from typing import List, Optional

import generate_synthetic_dataset_v2 as v2
from cpe_resolver import ClauseGroup, CompanionComponent, ExtractedUnit, TOEExtraction
from generate_synthetic_dataset import format_chatml_record, format_slash_or_comma_models

# generic codebook phrases the model is meant to learn (never counted as gold vocabulary leakage)
v2.GENERIC_OK |= {"ic_dedicated_software", "storage_controller_rom", "crypto_library", "cryptographic_library"}

mk, add_noise, glue, maybe_vendor, pick_version = v2.mk, v2.add_noise, v2.glue, v2.maybe_vendor, v2.pick_version


# ---------------------------------------------------------------------------
# Invented vocabulary helpers
# ---------------------------------------------------------------------------

def rand_code(style: Optional[str] = None) -> str:
    L = lambda n: "".join(random.choices(string.ascii_uppercase, k=n))
    D = lambda n: "".join(random.choices(string.digits, k=n))
    style = style or random.choice(["LLDDDL", "LDDDDL", "LLLDDD", "LDDLL", "LLDDDLD", "LDDDD"])
    out = ""
    for ch in style:
        out += L(1) if ch == "L" else D(1)
    return out


BRANDS = ["Zentry", "Corvana", "Quillon", "Brightlane", "Nexora", "Velmark", "Orbitek", "Halvern", "Tessara", "Norvik",
          "Kelvane", "Drumlin", "Mavrick", "Solenta", "Pyrane", "Wexler", "Ardent", "Lumora", "Brenwick", "Talvane"]
KNOWN_VENDORS = ["Fortinet", "Barracuda", "Sophos", "WatchGuard", "Juniper", "Stormshield", "Check Point", "Zyxel", "Huawei", "Cisco"]
MULTI_VENDORS = ["Alcatel-Lucent Enterprise", "Hewlett Packard Enterprise", "Palo Alto Networks", "Juniper Networks",
                 "Extreme Networks", "Arista Networks", "Zyxel Communications", "Cisco Systems", "Trend Micro", "Dell Technologies"]
FAMILY_WORDS = ["OmniStack", "NetCore", "EdgeLine", "SwitchPro", "MeshLink", "AccessPoint X", "FlexRoute", "CoreLine", "PortMaster"]
CLASS_NOUNS = ["Secure Smart Card Controller", "Smart Card Controller", "Secure Flash Memory", "Security Controller",
               "Secure Microcontroller", "Hardware Security Module", "Smart Card Reader", "Fingerprint Reader",
               "Wireless Access Point", "Industrial Router", "Baseboard Management Controller", "Network Switch"]
CHIP_VENDORS = ["NXP", "Infineon", "STMicroelectronics", "Samsung", "Renesas", "Winbond", "Microchip", "Fudan Microelectronics", None]
GW_NOUNS_O = ["Edge Gateway", "Firewall", "UTM", "Web Gateway", "Perimeter Firewall", "Threat Prevention Firewall",
              "Mail Gateway", "VPN Gateway", "Edge Firewall"]
GW_NOUNS_A = ["Policy Manager", "Security Management", "Endpoint Manager", "Log Manager", "Identity Server", "Device Compliance Manager"]
EDITIONS = ["Enterprise Edition", "Standard Edition", "Enterprise Extended Edition", "Advanced Edition", "Community Edition",
            "Professional Edition", "Express Edition"]
SW_BASES = ["Database Server", "Application Server", "Message Broker", "Directory Server", "Storage Manager", "Report Server"]
OS_BASES = ["Rocky Linux", "AlmaLinux", "openSUSE Leap", "Linux Mint", "Zorin OS", "Corvex Linux", "Halvern OS"]
FUNC_LISTS = ["Copy, Print, Fax, Scan", "Copy, Print, Scan", "Print, Copy and Scan", "Copy, Print, Fax and Scan"]


def vtext(ver: str) -> str:
    return random.choice([f"v{ver}", f"V{ver}", f"Version {ver}", f"version {ver}", f"Ver. {ver}", f", Version {ver}", f" {ver}"]).strip()


def rand_ver(kind: str = "plain") -> str:
    a, b, c = random.randint(1, 12), random.randint(0, 9), random.randint(0, 9)
    if kind == "plain":
        return random.choice([f"{a}.{b}", f"{a}.{b}.{c}", f"{a}.{b}.{c}.{random.randint(1, 99):02d}"])
    if kind == "hw":
        return f"{a}.{b}.{c}.{random.randint(1, 99):02d}HW{random.randint(1, 9):02d}"
    if kind == "build":
        return random.choice([f"{a}.{b}R{random.randint(1, 20)}", f"V{random.randint(100, 900)}R{random.randint(10, 30)}C{random.randint(0, 20):02d}SPC{random.randint(100, 300)}",
                              f"{a}.{b}.{c}{random.choice('abcdefjmpqrs')}"])
    return f"{a}.{b}"


def unit(vendor, product, part, version="-"):
    return ExtractedUnit(vendor=vendor, product=product, part=part, version=version)


def comp(product, part, ver="-", vendor=None):
    return CompanionComponent(vendor=vendor, product=product, part=part, versions=[ver])


# ---------------------------------------------------------------------------
# New patterns
# ---------------------------------------------------------------------------

def p_chip_dedsw():
    """IC + IC Dedicated Software (D12): chip h with revision, software o companion, class words dropped."""
    vendor = random.choice(CHIP_VENDORS)
    noun = random.choice(CLASS_NOUNS[:6] + ["Smart Card IC", "Smart Card IC", "Security IC"])
    n = random.choice([1, 1, 1, 2])
    codes = [rand_code() for _ in range(n)]
    rev = random.choice([None, None, "VB", "VC", "RV11", "RV27", "A02", "B11", "2", "r1p0"])
    revtxt = {None: "", }.get(rev) if rev is None else random.choice([f" {rev}", f" Version {rev}", f" rev. {rev}", f" revision {rev}"])
    cs = " and ".join(codes)
    ven, shown = maybe_vendor(vendor, 0.75)
    incl = random.choice(["including", "with", "incorporating", "together with", "embedding", "bundled with", "and"])
    sw = random.choice(["IC Dedicated Software", "IC Dedicated Software", "IC Dedicated Support Software"])
    tail = f"{incl} {sw}"
    lib_noise = random.choice(["", "", "", "", " and cryptographic library", " and Toolbox (T1/T2)", " and Crypto Library (R2)", ", Flash Loader"])
    order = random.choice(["noun_first", "code_first"])
    lead = f"{vendor + ' ' if shown else ''}"
    if order == "noun_first":
        text = f"{lead}{noun} {cs}{revtxt} {tail}{lib_noise}"
    else:
        text = f"{lead}{cs} {noun}{revtxt} {tail}{lib_noise}"
    units = [unit(ven, c, "h", rev or "-") for c in codes]
    return add_noise(glue(text.strip(), vendor if shown else None)), mk(units, [comp(sw, "o")])


def p_chip_ref():
    """Chip with a reference code and a revision: revision is the version, reference is noise (D10)."""
    vendor = random.choice([v for v in CHIP_VENDORS if v] + [None])
    code = rand_code()
    ref = rand_code("LLDDDLD")
    rev = random.choice(["A", "B", "C", "F", "G", "A01", "B2"])
    noun = random.choice(["Integrated circuit", "Security IC", "microcontroller", "Smart Card IC", "secure chip"])
    refw = random.choice(["reference", "ref.", "identifier", "mask reference"])
    revw = random.choice(["rev.", "revision", "version", "design step"])
    ven, shown = maybe_vendor(vendor, 0.8)
    text = f"{vendor + ' ' if shown else ''}{code} {noun} ({refw} {ref} {revw} {rev})"
    return add_noise(text), mk([unit(ven, code, "h", rev)])


def p_class_strip():
    """Device-class words before a model code are dropped (D3)."""
    vendor = random.choice(["Winbond", "Microchip", "Infineon", "NXP", "Zyxel", "Dell", None, "Nuvoton"])
    noun = random.choice(CLASS_NOUNS)
    n = random.choice([1, 1, 2])
    code = rand_code()
    codes = [code] if n == 1 else [code, code[:-1] + random.choice(string.ascii_uppercase)]
    ver = random.choice(["-", "-", rand_ver("short"), rand_ver("short")])
    ven, shown = maybe_vendor(vendor, 0.75)
    cs = codes[0] if n == 1 else f"{codes[0]}, {codes[1]}"
    text = f"{vendor + ' ' if shown else ''}{noun} {cs}" + ("" if ver == "-" else f" {vtext(ver)}")
    if noun in ("Hardware Security Module", "Network Switch") and ver != "-":
        pass
    return add_noise(text), mk([unit(ven, c, "h", ver) for c in codes])


def p_series_list():
    """Family + bare numbers + class words, or Family FW x Series E, Series E2 (D3, R8)."""
    vendor = random.choice(KNOWN_VENDORS + MULTI_VENDORS + [None])
    ven, shown = maybe_vendor(vendor, 0.8)
    mode = random.choice(["numbers", "numbers", "fw_series", "alpha_list"])
    fam = random.choice(["ZR", "NX", "KX", "PXR", "TQ", "VLX", "HG"]) + random.choice(["10", "20", "300", "7", "5"]) if mode == "numbers" else random.choice(FAMILY_WORDS + [f"{rand_code('LLL')}"])
    lead = f"{vendor + ' ' if shown else ''}"
    if mode == "numbers":
        nums = random.sample(["3900", "5200", "6800", "8900", "2300", "4100", "7600", "1200"], random.randint(1, 3))
        os_name = random.choice(["ZOS", "NetOS", "EdgeOS", "XOS", "CoreOS"]) + random.choice(["", "", "-Q"])
        osv = rand_ver("plain")
        cls = random.choice(["Series Switches", "Series Routers", "Series", "Series Ethernet Switches"])
        hw = " and ".join(nums) if len(nums) <= 2 else ", ".join(nums[:-1]) + " and " + nums[-1]
        runs = random.choice(["Running the {o} Operating System", "running {o}", "with {o}", "Running {o} Operating System"]).format(o=os_name)
        text = f"{lead}{fam} {hw} {cls} {runs} {vtext(osv)}"
        units = [unit(ven, f"{fam} {x}", "h") for x in nums]
        return add_noise(text), mk(units, [comp(os_name, "o", osv)])
    if mode == "fw_series":
        fwv = rand_ver("plain")
        series = random.sample(["E", "E2", "X", "X2", "S", "S3", "M"], random.randint(2, 4))
        text = f"{lead}{fam} FW {fwv} " + ", ".join(f"Series {s}" for s in series)
        units = [unit(ven, f"{fam} Series {s}", "h") for s in series]
        return add_noise(text), mk(units, [comp("Firmware", "o", fwv)])
    # alpha_list: product-line name kept, vendor dropped, model codes expand with the family prefix
    codes = [rand_code("LLDDD") for _ in range(random.randint(2, 3))]
    first = f"{lead}{fam} {codes[0]}"
    text = first + ", " + ", ".join(codes[1:])
    return add_noise(text), mk([unit(ven, f"{fam} {c}", "h") for c in codes])


def p_gateway_sw():
    """Standalone gateway / firewall software is o; management / NAC software is a (D2)."""
    is_o = random.random() < 0.65
    noun = random.choice(GW_NOUNS_O if is_o else GW_NOUNS_A)
    part = "o" if is_o else "a"
    mode = random.choice(["known", "known", "brand"])
    brand = random.choice(BRANDS)
    ver = rand_ver(random.choice(["plain", "plain", "hw", "build"]))
    acr = "".join(w[0] for w in noun.split()[:3]).upper()
    if mode == "known":
        vendor = random.choice(KNOWN_VENDORS)
        prod = f"{brand} {noun}"
        ven_out = vendor
        lead = f"{vendor} {brand} {noun}"
    else:  # brand is the vendor-less product name (kept in the product)
        prod = f"{brand} {noun}"
        ven_out = None
        lead = f"{brand} {noun}"
    suffix = random.choice(["", "", f" ({acr})", f" ({acr}) Software", " Software"])
    # Software / (ABC) never stay in the product name (R5)
    text = f"{lead}{suffix} {vtext(ver)}"
    return add_noise(text), mk([unit(ven_out, prod, part, ver)])


def p_edition_patch():
    """Editions and patch ids are dropped; LTS never stays (D4, D5)."""
    if random.random() < 0.55:
        vendor = random.choice(["Fujitsu", "Corvex", "Halvern", "Tessara", "Orbitek", "Norvik"])
        base = random.choice(SW_BASES)
        ed = random.choice(EDITIONS)
        ver = rand_ver("plain")
        patch = ""
        if random.random() < 0.6:
            ids = [f"T{random.randint(100000, 999999)}QP-{random.randint(1, 9):02d}" for _ in range(random.choice([1, 2]))]
            patch = f"(with patch {' and '.join(ids)})"
        prod = f"{base.split()[0]} {base.split()[1]}" if random.random() < 0.0 else base
        text = f"{vendor} {prod} {ed} {ver}{patch}".replace("  ", " ")
        return add_noise(text), mk([unit(vendor, prod, "a", ver)])
    osn = random.choice(OS_BASES)
    ver = random.choice([f"{random.choice([16, 18, 20, 22, 24])}.04.{random.randint(1, 6)}", f"{random.randint(7, 15)}.{random.randint(0, 6)}"])
    form = random.choice(["{o} LTS {v}", "{o} {v} LTS", "{o} {v} (LTS)", "{o} Long Term Support {v}"])
    text = form.format(o=osn, v=ver)
    extra, comps = "", []
    if random.random() < 0.4:
        a, av = random.choice([("KVM", "")]), f"{random.randint(1, 5)}.{random.randint(0, 9)}"
        extra = f" with KVM and QEMU {av}"
        comps = [comp("KVM", "a"), comp("QEMU", "a", av)]
    return add_noise(text + extra), mk([unit(None, osn, "o", ver)], comps)


def p_func_rom():
    """Printer models with a function list and ROM companions (R3, R5)."""
    vendor, prefix, pool = random.choice(v2.PRINTER_MFP_FAMILIES + v2.MFP_EXTRA_FAMILIES)
    codes = random.sample(pool, random.randint(2, min(6, len(pool))))
    ven, shown = maybe_vendor(vendor, 0.9)
    text, units = format_slash_or_comma_models(vendor, prefix, codes, include_vendor=shown,
                                               repeat_prefix_mode=random.choice(["first_only", "first_only", "all"]),
                                               sep=random.choice(["/", ",_and"]))
    funcs = random.choice(FUNC_LISTS)
    over = random.choice(["", "", "Overwrite "])
    cv = f"{random.randint(1, 3)}.{random.randint(0, 9)}.{random.randint(1, 30)}{random.choice(['', 'A', 'B'])}"
    comps = [comp("Storage Controller ROM", "o", cv)]
    ctext = f"{over}StorageController ROM Ver. {cv}"
    if random.random() < 0.7:
        fv = f"{random.randint(1, 5)}.{random.randint(0, 9)}.{random.randint(0, 9)}"
        comps.append(comp("Fax ROM", "o", fv))
        ctext += f", Fax ROM Ver. {fv}"
    text = f"{text} models with {funcs} and {ctext}"
    return add_noise(glue(text, vendor if shown else None)), mk(units, comps)


def p_brand_version():
    """Brand v8.1: the brand is the product, the v-number the version (R4)."""
    brand = random.choice(BRANDS)
    ven = random.choice([None, None, None, random.choice(["Zentra Systems", "Halvern Corp"])])
    ver = rand_ver("plain")
    extra = random.choice(["", "", " Appliance", " Platform", " Suite"])  # class word stays only when it is a product word
    prod = brand
    text = f"{ven + ' ' if ven else ''}{brand}{extra} {random.choice(['v', 'V', 'version ', 'Version '])}{ver}"
    # appliance/platform/suite are class words (R5): dropped
    return add_noise(text), mk([unit(ven, prod, "a", ver)])


def p_multiword_vendor():
    """Multi-word vendor shown in the text; the product keeps only the product-line name (R9)."""
    vendor = random.choice(MULTI_VENDORS)
    fam = random.choice(FAMILY_WORDS)
    ver = rand_ver("plain")
    osn = random.choice(["AOS", "OS-X", "NetOS", "ROS"])
    osv = f"{random.randint(5, 9)}.{random.randint(0, 9)}.{random.randint(1, 9)}.R{random.randint(1, 15):02d}"
    text = f"{vendor} {fam} with {osn} {osv}"
    return add_noise(text), mk([unit(vendor, fam, "h")], [comp(osn, "o", osv)])


MODULES_SW = ["Boot Loader", "Panel Driver", "Image Processor", "Font Pack", "Duplex Unit", "Paper Handler", "Display Firmware",
              "Security Module", "Job Log", "Address Book", "Language Pack", "Mail Client", "Stamp Data", "Barcode Font",
              "Finisher Control", "Tray Control", "Driver Pack", "Color Profile", "Sleep Manager", "Update Agent"]
MODULES_HW = ["Key Chip", "Memory Board", "Storage Board", "Interface Card", "Control Board"]


def p_module_table():
    """Printer family with a long table of firmware modules (o) and hardware modules (h), each with its own version (R3, R7)."""
    vendor, prefix, pool = random.choice(v2.PRINTER_MFP_FAMILIES + v2.MFP_EXTRA_FAMILIES)
    codes = random.sample(pool, random.randint(1, min(3, len(pool))))
    ven, shown = maybe_vendor(vendor, 0.9)
    text, units = format_slash_or_comma_models(vendor, prefix, codes, include_vendor=shown,
                                               repeat_prefix_mode="first_only", sep=random.choice(["/", ","]))
    sw = random.sample(MODULES_SW, random.randint(5, 10))
    comps, parts = [], []
    for m in sw:
        mv = random.choice([f"{random.randint(1, 3)}.{random.randint(0, 9):02d}", f"{random.randint(0, 2)}{random.randint(0, 9)}.{random.randint(0, 9)}{random.randint(0, 9)}.{random.randint(0, 9)}{random.randint(0, 9)}",
                            f"{random.randint(1, 9)}.{random.randint(0, 9)}.{random.randint(0, 9)}"])
        comps.append(comp(m, "o", mv))
        parts.append(f"{m} {mv}")
    head = random.choice(["Software:", "Firmware:", "Firmware modules:", "Software versions:"])
    text = f"{text} all of above with {random.choice(['Facsimile Function', 'Fax Function', 'Scan Function'])} {head} " + ", ".join(parts)
    if random.random() < 0.5:
        hw = random.sample(MODULES_HW, random.randint(1, 2))
        hp = []
        for h in hw:
            hv = f"{random.randint(0, 9)}{random.randint(0, 9)}{random.randint(0, 9)}{random.randint(0, 9)}"
            comps.append(comp(h, "h", hv))
            hp.append(f"{h} {hv}")
        text += " Hardware: " + ", ".join(hp)
    return add_noise(text), mk(units, comps)


def p_acronym_suite():
    """A software suite that lists acronym products, each with its own version; each acronym is its own `a` product (R7)."""
    vendor = random.choice(["Halvern", "Tessara", "Corvex", "Orbitek", "Norvik", "Quillon"])
    suite = random.choice(["Operations Intelligence", "Network Insight", "Service Assurance", "Infrastructure Manager", "Data Platform"])
    n = random.randint(3, 6)
    acrs = []
    while len(acrs) < n:
        a = "".join(random.choices(string.ascii_uppercase, k=random.choice([3, 3, 4])))
        if a not in acrs:
            acrs.append(a)
    items = []
    units = []
    for a in acrs:
        av = rand_ver("plain")
        items.append(f"{a} {av}")
        units.append(unit(None, a, "a", av))
    sep = random.choice([" - ", ": ", ", "])
    text = f"{random.choice(['', '', 'Corp '])}{vendor}{random.choice(['®', '', '™'])} {suite}{sep}" + ", ".join(items)
    return add_noise(text), mk(units)


def p_chip_libs_v3():
    """v2's chip + libraries, plus the IC Dedicated Software o companion that v2 ignored."""
    inp, ext = v2.p_chip_libs()
    if "IC dedicated software" in inp:
        ext.clauses[0].companions.append(comp("IC Dedicated Software", "o"))
        inp = inp.replace("specific IC dedicated software", "IC Dedicated Software")
    return inp, ext


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def build_records(n_total: int, seed: int, gold_path: str, cache_path: str, cpe_path: str, use_cpe: bool = True):
    random.seed(seed)
    block = v2.GoldBlocklist(gold_path)
    nvd = v2.NvdPart(cache_path)
    if use_cpe:
        multi_fams, apps, oss = v2.load_cpe_families(cpe_path)
    else:
        multi_fams, apps, oss = [], [], []
        print("[v3] --no_cpe: standalone NVD-mined modes disabled (local test only)")
    stats: Counter = Counter()

    def standalone():
        if not use_cpe:  # local test: only the curated modes
            random.seed(random.random())
            for _ in range(10):
                try:
                    inp, ext = v2.p_standalone(multi_fams, apps, oss, nvd, stats)
                    return inp, ext
                except IndexError:
                    continue
            return p_brand_version()
        return v2.p_standalone(multi_fams, apps, oss, nvd, stats)

    makers = {
        # kept from v2 (weights scaled down to make room)
        "mfp": lambda: v2.p_mfp(), "mfp_kit": lambda: v2.p_mfp(), "mfp_long": lambda: v2.p_mfp(long_list=True),
        "oem": v2.p_oem, "network": v2.p_network, "chip_libs": p_chip_libs_v3, "inline": v2.p_inline_versions,
        "standalone": standalone, "applet": v2.p_applet, "card_os": v2.p_card_os, "chip_rev": v2.p_chip_rev,
        "multilingual": lambda: v2.p_multilingual(nvd),
        # new in v3
        "chip_dedsw": p_chip_dedsw, "chip_ref": p_chip_ref, "class_strip": p_class_strip, "series_list": p_series_list,
        "gateway_sw": p_gateway_sw, "edition_patch": p_edition_patch, "func_rom": p_func_rom,
        "brand_version": p_brand_version, "multiword_vendor": p_multiword_vendor,
        "module_table": p_module_table, "acronym_suite": p_acronym_suite,
    }
    weights = [
        ("mfp", 0.04), ("mfp_kit", 0.03), ("mfp_long", 0.02), ("oem", 0.03), ("network", 0.07), ("chip_libs", 0.04),
        ("inline", 0.02), ("standalone", 0.08), ("applet", 0.06), ("card_os", 0.03), ("chip_rev", 0.03), ("multilingual", 0.04),
        ("chip_dedsw", 0.08), ("chip_ref", 0.03), ("class_strip", 0.05), ("series_list", 0.07), ("gateway_sw", 0.09),
        ("edition_patch", 0.05), ("func_rom", 0.04), ("brand_version", 0.03), ("multiword_vendor", 0.02),
        ("module_table", 0.05), ("acronym_suite", 0.03),
    ]
    names, ws = zip(*weights)
    recs, seen, attempts = [], set(), 0
    while len(recs) < n_total and attempts < n_total * 30:
        attempts += 1
        kind = random.choices(names, ws)[0]
        try:
            inp, ext = makers[kind]()
        except (IndexError, ValueError):
            stats["generator_error:" + kind] += 1
            continue
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
    ap.add_argument("--sample", type=int, default=0)
    ap.add_argument("--no_cpe", action="store_true", help="local test without extracted_cpe_targets.json")
    ap.add_argument("--out_dir", default=None)
    a = ap.parse_args()
    n = a.sample if a.sample else a.n_train + a.n_val
    recs, stats = build_records(n, a.seed, a.gold, a.cache, a.cpe, use_cpe=not a.no_cpe)
    if a.sample:
        for i, r in enumerate(recs, 1):
            print(f"--- {i} [{r['kind']}]\nIN : {r['input']}\nOUT: {r['output_json']}")
        print("\nstats:", dict(stats))
        return
    if not a.out_dir:
        raise SystemExit("give --out_dir (never data/synthetic or data/synthetic_v2) or use --sample N")
    norm = os.path.abspath(a.out_dir).rstrip("/")
    if norm.endswith("data/synthetic") or norm.endswith("data/synthetic_v2"):
        raise SystemExit("refusing to overwrite baseline / v2 data")
    os.makedirs(a.out_dir, exist_ok=True)
    clean = [{k: v for k, v in r.items() if k != "kind"} for r in recs]
    for name, part in (("synthetic_train.jsonl", clean[: a.n_train]), ("synthetic_val.jsonl", clean[a.n_train: a.n_train + a.n_val])):
        with open(os.path.join(a.out_dir, name), "w", encoding="utf-8") as f:
            for r in part:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"[v3] wrote {min(a.n_train, len(clean))} train + {max(0, len(clean) - a.n_train)} val -> {a.out_dir}")
    print("[v3] stats:", dict(stats))


if __name__ == "__main__":
    main()
