import json
import os
import re
from collections import defaultdict
from typing import Dict, List, Literal, Optional, Tuple
from pydantic import BaseModel, Field

# =====================================================================
# 1. Pydantic Schema for Qwen 2.5 3B Structured Output
# =====================================================================

class ExtractedUnit(BaseModel):
    vendor: Optional[str] = Field(
        None,
        description="Explicit vendor/brand name in the text, or null if omitted"
    )
    product: str = Field(
        ...,
        description="Full model or product name with inherited prefixes expanded"
    )
    part: Literal["h", "a", "o"] = Field(
        ...,
        description="'h'=hardware/device/IC, 'a'=application/software/module/library, 'o'=OS/firmware/ROM"
    )
    version: str = Field(
        "-",
        description="Direct version specific to this single unit, or '-' if none / shared in companions"
    )


class CompanionComponent(BaseModel):
    vendor: Optional[str] = Field(
        None,
        description="Explicit vendor if different from target units, else null"
    )
    product: str = Field(
        ...,
        description="OS, firmware, ROM module, library, or kit name (e.g., 'Controller ROM', 'Junos OS', 'Firmware', 'Data Security Kit (E)')"
    )
    part: Literal["h", "a", "o"] = Field(
        ...,
        description="'o' for OS/firmware/ROM/system software, 'a' for software kit/library, 'h' for hardware option/chip"
    )
    versions: List[str] = Field(
        default_factory=lambda: ["-"],
        description="One or more versions for this component (e.g. ['1.101.12'] or ['1.02.013', '2.07.003'])"
    )


class ClauseGroup(BaseModel):
    targets: List[ExtractedUnit] = Field(
        ...,
        description="Primary hardware models or standalone software products in this clause"
    )
    companions: List[CompanionComponent] = Field(
        default_factory=list,
        description="Shared firmware, OS, ROM versions, or optional kits that run on / apply to all targets in this clause"
    )


class TOEExtraction(BaseModel):
    clauses: List[ClauseGroup] = Field(
        ...,
        description="List of independent product-to-version configuration clauses extracted from the title"
    )


# =====================================================================
# 2. Domain Rules: Vendor Aliases & Common Criteria Chip/OEM Prefixes
# =====================================================================

VENDOR_ALIASES: Dict[str, str] = {
    "fuji xerox": "fujixerox",
    "fujixerox": "fujixerox",
    "konica minolta": "konicaminolta",
    "konicaminolta": "konicaminolta",
    "hewlett packard enterprise": "hpe",
    "aruba, a hewlett packard enterprise company": "arubanetworks",
    "aruba networks": "arubanetworks",
    "aruba": "arubanetworks",
    "juniper networks": "juniper",
    "juniper networks, inc.": "juniper",
    "cisco systems": "cisco",
    "red hat": "redhat",
    "suse": "suse",
    "f5 networks": "f5",
    "palo alto networks": "paloaltonetworks",
    "check point": "checkpoint",
    "check point software technologies": "checkpoint",
    "check point software technologies incorporated": "checkpoint",
    "dell emc": "emc",
    "emc": "emc",
    "brocade communication systems": "brocade",
    "brocade communication systems, inc.": "brocade",
    "lg electronics": "lg",
    "lg electronics inc.": "lg",
    "infineon technologies": "infineon",
    "infineon technologies ag": "infineon",
    "stmicroelectronics": "stmicroelectronics",
    "nxp semiconductors": "nxp",
    "computer associates": "ca",
    "symantec": "symantec",
    "pulse secure": "pulsesecure",
    "motorola mobility": "motorola",
    "motorola mobility llc": "motorola",
    "ta triumph-adler": "triumph-adler",
    "triumph-adler": "triumph-adler",
    "rex rotary": "rex_rotary",
    "toshiba": "toshibatec",
    "toshibatec": "toshibatec",
    "oberthur": "oberthur",
    "idemia": "idemia",
}

# Known product-line / OEM brand / CC microcontroller prefix -> canonical CPE vendor
BRAND_AND_CHIP_PREFIX_VENDORS: List[Tuple[re.Pattern, str]] = [
    # Printers & MFPs
    (re.compile(r"^bizhub\b", re.I), "konicaminolta"),
    (re.compile(r"^ineo\+?\b", re.I), "develop"),
    (re.compile(r"^taskalfa\b", re.I), "kyocera"),
    (re.compile(r"^copystar\b|^cs\s+\d{3,4}[a-z]*\b", re.I), "kyocera"),
    (re.compile(r"^workcentre\b|^versalink\b|^altalink\b|^phaser\b", re.I), "xerox"),
    (re.compile(r"^docucentre\b|^apeosport\b|^apeos\b", re.I), "fujixerox"),
    (re.compile(r"^e-studio\b", re.I), "toshibatec"),
    (re.compile(r"^imagerunner\b|^imagepress\b", re.I), "canon"),
    (re.compile(r"^imagio\b|^aficio\b", re.I), "ricoh"),
    (re.compile(r"^laserjet\b|^color_laserjet\b|^pagewide\b|^futuresmart\b|^storageworks\b", re.I), "hp"),
    (re.compile(r"^bp-[a-z]?\d+|^mx-\d+", re.I), "sharp"),
    # Networking & Security
    (re.compile(r"^junos\b|^srx\d+|^qfx\d+|^ex\d+|^mx\d+|^ptx\d+", re.I), "juniper"),
    (re.compile(r"^catalyst\b|^nexus\b|^aironet\b|^asa\b|^asav\b|^anyconnect\b|^ios\b|^nx-os\b", re.I), "cisco"),
    (re.compile(r"^ironport\b|^asyncos\b", re.I), "cisco"),
    (re.compile(r"^fortigate\b|^fortios\b|^fortiproxy\b|^fortimanager\b", re.I), "fortinet"),
    (re.compile(r"^big-ip\b", re.I), "f5"),
    (re.compile(r"^arubaos\b", re.I), "arubanetworks"),
    (re.compile(r"^pulse_connect_secure\b", re.I), "pulsesecure"),
    (re.compile(r"^sidewinder\b", re.I), "mcafee"),
    (re.compile(r"^proxysg\b|^sgos\b", re.I), "bluecoat"),
    (re.compile(r"^sonicos\b", re.I), "sonicwall"),
    (re.compile(r"^vsphere\b|^esxi\b|^vcenter\b", re.I), "vmware"),
    (re.compile(r"^Windows\b", re.I), "microsoft"),
    (re.compile(r"^z/vm\b|^z/os\b|^websphere\b|^tivoli\b", re.I), "ibm"),
    # Smart Cards, Secure Elements, Microcontrollers (Common Criteria heavy)
    (re.compile(r"^s3[cdfknt][0-9a-z]{3,}\b|^sc3\d{3}\b|^exynos\b|^galaxy\b|^knox\b", re.I), "samsung"),
    (re.compile(r"^sle\d{2}[0-9a-z]+|^slb\d{4}[0-9a-z_]*|^slc\d{2}[0-9a-z]+|^m7[789]\d{2}\b|^m50\d{2}\b|^ifx_cci_|^optiga\b", re.I), "infineon"),
    (re.compile(r"^st23[0-9a-z]+|^st31[0-9a-z]+|^st33[0-9a-z]+|^sb23[0-9a-z]+|^sa23[0-9a-z]+|^sc33[0-9a-z]+|^neslib\b", re.I), "stmicroelectronics"),
    (re.compile(r"^j[23][ade][0-9_a-z]+|^p60[0-9a-z]+|^p5cc[0-9a-z]+|^jcop\b|^sn100\b|^mifare\b", re.I), "nxp"),
    (re.compile(r"^at90sc[0-9a-z]+", re.I), "atmel"),
    (re.compile(r"^id-one\b|^etravel\b|^multiapp\b|^ias_classic\b", re.I), "idemia"),
    (re.compile(r"^tcos\b", re.I), "t-systems"),
    (re.compile(r"^sdm\d{3}\b|^spu\d{3}\b|^snapdragon\b", re.I), "qualcomm"),
]


# Version modifier companions that should fold into the parent software/OS version instead of becoming separate CPEs
VERSION_MODIFIER_SLUGS = {
    "service_pack": "sp",
    "sp": "sp",
    "update": "update",
    "patch": "patch",
    "hotfix": "hotfix",
    "feature_pack": "fp",
    "driver_level": "driver_level",
}

# Descriptive phrases occasionally extracted as a companion without a version that are just title noise
NOISE_COMPANION_SLUGS = {
    "series_controller_software",
    "controller_software_for_asia_pacific",
    "series_controller_software_for_asia_pacific",
    "specific_ic_dedicated_software",
    "ic_dedicated_software",
}
GENERIC_COMPONENT_PREFIXES = {
    "system", "panel", "fax", "controller", "control", "data", "security",
    "network", "printer", "scanner", "copy", "web", "firmware", "software",
    "driver", "module", "library", "card", "smart", "secure", "client",
    "server", "appliance", "gateway", "router", "switch", "platform",
    "application", "applet", "os", "rom", "bios", "hdd", "ssd", "usb",
    "pki", "crypto", "cryptographic", "base", "toolbox", "ic", "chip",
    "series", "service", "update", "patch", "release", "virtualization", "kvm",
}

def slugify_cpe(text: str) -> str:
    """Convert a human string into an NVD CPE 2.3 style lowercase slug."""
    if not text:
        return "-"
    s = text.strip().lower()
    # Remove trademark symbols
    s = re.sub(r"[®™©]", "", s)
    # Remove trailing corporate suffixes
    s = re.sub(r"\b(inc\.?|llc\.?|ltd\.?|corp\.?|corporation|incorporated|ag|gmbh)\b", "", s).strip()
    # Replace whitespace and slashes with underscores
    s = re.sub(r"[\s/]+", "_", s)
    # Keep alphanumeric, underscores, hyphens, dots, plus
    s = re.sub(r"[^a-z0-9_\-\.\+]", "", s)
    s = re.sub(r"_+", "_", s).strip("_.")
    return s or "-"


def normalize_version(ver: str) -> str:
    """Clean version strings into CPE 2.3 version tokens."""
    if not ver or ver.strip() in ("-", "*", ""):
        return "-"
    v = ver.strip()
    # Strip leading 'Version:', 'Ver.', 'v', 'V', 'Release'
    v = re.sub(r"^(version|ver\.?|release|rel\.?)\s*:?\s*", "", v, flags=re.I)
    v = re.sub(r"^[vV](?=\d)", "", v)
    v = v.strip()
    v = re.sub(r"\s+", "_", v).lower()
    return v or "-"


class CPEDictionaryResolver:
    """
    Indexes `extracted_cpe_targets.json` (1.69M entries -> 149.6k unique CPE products)
    into a compact cache for fast vendor and canonical product resolution.
    """

    def __init__(
        self,
        raw_cpe_path: str = "data/cpe_index/extracted_cpe_targets.json",
        cache_path: str = "data/cpe_index/cpe_lookup_cache.json"
    ):
        self.raw_cpe_path = raw_cpe_path
        self.cache_path = cache_path

        # product_slug -> list of (vendor, part, count)
        self.product_to_vendors: Dict[str, List[Tuple[str, str, int]]] = {}
        # prefix_token -> list of (vendor, count)
        self.prefix_to_vendors: Dict[str, List[Tuple[str, int]]] = {}
        # set of known official vendor slugs
        self.known_vendors: set = set()

        self._load_or_build()

    def _load_or_build(self):
        if os.path.exists(self.cache_path):
            with open(self.cache_path, "r", encoding="utf-8") as f:
                cache = json.load(f)
            self.product_to_vendors = cache["product_to_vendors"]
            self.prefix_to_vendors = cache["prefix_to_vendors"]
            self.known_vendors = set(cache["known_vendors"])
            return

        print(f"[CPEDictionaryResolver] Building index from {self.raw_cpe_path}...")
        prod_counts: Dict[str, Dict[Tuple[str, str], int]] = defaultdict(lambda: defaultdict(int))
        prefix_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        vendors_set = set()

        with open(self.raw_cpe_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for entry in data:
            idx = entry.rfind(" - cpe:2.3:")
            if idx == -1:
                continue
            cpe = entry[idx + 3:]
            parts = cpe.split(":")
            if len(parts) < 5:
                continue
            part, vendor, product = parts[2], parts[3], parts[4]
            vendors_set.add(vendor)
            prod_counts[product][(vendor, part)] += 1

            # Index the first token and first 2 tokens of product slug if distinctive
            tokens = product.split("_")
            if tokens and len(tokens[0]) >= 3 and not tokens[0].isdigit():
                prefix_counts[tokens[0]][vendor] += 1
            if len(tokens) >= 2:
                two_tok = f"{tokens[0]}_{tokens[1]}"
                prefix_counts[two_tok][vendor] += 1

        # Compact and sort by frequency
        self.product_to_vendors = {
            prod: [[v, p, cnt] for (v, p), cnt in sorted(vp_dict.items(), key=lambda x: -x[1])[:5]]
            for prod, vp_dict in prod_counts.items()
        }
        self.prefix_to_vendors = {
            pref: [[v, cnt] for v, cnt in sorted(v_dict.items(), key=lambda x: -x[1])[:5]]
            for pref, v_dict in prefix_counts.items()
            if len(v_dict) <= 15  # Ignore overly generic prefixes like 'server' or 'client'
        }
        self.known_vendors = vendors_set

        with open(self.cache_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "product_to_vendors": self.product_to_vendors,
                    "prefix_to_vendors": self.prefix_to_vendors,
                    "known_vendors": sorted(list(self.known_vendors)),
                },
                f,
            )
        print(
            f"[CPEDictionaryResolver] Saved cache to {self.cache_path} "
            f"({len(self.product_to_vendors)} products, {len(self.known_vendors)} vendors)."
        )

    def resolve_vendor_and_product(
        self,
        raw_vendor: Optional[str],
        raw_product: str,
        part: str,
        fallback_vendor: Optional[str] = None,
        raw_source_text: Optional[str] = None,
    ) -> Tuple[str, str, str, str]:
        """
        Returns (resolved_vendor_slug, resolved_product_slug, resolved_part, resolution_source).
        Priority:
        1. Brand/Chip regex rules when raw_product starts with an unambiguous OEM/chip prefix (e.g. 'ineo+', 'bizhub', 'S3D384E').
        2. Exact product match in CPE Dictionary (if unambiguous or matches raw_vendor).
        3. Normalized explicit raw_vendor (ONLY if it actually appears in raw_source_text when provided).
        4. Two-token / single-token prefix lookup in CPE Dictionary.
        5. Fallback vendor from the clause's primary target.
        """
        # Normalize trademark symbols into spaces so "CYBEX™SC840" becomes "CYBEX SC840"
        prod_clean = re.sub(r"[®™©]+", " ", raw_product).strip()
        # Separate camel/brand boundary if a known uppercase brand was concatenated with a model code (e.g. "CYBEXSC840" -> "CYBEX SC840")
        prod_clean = re.sub(r"^(CYBEX|TASKalfa|DocuCentre|ApeosPort|WorkCentre|VersaLink|AltaLink|LaserJet|FortiGate)(?=[A-Z0-9])", r"\1 ", prod_clean)
        prod_slug = slugify_cpe(prod_clean)

        # Normalize explicit vendor if provided AND verify it isn't hallucinated if raw_source_text is available
        explicit_v_slug = None
        if raw_vendor and raw_vendor.strip() and raw_vendor.strip().lower() not in ("null", "none", "-", "unknown"):
            rv_clean = re.sub(r"[®™©]", "", raw_vendor.strip())
            rv_lower = rv_clean.lower().strip()
            # Guard against LLM vendor hallucination OR splitting a chip prefix into vendor (e.g. 'ST' + '23YL80B' from 'ST23YL80B')
            is_in_text = True
            if raw_source_text:
                src_lower = raw_source_text.lower()
                first_word = rv_lower.split()[0] if rv_lower.split() else rv_lower
                pattern_whole = r"\b" + re.escape(first_word) + r"\b"
                if not re.search(pattern_whole, src_lower):
                    is_in_text = False
                    # If the LLM split a single chip token like 'ST23YL80B' into vendor='ST' and product='23YL80B',
                    # rejoin them back into prod_clean so the chip prefix rule matches 'ST23YL80B'!
                    rejoined = f"{rv_clean}{prod_clean}"
                    if rejoined.lower() in src_lower:
                        prod_clean = rejoined
                        prod_slug = slugify_cpe(prod_clean)

            if is_in_text:
                if rv_lower in VENDOR_ALIASES:
                    explicit_v_slug = VENDOR_ALIASES[rv_lower]
                else:
                    cand = slugify_cpe(rv_lower)
                    if cand in self.known_vendors:
                        explicit_v_slug = cand
                    else:
                        first_v = cand.split("_")[0]
                        explicit_v_slug = first_v if first_v in self.known_vendors else cand

        # Check domain brand/chip regex rules (handles OEM switches like bizhub vs ineo+ and CC smartcard chips)
        rule_vendor = None
        for pattern, v_target in BRAND_AND_CHIP_PREFIX_VENDORS:
            if pattern.search(prod_clean) or pattern.search(prod_slug):
                rule_vendor = v_target
                break

        # If an unambiguous OEM brand or semiconductor chip rule matched, it takes priority
        if rule_vendor and (
            prod_slug.startswith(("bizhub", "ineo", "taskalfa", "workcentre", "versalink", "altalink", "docucentre", "apeosport"))
            or explicit_v_slug is None
        ):
            explicit_v_slug = rule_vendor

        # Strip duplicated vendor prefix from product slug if present (e.g. product="cisco_catalyst_9300" -> "catalyst_9300")
        effective_v = explicit_v_slug or rule_vendor or fallback_vendor
        if effective_v and prod_slug.startswith(f"{effective_v}_"):
            stripped = prod_slug[len(effective_v) + 1:]
            if stripped:
                prod_slug = stripped

        # 1. Exact product lookup in official CPE dictionary
        #    NEVER allow generic component names ('firmware', 'system', 'toolbox', 'base', 'panel', 'service_pack')
        #    to match random third-party products in the NVD CPE dictionary when no explicit vendor was given.
        is_generic_companion_slug = (
            not explicit_v_slug
            and not rule_vendor
            and (
                prod_slug in GENERIC_COMPONENT_PREFIXES
                or prod_slug.split("_")[0] in GENERIC_COMPONENT_PREFIXES
                or len(prod_slug) <= 3
                or prod_slug in {"toolbox", "base", "scl", "ec", "rsa", "sha-2", "control_software", "system_software"}
            )
        )
        if prod_slug in self.product_to_vendors and not is_generic_companion_slug:
            candidates = self.product_to_vendors[prod_slug]
            # If explicit vendor matches one of the dictionary vendors for this product, use it!
            if explicit_v_slug:
                for v_cand, p_cand, _ in candidates:
                    if v_cand == explicit_v_slug:
                        return v_cand, prod_slug, part, "cpe_exact+explicit"
            # If fallback_vendor matches one of the dictionary vendors for this product, prefer it!
            if not explicit_v_slug and fallback_vendor:
                for v_cand, p_cand, _ in candidates:
                    if v_cand == fallback_vendor:
                        return v_cand, prod_slug, part, "cpe_exact+clause_vendor"
            # If no explicit vendor, take top CPE dictionary vendor for this exact product
            if not explicit_v_slug:
                top_v, top_p, _ = candidates[0]
                return top_v, prod_slug, part, "cpe_exact"

        # 2. If OEM/Chip prefix rule matched and no conflicting explicit vendor
        if rule_vendor and not explicit_v_slug:
            return rule_vendor, prod_slug, part, "domain_rule"

        # 3. If explicit vendor is given, use it
        if explicit_v_slug:
            return explicit_v_slug, prod_slug, part, "explicit_vendor"

        # 4. Prefix token lookup in CPE dictionary (only when tokens are brand-distinctive, not generic component words)
        tokens = prod_slug.split("_")
        if tokens and tokens[0] not in GENERIC_COMPONENT_PREFIXES:
            if len(tokens) >= 2:
                two_tok = f"{tokens[0]}_{tokens[1]}"
                if two_tok in self.prefix_to_vendors:
                    top_v, top_cnt = self.prefix_to_vendors[two_tok][0]
                    if top_cnt >= 3:
                        return top_v, prod_slug, part, f"cpe_prefix({two_tok})"
            if tokens[0] in self.prefix_to_vendors:
                top_v, top_cnt = self.prefix_to_vendors[tokens[0]][0]
                if top_cnt >= 5:
                    return top_v, prod_slug, part, f"cpe_prefix({tokens[0]})"

        # 5. Fallback to clause vendor
        if fallback_vendor:
            return fallback_vendor, prod_slug, part, "clause_inheritance"

        return "unknown", prod_slug, part, "unresolved"

    def build_cpes_from_extraction(
        self,
        extraction: TOEExtraction,
        attach_shared_firmware_to_models: bool = False,
        raw_source_text: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        """
        Converts Qwen 2.5 3B's `TOEExtraction` JSON into normalized CPE 2.3 entries.
        """
        results = []
        seen = set()

        def add_cpe(part: str, vendor: str, product: str, version: str, source: str):
            cpe_str = f"cpe:2.3:{part}:{vendor}:{product}:{version}:*:*:*:*:*:*:*"
            if cpe_str not in seen:
                seen.add(cpe_str)
                results.append(
                    {
                        "cpe": cpe_str,
                        "short": f"{part}:{vendor}:{product}:{version}",
                        "part": part,
                        "vendor": vendor,
                        "product": product,
                        "version": version,
                        "resolution": source,
                    }
                )

        for clause in extraction.clauses:
            resolved_targets = []
            clause_primary_vendor = None

            # Pre-scan companions for version modifiers (e.g., Service Pack 3, Update 2, Hotfix 1)
            modifier_suffixes = []
            active_companions = []
            for comp in clause.companions:
                c_slug = slugify_cpe(comp.product)
                c_vers = [normalize_version(v) for v in (comp.versions or ["-"]) if normalize_version(v) != "-"]
                if c_slug in VERSION_MODIFIER_SLUGS and c_vers:
                    mod_tag = VERSION_MODIFIER_SLUGS[c_slug]
                    for v_item in c_vers:
                        modifier_suffixes.append(f"{mod_tag}{v_item}" if mod_tag == "sp" else f"{mod_tag}_{v_item}")
                elif c_slug in NOISE_COMPANION_SLUGS and not c_vers:
                    # Drop versionless title noise like "Series Controller Software"
                    continue
                else:
                    active_companions.append(comp)

            # Pass 1: Resolve all target units in the clause
            for unit in clause.targets:
                u_prod = unit.product.strip()
                u_ver = unit.version.strip() if unit.version else "-"

                # If unit is software/OS (part 'a' or 'o'), strip embedded trailing version from product name
                # e.g. product="vSphere 5.5 Update 2", version="-" -> product="vSphere", version="5.5 Update 2"
                # or product="Linux Enterprise Server 11 Service Pack 2", version="11 Service Pack 2" -> product="Linux Enterprise Server"
                if unit.part in ("a", "o"):
                    m_ver = re.search(
                        r"\s+(?:v|version\s+|release\s+)?(\d+(?:\.\d+)*(?:\s+(?:with\s+)?(?:update|service\s+pack|sp|patch|r|build)\s*\d+)*)$",
                        u_prod,
                        flags=re.I,
                    )
                    if m_ver:
                        extracted_v = m_ver.group(1).strip()
                        if u_ver in ("-", "", "*"):
                            u_ver = extracted_v
                        u_prod = u_prod[: m_ver.start()].strip()
                    elif u_ver not in ("-", "", "*") and u_prod.lower().endswith(u_ver.lower()):
                        # Direct suffix match (e.g. product="Linux Enterprise Server 11 Service Pack 2", version="11 Service Pack 2")
                        u_prod = u_prod[: -len(u_ver)].strip()

                v_slug, p_slug, part_slug, src = self.resolve_vendor_and_product(
                    unit.vendor,
                    u_prod,
                    unit.part,
                    fallback_vendor=clause_primary_vendor,
                    raw_source_text=raw_source_text,
                )
                if v_slug != "unknown" and clause_primary_vendor is None:
                    clause_primary_vendor = v_slug
                ver_slug = normalize_version(u_ver)

                # Fold any version modifier companions (like "Service Pack 3") into software/OS targets
                if modifier_suffixes and part_slug in ("a", "o"):
                    mod_joined = "_".join(modifier_suffixes)
                    ver_slug = f"{ver_slug}_{mod_joined}" if ver_slug != "-" else mod_joined

                resolved_targets.append((part_slug, v_slug, p_slug, ver_slug, src))
                add_cpe(part_slug, v_slug, p_slug, ver_slug, src)

            # Pass 2: Resolve remaining companion components (shared OS, ROMs, kits, libraries)
            for comp in active_companions:
                c_v_slug, c_p_slug, c_part, c_src = self.resolve_vendor_and_product(
                    comp.vendor,
                    comp.product,
                    comp.part,
                    fallback_vendor=clause_primary_vendor,
                    raw_source_text=raw_source_text,
                )
                versions = comp.versions if comp.versions else ["-"]
                for raw_v in versions:
                    v_norm = normalize_version(raw_v)
                    if attach_shared_firmware_to_models and c_part == "o" and resolved_targets:
                        # Create model-specific firmware CPEs for each hardware unit in the clause
                        for t_part, t_v, t_p, _, _ in resolved_targets:
                            if t_part == "h":
                                fw_prod = f"{t_p}_{c_p_slug}" if c_p_slug != "firmware" else f"{t_p}_firmware"
                                add_cpe("o", t_v, fw_prod, v_norm, f"{c_src}+model_bound")
                    else:
                        add_cpe(c_part, c_v_slug, c_p_slug, v_norm, c_src)

        return results


# =====================================================================
# 4. Self-Test on Hard Compounding Examples from names.json & benchmark
# =====================================================================
if __name__ == "__main__":
    resolver = CPEDictionaryResolver()

    # Test 1: Multi-brand OEM printer + shared control software (names.json #5)
    # "bizhub C754 / bizhub C654 / ineo+ 754 / ineo+ 654 Control Software Version: A2X00Y0-0100-G00-53"
    sample_1 = TOEExtraction(
        clauses=[
            ClauseGroup(
                targets=[
                    ExtractedUnit(vendor=None, product="bizhub C754", part="h", version="-"),
                    ExtractedUnit(vendor=None, product="bizhub C654", part="h", version="-"),
                    ExtractedUnit(vendor=None, product="ineo+ 754", part="h", version="-"),
                    ExtractedUnit(vendor=None, product="ineo+ 654", part="h", version="-"),
                ],
                companions=[
                    CompanionComponent(
                        vendor=None,
                        product="Control Software",
                        part="o",
                        versions=["A2X00Y0-0100-G00-53"],
                    )
                ],
            )
        ]
    )

    # Test 2: Multi-clause hardware + different OS versions (names.json #53)
    # "IronPort Email Security Appliances (ESA), comprising the C160, C370, X1060, and X1070 appliance models,
    #  running IronPort AsyncOS software, version 7.1, and the C670 appliance model running IronPort AsyncOS version 7.3"
    sample_2 = TOEExtraction(
        clauses=[
            ClauseGroup(
                targets=[
                    ExtractedUnit(vendor="IronPort", product="C160", part="h", version="-"),
                    ExtractedUnit(vendor="IronPort", product="C370", part="h", version="-"),
                    ExtractedUnit(vendor="IronPort", product="X1060", part="h", version="-"),
                    ExtractedUnit(vendor="IronPort", product="X1070", part="h", version="-"),
                ],
                companions=[
                    CompanionComponent(vendor="IronPort", product="AsyncOS", part="o", versions=["7.1"])
                ],
            ),
            ClauseGroup(
                targets=[
                    ExtractedUnit(vendor="IronPort", product="C670", part="h", version="-"),
                ],
                companions=[
                    CompanionComponent(vendor="IronPort", product="AsyncOS", part="o", versions=["7.3"])
                ],
            ),
        ]
    )

    # Test 3: Multi-ROM / Subsystem versions + omitted vendor (names.json #41)
    # "TASKalfa 3501i, TASKalfa 4501i, CS 3501i with Data Security Kit (E), FAX System (W)
    #  System:2N9_2000.C02.201 Panel:2N4_7000.C02.010 FAX:3N6_5100.B04.001"
    sample_3 = TOEExtraction(
        clauses=[
            ClauseGroup(
                targets=[
                    ExtractedUnit(vendor=None, product="TASKalfa 3501i", part="h", version="-"),
                    ExtractedUnit(vendor=None, product="TASKalfa 4501i", part="h", version="-"),
                    ExtractedUnit(vendor=None, product="CS 3501i", part="h", version="-"),
                ],
                companions=[
                    CompanionComponent(vendor=None, product="Data Security Kit (E)", part="a", versions=["-"]),
                    CompanionComponent(vendor=None, product="FAX System (W)", part="a", versions=["-"]),
                    CompanionComponent(vendor=None, product="System Firmware", part="o", versions=["2N9_2000.C02.201"]),
                    CompanionComponent(vendor=None, product="Panel Firmware", part="o", versions=["2N4_7000.C02.010"]),
                    CompanionComponent(vendor=None, product="FAX Firmware", part="o", versions=["3N6_5100.B04.001"]),
                ],
            )
        ]
    )

    # Test 4: Smart Card IC with multiple library version alternatives (names.json #101 & reverse_benchmark #41)
    # "XSmart e-Passport V1.3 on S3CT9KW/S3CT9KC/S3CT9K9"
    sample_4 = TOEExtraction(
        clauses=[
            ClauseGroup(
                targets=[
                    ExtractedUnit(vendor=None, product="S3CT9KW", part="h", version="-"),
                    ExtractedUnit(vendor=None, product="S3CT9KC", part="h", version="-"),
                    ExtractedUnit(vendor=None, product="S3CT9K9", part="h", version="-"),
                ],
                companions=[
                    CompanionComponent(vendor=None, product="XSmart e-Passport", part="a", versions=["1.3"])
                ],
            )
        ]
    )

    for idx, (title, sample) in enumerate(
        [
            ("OEM Multi-Brand (bizhub / ineo+)", sample_1),
            ("Multi-Clause Paired Versions (IronPort AsyncOS 7.1 vs 7.3)", sample_2),
            ("Kyocera Multi-Subsystem Firmware + Kits", sample_3),
            ("Smart Card IC Vendor Resolution (S3CT9KW -> Samsung)", sample_4),
        ],
        1,
    ):
        print(f"\n{'='*75}\nTest {idx}: {title}\n{'-'*75}")
        cpes = resolver.build_cpes_from_extraction(sample, attach_shared_firmware_to_models=False)
        for item in cpes:
            print(f"  {item['short']:48s}  [{item['resolution']}]")
