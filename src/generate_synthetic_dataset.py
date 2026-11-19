import json
import os
import random
import re
from collections import defaultdict
from typing import Dict, List, Literal, Tuple

from cpe_resolver import (
    ClauseGroup,
    CompanionComponent,
    ExtractedUnit,
    TOEExtraction,
)

SYSTEM_PROMPT = (
    "You are an expert security evaluation analyst extracting Target of Evaluation (TOE) "
    "product configurations into structured JSON.\n"
    "Rules:\n"
    "1. Expand shorthand or slash/comma-separated model lists by inheriting shared family prefixes "
    "(e.g. 'DocuCentre-IV C2265/C2263' -> 'DocuCentre-IV C2265', 'DocuCentre-IV C2263').\n"
    "2. Group primary hardware or standalone products into `targets` and place shared OS, firmware, "
    "ROM modules, or optional software/hardware kits into `companions` for that clause.\n"
    "3. When a sentence contains distinct product groups with different versions "
    "(e.g., 'Model A running OS v1.0 and Model B running OS v2.0'), emit separate `clauses`.\n"
    "4. Set `version` to '-' ONLY for base hardware when no version is directly attached. "
    "For standalone software (`part='a'`) or standalone OS (`part='o'`), put its version directly in `target.version`.\n"
    "5. Ignore certification metadata noise such as '(ANSSI-CC-...)', '(EUCC-...)', or EAL level descriptions."
)


# =====================================================================
# 1. Mine Real Product Families & Vocabularies from extracted_cpe_targets.json
# =====================================================================

def clean_title_product(title: str, vendor_slug: str) -> Tuple[str, str]:
    """
    Given a CPE human title like 'Cisco Catalyst 2960-24TT-L' and vendor 'cisco',
    splits out a human vendor display string and a clean product display string.
    """
    title_ascii = re.sub(r"[^\x00-\x7F®™]+", "", title).strip()
    if not title_ascii:
        title_ascii = title.strip()

    tokens = title_ascii.split()
    if not tokens:
        return vendor_slug.capitalize(), title_ascii

    v_norm = vendor_slug.replace("_", "").replace("-", "").lower()
    for n_tok in (3, 2, 1):
        if len(tokens) > n_tok:
            cand = "".join(tokens[:n_tok]).lower()
            cand_clean = re.sub(r"[^a-z0-9]", "", cand)
            if cand_clean == v_norm or (len(v_norm) >= 4 and cand_clean.startswith(v_norm)):
                v_disp = " ".join(tokens[:n_tok])
                p_disp = " ".join(tokens[n_tok:])
                return v_disp, p_disp

    return vendor_slug.capitalize(), title_ascii


def load_cpe_families(cpe_path: str = "data/cpe_index/extracted_cpe_targets.json", max_entries: int = 1700000):
    """
    Extracts prefix-grouped hardware families, OS/firmware items, and standalone software
    from `extracted_cpe_targets.json`.
    """
    print(f"[SyntheticGenerator] Mining product families from {cpe_path}...")
    with open(cpe_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    hw_families: Dict[str, Dict[str, List[Tuple[str, str, str]]]] = defaultdict(lambda: defaultdict(list))
    hw_seen = set()

    standalone_apps: List[Tuple[str, str, str]] = []
    app_seen = set()

    os_items: List[Tuple[str, str, str]] = []
    os_seen = set()

    for entry in data[:max_entries]:
        idx = entry.rfind(" - cpe:2.3:")
        if idx == -1:
            continue
        title = entry[:idx].strip()
        if any(ord(ch) > 127 and ch not in "®™" for ch in title):
            continue

        cpe = entry[idx + 3:]
        parts = cpe.split(":")
        if len(parts) < 6:
            continue
        part, vendor, product, version = parts[2], parts[3], parts[4], parts[5]

        if "\\" in product or len(product) < 3:
            continue

        if part == "h" and (vendor, product) not in hw_seen:
            hw_seen.add((vendor, product))
            v_disp, p_disp = clean_title_product(title, vendor)
            if version not in ("-", "*"):
                p_disp = re.sub(r"\s+" + re.escape(version) + r"$", "", p_disp, flags=re.I).strip()

            p_tokens = p_disp.split()
            if len(p_tokens) >= 2:
                family_prefix = " ".join(p_tokens[:-1])
                last_tok = p_tokens[-1]
                if any(c.isdigit() for c in last_tok) and len(last_tok) >= 2:
                    hw_families[vendor][family_prefix].append((product, p_disp, v_disp))
            elif len(p_tokens) == 1 and any(c.isdigit() for c in p_tokens[0]):
                m = re.match(r"^([A-Za-z\-]+)\d", p_tokens[0])
                if m and len(m.group(1)) >= 2:
                    hw_families[vendor][m.group(1)].append((product, p_disp, v_disp))

        elif part == "a" and version not in ("-", "*") and len(version) <= 18:
            if (vendor, product) not in app_seen and len(standalone_apps) < 8000:
                app_seen.add((vendor, product))
                v_disp, p_disp = clean_title_product(title, vendor)
                p_disp = re.sub(r"\s+(v|version\s+|release\s+)?" + re.escape(version) + r".*$", "", p_disp, flags=re.I).strip()
                if p_disp and len(p_disp) >= 3 and not any(c.isdigit() for c in p_disp[-3:]):
                    standalone_apps.append((v_disp, p_disp, version))

        elif part == "o" and version not in ("-", "*") and not product.endswith("_firmware"):
            if (vendor, product, version) not in os_seen and len(os_items) < 5000:
                os_seen.add((vendor, product, version))
                v_disp, p_disp = clean_title_product(title, vendor)
                p_disp = re.sub(r"\s+(v|version\s+|release\s+)?" + re.escape(version) + r".*$", "", p_disp, flags=re.I).strip()
                if p_disp and len(p_disp) >= 3:
                    os_items.append((v_disp, p_disp, version))

    multi_model_families = []
    for vendor, fam_dict in hw_families.items():
        for prefix, models in fam_dict.items():
            if len(models) >= 2:
                multi_model_families.append((vendor, prefix, models))

    print(
        f"[SyntheticGenerator] Found {len(multi_model_families)} multi-model hardware families, "
        f"{len(standalone_apps)} standalone apps, {len(os_items)} OS entries."
    )
    return multi_model_families, standalone_apps, os_items


# =====================================================================
# 2. Domain-Specific Curated Vocabularies for High-Fidelity Compounding
# =====================================================================

PRINTER_MFP_FAMILIES = [
    ("Fuji Xerox", "DocuCentre-IV", ["C2265", "C2263", "C3370", "C4470", "C5570"]),
    ("Fuji Xerox", "ApeosPort-VI", ["C7771", "C6671", "C5571", "C4471", "C3371", "C3370", "C2271"]),
    ("Fuji Xerox", "DocuCentre-VI", ["C7771", "C6671", "C5571", "C4471", "C3371", "C3370", "C2271"]),
    ("Fuji Xerox", "ApeosPort-VII", ["C7773", "C6673", "C5573", "C4473", "C3373", "C2273", "C7788", "C6688", "C5588"]),
    ("Xerox", "WorkCentre", ["5632", "5638", "5645", "5655", "5665", "5675", "5687", "7830", "7835", "7845", "7855"]),
    ("Xerox", "VersaLink", ["B7025", "B7030", "B7035", "C7020", "C7025", "C7030", "B405", "C405"]),
    ("Xerox", "AltaLink", ["B8045", "B8055", "B8065", "B8075", "B8090", "C8030", "C8035", "C8045", "C8055", "C8070"]),
    ("RICOH", "MP", ["C6003", "C5503A", "C4503A", "C3503", "C3003", "3352", "2552"]),
    ("RICOH", "IM", ["C300", "C400", "C530F", "C530FB", "C6500", "C8000", "C7010", "C6000", "C4500"]),
    ("Lexmark", "", ["MX421", "MX521", "MX522", "MX622", "MX622h", "CX622h", "CX625h", "MS622", "MS822", "MS826", "CS622", "CS720", "CS725", "CS820", "CS921", "CS923"]),
    ("SHARP", "BP-", ["B550WD", "B547WD", "B540WR", "B537WR", "70C45", "70C55", "70C65"]),
    ("SHARP", "MX-", ["8081", "7081", "6071", "5071", "4071", "3571", "3071"]),
    ("TOSHIBA", "e-STUDIO", ["2525AC", "3025AC", "3525AC", "4525AC", "5525AC", "6525AC"]),
    ("Canon", "imageRUNNER ADVANCE", ["C350", "C250", "C3520", "C3525", "C3530", "C5535", "C5540", "C5550", "C5560"]),
    ("HP", "Color LaserJet Enterprise MFP", ["M578", "M681", "M682", "M776"]),
    ("HP", "LaserJet Enterprise MFP", ["M528", "M632", "M633", "M634", "M635", "M636", "M725"]),
    ("HP", "Color LaserJet Managed Flow MFP", ["E77822", "E77825", "E77830", "E87640", "E87650", "E87660", "E78323", "E78325", "E78330"]),
    ("HP", "LaserJet Managed Flow MFP", ["E72525", "E72530", "E72535", "E82540", "E82550", "E82560"]),
]

OEM_MULTI_BRAND_GROUPS = [
    [
        (None, "bizhub", ["C754", "C654", "C658", "C558", "C458", "C360i", "C300i", "C250i", "C287", "C227", "754", "654"]),
        (None, "ineo+", ["754", "654", "658", "558", "458", "360i", "300i", "250i", "287", "227"]),
    ],
    [
        ("KONICA MINOLTA", "bizhub", ["C360i", "C300i", "C250i", "C036DNi", "030DNi", "C025DNi"]),
        ("DEVELOP", "ineo+", ["360i", "300i", "250i"]),
    ],
    [
        ("KYOCERA", "TASKalfa", ["3501i", "4501i", "5501i", "6053ci", "5053ci", "4053ci", "3553ci", "6500i", "8000i"]),
        (None, "CS", ["3501i", "4501i", "5501i", "6053ci", "5053ci", "4053ci", "3553ci", "6500i", "8000i"]),
        ("TA Triumph-Adler", "", ["3555i", "4555i", "5555i", "6007ci", "5007ci", "4007ci"]),
        ("UTAX", "", ["6007ci", "5007ci", "4007ci"]),
    ],
    [
        ("RICOH", "IM", ["C7010", "C6000", "C4500", "C3000"]),
        ("nashuatec", "IM", ["C7010", "C6000", "C4500", "C3000"]),
        ("Rex Rotary", "IM", ["C7010", "C6000", "C4500", "C3000"]),
        ("Gestetner", "IM", ["C7010", "C6000", "C4500", "C3000"]),
    ],
]

SMARTCARD_IC_FAMILIES = [
    ("NXP", "Secure Smart Card Controller", ["J3D145_M59", "J2D145_M59", "J3D120_M60", "J3D082_M60", "J2D120_M60", "J2D082_M60"]),
    (None, "Secure Smart Card Controller", ["J3E145_M64", "J3E120_M65", "J3E082_M65", "J2E145_M64", "J2E120_M65", "J2E082_M65"]),
    ("NXP", "Secure Smart Card Controller", ["P60D024MVB", "P60D016MVB", "P60D012MVB", "P6021P VB", "P6021M VB", "P6021D VB"]),
    ("Infineon", "Security Controller", ["M7820 A11", "M7892 B11", "M5072 G11", "M7794 A12", "M7794 G12", "SLC52GDA"]),
    ("Infineon", "Security Controller", ["SLE78CLX1440P", "SLE66CLX800PE", "SLB9670_2.0"]),
    (None, "16-bit RISC Microcontroller for Smart Card", ["S3FT9MF", "S3FT9MT", "S3FT9MS"]),
    (None, "", ["S3D384E", "S3D352E", "S3D300E", "S3D264E", "S3D232E", "S3K384E"]),
    (None, "", ["S3CT9KW", "S3CT9KC", "S3CT9K9", "S3B512C", "SC3512", "S3NSEN6"]),
    ("STMicroelectronics", "Secure Microcontroller", ["ST23YL80B", "SA23YL80C", "ST31P450", "SB23YR48B", "SB23YR80B", "ST33TPHF2ESPI"]),
    ("Philips", "Secure Smart Card Controller", ["P5CC036V1D", "P5CC009V1D"]),
]

NETWORK_APPLIANCE_FAMILIES = [
    ("Juniper Networks", "", ["SRX100", "SRX110", "SRX210", "SRX220", "SRX240", "SRX550", "SRX650", "SRX1400", "SRX3400", "SRX3600", "SRX5600", "SRX5800"], "Junos OS", ["12.1X44-D15.5", "12.1X46-D20", "15.1X49-D150", "18.1R3", "19.2R1", "21.4R2"]),
    ("Juniper", "", ["QFX5100", "QFX5110-48S", "QFX5120-48T", "QFX5200-32C", "QFX10002", "QFX10008", "EX4600", "EX4650-48Y", "EX9200", "EX9251", "MX204", "MX480", "MX960"], "Junos OS", ["13.2X50-D19", "13.2X51-D20", "13.3R1.8", "18.1R1", "18.1R2", "22.3R1"]),
    ("Cisco", "Catalyst", ["9300-24T", "9300-48T", "9300-24P", "9300-48P", "9200-24P", "9200-48P", "6500"], "IOS XE", ["16.12.4", "17.3.1", "17.6.3"]),
    ("Cisco", "ASA", ["5506-X", "5506-H", "5506-W", "5508-X", "5516-X", "5525-X", "5545-X", "5555-X"], "ASA Software", ["9.4(1.13)", "9.8(4)", "9.12(3)12", "9.16(2)"]),
    ("Cisco", "Nexus", ["7000", "9000", "9300", "9500", "3000", "2000"], "NX-OS", ["5.1(a)", "7.0(3)I5(1)", "9.3(5)", "10.2(3)F"]),
    ("Aruba", "", ["2930F", "2930M", "3810M", "5400R", "600", "3000", "6000", "7000"], "ArubaOS", ["6.3", "8.6.0.4", "16.04", "16.10"]),
    ("IronPort", "", ["C160", "C370", "C670", "X1060", "X1070", "S170", "S370"], "AsyncOS", ["7.1", "7.3", "8.5.6", "11.4", "14.2"]),
    ("Blue Coat", "ProxySG", ["SG510", "SG810", "SG900", "SG9000", "S200", "S400"], "SGOS", ["5.5", "6.5.9.1", "6.7.4", "7.3.2"]),
    ("Fortinet", "FortiGate", ["1240B", "3000D", "1500D", "600E", "200F", "100F"], "FortiOS", ["4.0", "5.6.11", "6.4.8", "7.0.5", "7.2.4"]),
    ("F5 Networks", "BIG-IP", ["11050", "8900", "6900", "i5800", "i7800", "i10800"], "Local Traffic Manager", ["10.2.2 Build 763.3 Hotfix 2", "13.1.3.4", "15.1.5.1", "16.1.2"]),
    ("Sidewinder", "G2 Security Appliance", ["210", "310", "315", "410", "415", "510", "515", "1100", "1150", "2150", "2150D", "4150"], "Sidewinder G2 Software", ["6.0", "6.1", "6.1.0.05.E51", "6.1.2.03"]),
    ("Vertiv", "CYBEX", ["SCMV2160DPH", "SC840DVIE", "SC940DVIE", "SC840HE", "SC940HE", "SC840DPE", "SC940DPE", "SC820DPH", "SC840DPH", "SC920DPH", "SC940DPH"], "Firmware", ["44404-E7E7", "44404-E5E5", "38002-C1C1"]),
]

ENTERPRISE_SW_OS_EXAMPLES = [
    ("VMware", "vSphere", "a", ["5.5 Update 2", "6.0 Update 3", "6.7 Update 1", "7.0", "8.0 Update 1"], ""),
    ("VMware", "ESXi", "o", ["5.1", "5.5", "6.5", "7.0 Update 3"], ""),
    ("Rapid7", "Nexpose", "a", ["5.1", "5.14", "6.4", "6.6.12"], "Vulnerability Management and Penetration Testing System"),
    ("EMC", "Avamar", "a", ["7.2.1", "7.5.0", "18.1", "19.4"], ""),
    ("Dell EMC", "Avamar", "a", ["18.1", "19.1", "19.7"], ""),
    ("EMC", "NetWorker", "a", ["8.0.1.4", "9.2.1", "18.2", "19.3"], ""),
    ("Red Hat", "Enterprise Linux", "o", ["5.6", "7.1", "7.6", "8.1", "8.2", "8.4", "9.0"], ""),
    ("Red Hat", "Enterprise Linux AS", "o", ["3 Update 2", "4 Update 5", "5 Update 3"], ""),
    ("SUSE", "Linux Enterprise Server", "o", ["8 with service pack 3", "11 Service Pack 2", "12", "15 SP2", "15 SP4"], ""),
    ("Microsoft", "Windows Server", "o", ["2003", "2008 R2", "2012 R2", "2016", "2019", "2022"], ""),
    ("Pulse", "Connect Secure", "a", ["8.2", "8.3R7", "9.0R3", "9.1"], ""),
    ("Symantec", "Data Loss Prevention", "a", ["14.5", "15.1", "15.8", "16.0"], ""),
    ("Symantec", "Privileged Access Manager", "a", ["3.3.0.1085", "3.4.2", "4.0.1"], ""),
    ("IBM", "Tivoli Identity Manager", "a", ["5.0", "5.1", "6.0"], ""),
    ("IBM", "WebSphere DataPower", "o", ["6.0.2.0", "7.1.0.4", "7.5.2"], "Firmware"),
    ("Citrix", "XenApp", "a", ["6.5", "7.6 Platinum Edition", "7.15 LTSR"], ""),
    ("RSA", "Archer Suite", "a", ["6.5", "6.7", "6.9"], ""),
    ("Fortinet", "FortiProxy", "a", ["1.0", "2.0.5", "7.0.1", "7.2.0"], ""),
    ("Cisco", "AnyConnect Secure Mobility Desktop Client", "a", ["4.1", "4.6", "4.9", "4.10"], ""),
    ("Cisco", "Email Security Appliance", "a", ["9.1", "11.1", "13.5", "14.0"], ""),
    ("CyberArk", "Privileged Account Security Solution", "a", ["9.1", "10.8", "11.5", "12.2"], ""),
    ("Varonis", "Data Security Platform", "a", ["8.5", "8.6", "8.7"], ""),
    ("Cigent", "PBA Software", "a", ["2.0", "2.1.4", "3.0"], ""),
    ("Sybase", "Replication Server", "a", ["15.2", "15.7.1", "16.0"], ""),
    ("Oracle", "Database 11g Enterprise Edition", "a", ["11.1.0.7", "11.2.0.4", "12.1.0.2", "19c"], ""),
    ("Intel", "SOA Expressway", "a", ["2.7.0.4", "2.8.1"], ""),
    ("Layer7", "API Gateway", "a", ["10.0.00", "10.1.00", "11.0"], ""),
    ("BAE Systems", "STOP", "o", ["8.2", "8.8.2", "9.0"], ""),
]


# =====================================================================
# 3. Template Generators for All Compounding Archetypes
# =====================================================================

def format_slash_or_comma_models(
    vendor_disp: str,
    prefix: str,
    model_codes: List[str],
    include_vendor: bool = True,
    repeat_prefix_mode: str = "first_only",
    sep: str = "/",
) -> Tuple[str, List[ExtractedUnit]]:
    units = []
    text_parts = []
    v_val = vendor_disp if (include_vendor and vendor_disp) else None

    for i, code in enumerate(model_codes):
        full_prod = f"{prefix} {code}".strip() if (prefix and not prefix.endswith("-")) else f"{prefix}{code}".strip()
        units.append(ExtractedUnit(vendor=v_val, product=full_prod, part="h", version="-"))

        if i == 0:
            text_parts.append(full_prod)
        else:
            if repeat_prefix_mode == "all":
                text_parts.append(full_prod)
            elif repeat_prefix_mode == "some" and random.random() < 0.4:
                text_parts.append(full_prod)
            else:
                text_parts.append(code)

    if sep == "/":
        joined = "/".join(text_parts) if random.random() < 0.7 else " / ".join(text_parts)
    elif sep == ",_and":
        if len(text_parts) == 2:
            joined = f"{text_parts[0]} and {text_parts[1]}"
        else:
            joined = ", ".join(text_parts[:-1]) + random.choice([", and ", " and ", " & "]) + text_parts[-1]
    else:
        joined = ", ".join(text_parts)

    if include_vendor and vendor_disp:
        v_decorated = vendor_disp + random.choice(["", "®", "™", " Inc."]) if random.random() < 0.25 else vendor_disp
        return f"{v_decorated} {joined}".strip(), units
    return joined.strip(), units


def gen_pattern_1_mfp_multi_rom() -> Tuple[str, TOEExtraction]:
    vendor_disp, prefix, pool = random.choice(PRINTER_MFP_FAMILIES)
    k = random.randint(2, min(7, len(pool)))
    codes = random.sample(pool, k)
    include_vendor = random.random() < 0.85
    sep = random.choice(["/", ",_and", ","])
    repeat_mode = random.choice(["first_only", "all", "some"])

    base_text, units = format_slash_or_comma_models(
        vendor_disp, prefix, codes, include_vendor=include_vendor, repeat_prefix_mode=repeat_mode, sep=sep
    )

    same_vendor_fams = [f for f in PRINTER_MFP_FAMILIES if f[0] == vendor_disp and f[1] != prefix]
    if same_vendor_fams and random.random() < 0.3:
        _, prefix2, pool2 = random.choice(same_vendor_fams)
        codes2 = random.sample(pool2, random.randint(2, min(5, len(pool2))))
        text2, units2 = format_slash_or_comma_models(
            vendor_disp, prefix2, codes2, include_vendor=False, repeat_prefix_mode="first_only", sep="/"
        )
        if include_vendor and vendor_disp:
            for u in units2:
                u.vendor = vendor_disp
        base_text = f"{base_text} {text2}"
        units.extend(units2)

    descriptor = random.choice([
        "",
        " Series",
        " Series Controller Software for Asia Pacific",
        " Multifunction Systems",
        " Multi-Function Printers",
        " Multifunction Printer Diskless models",
        " Single Function Printers",
        " multifunction printers (MFPs)",
    ])
    base_text += descriptor

    companions: List[CompanionComponent] = []
    comp_texts: List[str] = []

    style = random.choice(["rom_pair", "kyocera_subsystems", "lexmark_fw_se", "hp_futuresmart", "ricoh_ver", "simple_ver"])

    if style == "rom_pair":
        c_ver = f"{random.randint(1, 21)}.{random.randint(0, 120)}.{random.randint(1, 45)}"
        companions.append(CompanionComponent(vendor=None, product="Controller ROM", part="o", versions=[c_ver]))
        if random.random() < 0.55:
            f_ver = f"{random.randint(1, 5)}.{random.randint(0, 15)}.{random.randint(1, 20)}"
            companions.append(CompanionComponent(vendor=None, product="FAX ROM", part="o", versions=[f_ver]))
            comp_texts.append(f"Controller ROM Ver. {c_ver}, FAX ROM Ver. {f_ver}")
        else:
            comp_texts.append(f"Version: Controller ROM Ver. {c_ver}")

    elif style == "kyocera_subsystems":
        if random.random() < 0.7:
            companions.append(CompanionComponent(vendor=None, product="Data Security Kit (E)", part="a", versions=["-"]))
            companions.append(CompanionComponent(vendor=None, product="FAX System (W)", part="a", versions=["-"]))
            comp_texts.append("with Data Security Kit (E), FAX System (W)")
        sys_v = f"2N{random.randint(1,9)}_2000.C0{random.randint(1,5)}.{random.randint(100,300)}"
        pan_v = f"2N{random.randint(1,9)}_7000.C0{random.randint(1,5)}.0{random.randint(10,99)}"
        fax_v = f"3N{random.randint(1,9)}_5100.B0{random.randint(1,5)}.00{random.randint(1,9)}"
        companions.extend([
            CompanionComponent(vendor=None, product="System", part="o", versions=[sys_v]),
            CompanionComponent(vendor=None, product="Panel", part="o", versions=[pan_v]),
            CompanionComponent(vendor=None, product="FAX", part="o", versions=[fax_v]),
        ])
        comp_texts.append(f"System:{sys_v} Panel:{pan_v} FAX:{fax_v}")

    elif style == "lexmark_fw_se":
        fw_v = random.choice(["MXTGM.052.025", "CXTZJ.052.025", "MSTGM.052.025", "073.239", "081.234"])
        companions.append(CompanionComponent(vendor=None, product="Firmware", part="o", versions=[fw_v]))
        se_pn = f"57X0{random.randint(100, 999)}"
        companions.append(CompanionComponent(vendor=vendor_disp if include_vendor else None, product=f"Secure Element (P/N {se_pn})", part="h", versions=["-"]))
        comp_texts.append(f"with firmware version {fw_v} and {vendor_disp + ' ' if include_vendor else ''}Secure Element (P/N {se_pn})")

    elif style == "hp_futuresmart":
        fs_v = random.choice(["4.10", "4.11.0.1", "4.12.0.1", "5.3"])
        companions.append(CompanionComponent(vendor="HP", product="FutureSmart Firmware", part="o", versions=[fs_v]))
        if random.random() < 0.5:
            comp_texts.append(f"with HP FutureSmart {fs_v} Firmware")
        else:
            full_sentence = f"HP FutureSmart {fs_v} Firmware for the {base_text}"
            return full_sentence, TOEExtraction(clauses=[ClauseGroup(targets=units, companions=companions)])

    elif style == "ricoh_ver":
        r_ver = random.choice(["J-1.00", "E-1.00", "E-1.00-H", "G00-10", "G00-11", "G00-45"])
        companions.append(CompanionComponent(vendor=None, product="Firmware", part="o", versions=[r_ver]))
        comp_texts.append(random.choice([f", Version: {r_ver}", f" version {r_ver}", f" {r_ver}"]))

    else:
        v_num = f"{random.randint(1, 25)}.{random.randint(10, 199)}.{random.randint(0, 20)}.000"
        companions.append(CompanionComponent(vendor=None, product="System Software", part="o", versions=[v_num]))
        comp_texts.append(f"System Software Version {v_num}")

    full_sentence = f"{base_text} {' '.join(comp_texts)}".strip()
    return full_sentence, TOEExtraction(clauses=[ClauseGroup(targets=units, companions=companions)])


def gen_pattern_2_oem_multibrand() -> Tuple[str, TOEExtraction]:
    brand_group = random.choice(OEM_MULTI_BRAND_GROUPS)
    units: List[ExtractedUnit] = []
    segments: List[str] = []

    num_models = random.randint(2, 3)
    for v_disp, prefix, code_pool in brand_group:
        chosen_codes = random.sample(code_pool, min(num_models, len(code_pool)))
        seg_parts = []
        for idx, code in enumerate(chosen_codes):
            prod_name = f"{prefix} {code}".strip() if prefix else code
            units.append(ExtractedUnit(vendor=v_disp, product=prod_name, part="h", version="-"))
            if idx == 0:
                seg_parts.append(f"{v_disp} {prod_name}".strip() if v_disp else prod_name)
            else:
                seg_parts.append(prod_name if random.random() < 0.7 else code)
        segments.append("/".join(seg_parts) if random.random() < 0.6 else " / ".join(seg_parts))

    base_text = random.choice([" / ", ", "]).join(segments)
    companions: List[CompanionComponent] = []
    suffix_parts = []

    if random.random() < 0.6:
        opt_kit = random.choice(["FK-514", "Fax Option Type M52", "PKI Card System", "FAX System"])
        companions.append(CompanionComponent(vendor=None, product=opt_kit, part="a", versions=["-"]))
        suffix_parts.append(f"with {opt_kit}" if opt_kit != "PKI Card System" else "PKI Card System")

    fw_ver = random.choice([
        "A2X00Y0-0100-G00-53",
        "A55V0Y0-0100-G00-10pki",
        "G00-11",
        "G00-45",
        "E-1.00",
        "V1.00E",
    ])
    fw_label = random.choice(["Control Software Version:", "Control Software, version:", "Firmware", ""])
    companions.append(
        CompanionComponent(
            vendor=None,
            product="Control Software" if "Control Software" in fw_label else "Firmware",
            part="o",
            versions=[fw_ver],
        )
    )
    suffix_parts.append(f"{fw_label} {fw_ver}".strip())

    full_sentence = f"{base_text} {' '.join(suffix_parts)}".strip()
    return full_sentence, TOEExtraction(clauses=[ClauseGroup(targets=units, companions=companions)])


def gen_pattern_3_multi_clause_network() -> Tuple[str, TOEExtraction]:
    num_clauses = random.choice([1, 2])
    chosen_fams = random.sample(NETWORK_APPLIANCE_FAMILIES, num_clauses)
    clauses: List[ClauseGroup] = []
    clause_texts: List[str] = []

    for vendor_disp, prefix, hw_pool, os_name, ver_pool in chosen_fams:
        k_hw = random.randint(2, min(6, len(hw_pool)))
        models = random.sample(hw_pool, k_hw)
        include_v = random.random() < 0.85

        hw_text, units = format_slash_or_comma_models(
            vendor_disp,
            prefix,
            models,
            include_vendor=include_v,
            repeat_prefix_mode="first_only",
            sep=",_and",
        )
        hw_noun = random.choice(["", " Series Switches", " Routers", " Appliances", " Ethernet Switches", " Series Platforms"])
        hw_text = f"{hw_text}{hw_noun}"

        k_ver = 2 if (num_clauses == 1 and random.random() < 0.45) else 1
        vers = random.sample(ver_pool, min(k_ver, len(ver_pool)))
        ver_str = " and ".join(vers)

        os_vendor = vendor_disp if (include_v and random.random() < 0.5) else None
        companions = [CompanionComponent(vendor=os_vendor, product=os_name, part="o", versions=vers)]

        if num_clauses == 1 and random.random() < 0.4:
            c_text = f"{(os_vendor + ' ') if os_vendor else ''}{os_name} {ver_str} for {hw_text}"
        else:
            verb = random.choice(["running", "operating with", "with", "running Software version"])
            v_kw = random.choice(["version ", "v", ""])
            c_text = f"{hw_text} {verb} {(os_vendor + ' ') if os_vendor else ''}{os_name} {v_kw}{ver_str}".strip()

        clauses.append(ClauseGroup(targets=units, companions=companions))
        clause_texts.append(c_text)

    full_sentence = " and ".join(clause_texts)
    return full_sentence, TOEExtraction(clauses=clauses)


def gen_pattern_4_smartcard_crypto_libraries() -> Tuple[str, TOEExtraction]:
    sub_type = random.choice(["ic_with_libs", "applet_on_ic", "bare_ic_with_cert_noise"])
    vendor_disp, desc_noun, chip_pool = random.choice(SMARTCARD_IC_FAMILIES)

    if sub_type == "ic_with_libs":
        k_chips = random.randint(1, min(4, len(chip_pool)))
        chips = random.sample(chip_pool, k_chips)
        units = [ExtractedUnit(vendor=vendor_disp, product=c, part="h", version="-") for c in chips]
        chip_str = ", ".join(chips[:-1]) + (" and " + chips[-1] if len(chips) > 1 else chips[0])

        prefix_str = f"{vendor_disp + ' ' if vendor_disp else ''}{desc_noun + ' ' if desc_noun else ''}{chip_str}".strip()

        lib_pool = [
            ("RSA2048/4096", ["1.02.013", "2.07.003"]),
            ("EC", ["1.02.013", "2.07.003"]),
            ("SHA-2", ["1.01", "1.03.006"]),
            ("SCL", ["2.02.012"]),
            ("Base", ["1.02.013", "2.07.003"]),
            ("Toolbox", ["1.02.013", "1.03.006"]),
            ("NesLib", ["1.0", "3.0"]),
        ]
        chosen_libs = random.sample(lib_pool, random.randint(2, 5))
        companions: List[CompanionComponent] = []
        lib_texts = []
        for lib_name, lib_vers in chosen_libs:
            use_two = len(lib_vers) > 1 and random.random() < 0.4
            vs = lib_vers if use_two else [lib_vers[0]]
            companions.append(CompanionComponent(vendor=None, product=lib_name, part="a", versions=vs))
            lib_texts.append(f"{lib_name} v{' or v'.join(vs)}")

        libs_joined = ", ".join(lib_texts[:-1]) + " and " + lib_texts[-1]
        full_sentence = f"{prefix_str} with optional {libs_joined} libraries and with specific IC dedicated software"
        return full_sentence, TOEExtraction(clauses=[ClauseGroup(targets=units, companions=companions)])

    elif sub_type == "applet_on_ic":
        k_chips = random.randint(1, min(3, len(chip_pool)))
        chips = random.sample(chip_pool, k_chips)
        units = [ExtractedUnit(vendor=vendor_disp, product=c, part="h", version="-") for c in chips]
        chip_str = "/".join(chips)

        applet_name, applet_ver = random.choice([
            ("XSmart e-Passport", "1.3"),
            ("IDentity Applet", "3.4-p1"),
            ("eTravel Essential", "1.0"),
            ("IAS Classic", "5.2"),
            ("TCOS Identity Card", "1.0 Release 1"),
            ("VITALE application", "2.0.83"),
            ("Athena IDPass ICAO BAC", "3.0"),
        ])
        companions = [CompanionComponent(vendor=None, product=applet_name, part="a", versions=[applet_ver])]
        prep = random.choice(["on", "embedded in", "sur composants", "avec AA sur composant"])
        full_sentence = f"{applet_name} V{applet_ver} {prep} {vendor_disp + ' ' if vendor_disp else ''}{chip_str}"
        if random.random() < 0.35:
            cert_noise = random.choice([
                " (ANSSI-CC-2024/02-R01)",
                " (ANSSI-CC-2025/46)",
                " (EUCC-3090-2025-10-04)",
            ])
            full_sentence += cert_noise
        return full_sentence, TOEExtraction(clauses=[ClauseGroup(targets=units, companions=companions)])

    else:
        k_chips = random.randint(2, min(5, len(chip_pool)))
        chips = random.sample(chip_pool, k_chips)
        units = [ExtractedUnit(vendor=vendor_disp, product=c, part="h", version="-") for c in chips]
        chip_str = "/".join(chips)
        noise = random.choice([
            f" ({chips[0]}_20240730) (ANSSI-CC-2024/02-R01)",
            f" ({chips[0]}_20250630) (EUCC-3090-2025-10-04)",
            " --- The certificate comprises four major configurations with two different EAL levels.",
        ])
        full_sentence = f"{vendor_disp + ' ' if vendor_disp else ''}{chip_str}{noise}"
        return full_sentence, TOEExtraction(clauses=[ClauseGroup(targets=units, companions=[])])


def gen_pattern_5_inline_per_model_versions() -> Tuple[str, TOEExtraction]:
    models_pool = ["MS610e", "MS810e", "MS812e", "M3150", "M5155", "M5163", "M5170", "CS510", "MX410de", "MX511de"]
    fw_codes = ["LW20.PR4.P235CC", "LW20.DN4.P231CC", "LW20.DN7.P231CC", "LW20.VY4.P231CC", "LW50.PR2.P120"]
    k = random.randint(3, 6)
    chosen = random.sample(models_pool, k)
    clauses: List[ClauseGroup] = []
    parts_txt = []

    for m in chosen:
        fw = random.choice(fw_codes)
        clauses.append(
            ClauseGroup(
                targets=[ExtractedUnit(vendor="Lexmark", product=m, part="h", version="-")],
                companions=[CompanionComponent(vendor="Lexmark", product="Firmware", part="o", versions=[fw])],
            )
        )
        parts_txt.append(f"{m}({fw})")

    joined = ", ".join(parts_txt[:-1]) + ", and " + parts_txt[-1]
    full_sentence = f"Lexmark {joined} Single Function Printers"
    return full_sentence, TOEExtraction(clauses=clauses)


def gen_pattern_6_standalone_enterprise_sw_and_cpe(
    multi_model_families: List[Tuple[str, str, List[Tuple[str, str, str]]]],
    standalone_apps: List[Tuple[str, str, str]],
    os_items: List[Tuple[str, str, str]],
) -> Tuple[str, TOEExtraction]:
    """
    Pattern 6: Rich standalone Software / OS with Update/SP/Release/V-prefix versions,
    descriptive marketing subtitles, dual-software combinations, or CPE sibling hardware.
    Ensures the model strongly learns `part='a'` and `part='o'` with direct versions on `targets`.
    """
    mode = random.choice([
        "curated_enterprise_sw",
        "curated_enterprise_sw",
        "cpe_standalone_app_or_os",
        "cpe_dual_app",
        "cpe_hw_siblings_with_fw",
    ])

    if mode == "curated_enterprise_sw":
        v_disp, p_disp, part_type, ver_pool, subtitle = random.choice(ENTERPRISE_SW_OS_EXAMPLES)
        ver = random.choice(ver_pool)
        v_dec = v_disp + random.choice(["", "®", "™"])
        p_dec = p_disp + random.choice(["", "®", "™"])
        sub_str = f" {subtitle}" if (subtitle and random.random() < 0.75) else ""
        ver_kw = random.choice(["v", "V", "Version ", "Version: ", ", Version ", "Release ", ""])
        full_sentence = f"{v_dec} {p_dec}{sub_str} {ver_kw}{ver}".strip()
        unit = ExtractedUnit(vendor=v_disp, product=p_disp, part=part_type, version=ver)
        return full_sentence, TOEExtraction(clauses=[ClauseGroup(targets=[unit], companions=[])])

    elif mode == "cpe_dual_app" and len(standalone_apps) >= 2:
        a1, a2 = random.sample(standalone_apps, 2)
        v1, p1, ver1 = a1
        v2, p2, ver2 = a2
        u1 = ExtractedUnit(vendor=v1, product=p1, part="a", version=ver1)
        u2 = ExtractedUnit(vendor=v2, product=p2, part="a", version=ver2)
        text = f"{v1} {p1} v{ver1} and {v2} {p2} v{ver2}"
        return text, TOEExtraction(
            clauses=[
                ClauseGroup(targets=[u1], companions=[]),
                ClauseGroup(targets=[u2], companions=[]),
            ]
        )

    elif mode == "cpe_hw_siblings_with_fw" and multi_model_families:
        vendor_slug, prefix, siblings = random.choice(multi_model_families)
        k = random.randint(2, min(5, len(siblings)))
        picked = random.sample(siblings, k)
        v_disp = picked[0][2]

        codes = []
        for _, p_disp, _ in picked:
            if p_disp.startswith(prefix):
                suf = p_disp[len(prefix):].strip()
                codes.append(suf if suf else p_disp)
            else:
                codes.append(p_disp)

        sep = random.choice(["/", ",_and"])
        repeat_mode = random.choice(["first_only", "all"])
        text, units = format_slash_or_comma_models(
            v_disp, prefix, codes, include_vendor=True, repeat_prefix_mode=repeat_mode, sep=sep
        )

        fw_ver = f"{random.randint(1, 9)}.{random.randint(0, 20)}.{random.randint(1, 50)}"
        fw_name = random.choice(["Firmware", "System Firmware", "Controller Firmware"])
        companions = [CompanionComponent(vendor=None, product=fw_name, part="o", versions=[fw_ver])]
        text = f"{text} {fw_name} Version {fw_ver}"
        return text, TOEExtraction(clauses=[ClauseGroup(targets=units, companions=companions)])

    else:
        pool = standalone_apps if (random.random() < 0.65 and standalone_apps) else os_items
        part_type: Literal["a", "o"] = "a" if pool is standalone_apps else "o"
        v_disp, p_disp, ver = random.choice(pool)
        # Occasionally append Update / SP suffix
        if random.random() < 0.25:
            ver_extra = random.choice([" Update 2", " SP1", " Service Pack 3", " Patch 2"])
            ver = f"{ver}{ver_extra}"
        ver_fmt = random.choice([f"v{ver}", f"V{ver}", f"Version {ver}", f", Version {ver}", f"Release {ver}", f"{ver}"])
        text = f"{v_disp} {p_disp} {ver_fmt}".strip()
        unit = ExtractedUnit(vendor=v_disp, product=p_disp, part=part_type, version=ver)
        return text, TOEExtraction(clauses=[ClauseGroup(targets=[unit], companions=[])])


def format_chatml_record(raw_input: str, extraction: TOEExtraction) -> Dict[str, str]:
    json_target = json.dumps(extraction.model_dump(), ensure_ascii=False)
    text = (
        f"<|im_start|>system\n{SYSTEM_PROMPT}<|im_end|>\n"
        f'<|im_start|>user\nExtract from: "{raw_input}"<|im_end|>\n'
        f"<|im_start|>assistant\n{json_target}<|im_end|>"
    )
    return {
        "input": raw_input,
        "output_json": json_target,
        "text": text,
    }


def generate_synthetic_dataset(
    num_train: int = 2200,
    num_val: int = 200,
    seed: int = 42,
    train_out: str = "data/synthetic/synthetic_train.jsonl",
    val_out: str = "data/synthetic/synthetic_val.jsonl",
):
    random.seed(seed)
    multi_model_families, standalone_apps, os_items = load_cpe_families()

    records = []
    seen_inputs = set()
    total_needed = num_train + num_val

    attempts = 0
    while len(records) < total_needed and attempts < total_needed * 5:
        attempts += 1
        r = random.random()
        if r < 0.22:
            inp, ext = gen_pattern_1_mfp_multi_rom()
        elif r < 0.35:
            inp, ext = gen_pattern_2_oem_multibrand()
        elif r < 0.52:
            inp, ext = gen_pattern_3_multi_clause_network()
        elif r < 0.65:
            inp, ext = gen_pattern_4_smartcard_crypto_libraries()
        elif r < 0.71:
            inp, ext = gen_pattern_5_inline_per_model_versions()
        else:
            # ~29% standalone enterprise software/OS + CPE dictionary synthesis
            inp, ext = gen_pattern_6_standalone_enterprise_sw_and_cpe(multi_model_families, standalone_apps, os_items)

        if inp not in seen_inputs:
            seen_inputs.add(inp)
            records.append(format_chatml_record(inp, ext))

    train_records = records[:num_train]
    val_records = records[num_train:num_train + num_val]

    for out_path in (train_out, val_out):
        parent = os.path.dirname(out_path)
        if parent:
            os.makedirs(parent, exist_ok=True)

    with open(train_out, "w", encoding="utf-8") as f:
        for rec in train_records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    with open(val_out, "w", encoding="utf-8") as f:
        for rec in val_records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"[SyntheticGenerator] Wrote {len(train_records)} balanced train examples -> {train_out}")
    print(f"[SyntheticGenerator] Wrote {len(val_records)} balanced val examples   -> {val_out}")


if __name__ == "__main__":
    generate_synthetic_dataset()
