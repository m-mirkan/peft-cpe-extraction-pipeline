# Annotation Codebook — TOE title → Stage-1 JSON

**Version:** v1.0 (2026-11-21) · **Status:** all open decisions D1-D11 settled; rules are still to be validated against the gold review and the retrained model · **Author:** Mohamed

## 0. Purpose and how this document is used

This codebook defines what the *correct* Stage-1 JSON is for a certificate (TOE) title. It is a document for humans. It is never executed.

It is applied in four places:
1. **Training data:** `src/generate_synthetic_dataset.py` must generate examples that follow these rules.
2. **Gold test set:** hand-labeled real titles from `data/benchmarks/` follow these rules.
3. **System prompt:** only the 3–5 sharpest rules are copied into `SYSTEM_PROMPT` (it must be identical at training and inference).
4. **Resolver:** deterministic fixes (aliases, formatting) go into `src/cpe_resolver.py`, not into the model.

**Provenance of this draft.** Observations come from running the baseline adapter on `data/benchmarks/names.json` (100 titles, run on 2026-11-20). Decoding appears to be sampled, so outputs can differ between runs. NVD evidence comes from `data/cpe_index/cpe_lookup_cache.json`; the counts are number of NVD entries (one per version), so they favour products with many versions. Every rule below is a **proposal to verify**, not a fact.

## 1. Output schema (reminder)

```
{"clauses": [ {"targets": [ {vendor, product, part, version} ],
               "companions": [ {vendor, product, part, versions[]} ]} ]}
```
- `part` ∈ {`h`, `o`, `a`}. `vendor` may be `null` if the title does not state it.
- `version` is `"-"` only for base hardware with no version.

## 2. General principles

- **P1. Consistency beats cleverness.** The same kind of thing must get the same label everywhere.
- **P2. NVD is the reference, not the law.** If the product exists in NVD, prefer its dominant `part` and its product naming. If NVD itself is split (e.g. ASA software), pick one convention here and write it down (see Open Decisions).
- **P3. Deterministic things belong in the resolver.** If a fix can be done by a lookup table or string rule, do it in Python, not in training data.
- **P4. Unclear titles.** If a title is genuinely ambiguous, mark it `AMBIGUOUS` in the gold set and exclude it from scoring (see D6).

## 3. Rules

### R1 — `part` definitions
- `h` = physical device or model (router, switch, printer, smartphone, TPM, smart-card IC).
- `o` = operating system, firmware, ROM/boot software that runs the device.
- `a` = application software (including management and security applications).
- **Mobile OS** (Android, Windows Mobile) → `o`. *Evidence: NVD `windows_mobile` = o (14) vs a (1); baseline gave `a` in [13].*

### R2 — Software products follow the NVD part when the product exists
- Cisco PIX Firewall → `o` (NVD: o 75, a 2). *Baseline: `a` in [58].*
- Check Point VPN-1 / FireWall-1 → `a` (NVD: a 9 / a 17). *Baseline: `h` in [60], `a` in [63] → inconsistent.*
- Sidewinder G2 *Software* must get ONE part. *Baseline: `a` in [61], `o` in [62].* **Decided (D2):** when NVD splits between `o` and `a`, use the NVD majority for that product (ASA software → `o`, NX-OS → `o`). If the product is not in NVD (Sidewinder G2 Software), system software of a firewall/network appliance → `o`.
- VMware vSphere → `a` (NVD: vmware a 8, o 1); ESXi → `o` (NVD: o 530). *Baseline: `o` in [1].*
- Email Security Appliance → `a` (NVD: a 104, h 11). Baseline matched ([26]).

### R3 — Firmware / ROM components
- Firmware, Controller ROM, FAX ROM, control software that runs a printer or device → `o`.
- NVD names these `<model>_firmware` (about 40,000 NVD products, almost all `o`). The bare product `firmware` has almost no NVD entries. *Baseline emits `firmware`, `control_software`, `system`, `panel`, `fax` in about 15 titles (e.g. [4], [5], [29], [35], [38]–[41], [85]–[88]).*
- **Decided (D1):** the model outputs a plain component (`Firmware`, `Controller ROM`, `Control Software`, …) with `part: "o"` and its version. The resolver does the naming: it binds each firmware component to the hardware models of its clause as `<model>_firmware` (the resolver's `attach_shared_firmware_to_models` mode, which should become the default). The model must never invent model-bound names itself.

### R4 — Versions
- A version never stays inside `product`. `vSphere 5.5 Update 2` → product `vSphere`, version `5.5 Update 2`. *Baseline: version `-` in [1], [25], [69], [73].*
- Keep update / service-pack / release text in the version string; the resolver normalizes it (`5.5_update_2`).
- Standalone software or OS targets must carry a version when the title has one.
- Editions (`Platinum Edition`) → **D4**.

### R5 — Words that are not part of the product name
- Device-class nouns: *Switches, Routers, Appliances, Platform, Services Gateway, Single Function Printer, Multi-Function Printers*.
  *Baseline: `ms622_single_function_printer` [87], `srx650_services_gateway` [53], `nexus_7000_series_switch` [19].*
- **Exception:** keep `Series` when it is part of an NVD product name (`srx_series` exists in NVD; baseline [25] matched it). → **D3**
- Trademark symbols (®, ™), regional text (`for Asia Pacific`), packaging words (`Diskless model`) are noise.

### R6 — Components vs targets
- OS / firmware bundled with hardware → `companions` of that hardware clause.
- Standalone software or OS (no hardware named) → `targets`.
- Management or security software that is separately named and versioned (WCS, ACS) → its own `a` item, not `h`. *Baseline typed them `h` in [18], and emitted ACS twice (`h` and `o`) in [19].*
- Options / kits (`Data Security Kit`, `FAX System`, `Secure Element (P/N …)`) → **D5**.

### R7 — Clauses and version binding
- Separate `clauses` when different models run different versions.
- A version binds only to the component it is attached to, never to another product in the same title. *Baseline [28]: ASA version `9.4(1.13)` attached to ESXi, and `9.4(1.240)` to ASDM.*
- Do not emit an empty clause. *Baseline [65].*

### R8 — Multi-model expansion
- Slash / comma lists inherit the shared family prefix (`DocuCentre-IV C2265/C2263`). The baseline does this well.
- Bare numbers (`Aruba 600, 3000, 6000, 7000`) and bare letters (`Juniper M, T, MX`) → **D7**; baseline output `600`, `m`, `t` as products, which are almost certainly not usable CPE products.

### R9 — Vendor
- `vendor: null` is allowed when the title does not say it; the resolver fills it from NVD.
- A vendor name must never become a product. *Baseline [32]: `o:hewlett_packard:enterprise`.*

## 4. Fixes that belong in the resolver (not in the labels)

| Observed | Where | Proposed fix |
|---|---|---|
| `junos_os` not in NVD; NVD uses `junos` | [24], [33], [78], [80] | alias table: `junos_os` → `junos` |
| Wrong fuzzy vendor: `scl` → schneider-electric, `cam` → wyze, `VPN Client` → cisco, `next_generation_feature_pack` → forcepoint | [51], [55], [65], [60] | tighten or disable `cpe_prefix` matching unless the title vendor agrees |
| Unknown vendor | [20], [33] | infer vendor from the clause's other items, or flag |
| Backslash artifacts (`eTrust\ Admin`, `NetBackup\ 8.2`) | [65], [73] | strip `\` in post-processing |

## 5. Decisions (all settled in v1.0; decisions D3-D11 were delegated to Claude on 2026-11-21 and may be revisited after the gold review)

- ~~**D1.**~~ **DECIDED (2026-11-21):** the resolver does firmware naming (`<model>_firmware`); the model outputs a plain component. See R3.
- ~~**D2.**~~ **DECIDED (2026-11-21):** NVD majority when NVD is split; `o` for unlisted firewall/network system software. See R2.
- **D3. DECIDED:** drop `Series` / `Services Gateway` / device-class nouns from the product. Keep `Series` only if the exact NVD product name contains it (check with the lookup cache before keeping).
- **D4. DECIDED:** drop editions (`Enterprise Edition`, `Platinum Edition`), architecture, language and `LTS`. The version holds only the number (and update / release text per R4). Reason: NVD stores editions in a separate CPE field, not in product or version.
- **D5. DECIDED:** options and kits that are separately named hardware or software (`FAX Unit`, `HDD Option`, `eMMC`, `SPC-4-15-320`) are kept as `companions` with their own part; part numbers (`P/N 57X0185`), certificate ids (`ANSSI-CC-...`), application ids and build numbers are noise and dropped. Weakest decision: NVD rarely has these, so check how many resolve before you confirm.
- **D6. DECIDED:** titles that are genuinely ambiguous (vendor only, placeholder like `xyz`, family name only) get `status: "ambiguous"` in the gold set and are excluded from scoring. The model is not required to handle them.
- **D7. DECIDED:** bare model numbers / letters inherit the family prefix written in the title (`A-Series 12500`, `ProxySG SG510`); the vendor is kept when the title states it. If no family prefix exists, keep the bare number.
- **D8. DECIDED:** smart-card / ePassport applets and card OSes (`IDeal Citiz`, `ID-One CNS`, `XSmart e-Passport`, `JCOP`): `a` or `o`? Gold drafts use `a` for applications and `o` for JCOP / card OS platforms. Decision: applets and applications are `a`; card OS platforms (JCOP, ID-One Cosmo) are `o`.
- **D9. DECIDED:** `JCOP 4 P71`: product `JCOP` with version `4 P71`, or product `JCOP 4`? Drafts use product `JCOP`, version = everything after.
- **D10. DECIDED:** hardware revision / stepping (`A02`, `rev. E`, `Revision 3`, `T23`) goes in the hardware `version` (drafts), not in the product name.
- **D11. DECIDED:** chip names keep their manufacturer prefix in the product (`ST23YL80B`, never `23YL80B`). The vendor field stays `null` unless the title states the vendor; the resolver infers it from NVD.

## 6. Worked examples (to verify before they become training data)

| # | Title (short) | Baseline | Proposed |
|---|---|---|---|
| 1 | VMware vSphere 5.5 Update 2 | `o`, version `-` | `a`, product `vSphere`, version `5.5 Update 2` |
| 13 | Windows Mobile 6 | `a` | `o` |
| 25 | Junos 12.1 X46 D20 for SRX Series… | product `Junos 12.1 X46 D20`, version `-` | product `Junos`, version `12.1 X46 D20` |
| 28 | ASA 9.4(1.13) … ESXi 5.1 | ESXi gets ASA version | ESXi is a separate component with its own version |
| 58 | Cisco Secure PIX Firewall V6.2(2) | `a` | `o` (check product name against NVD `pix_firewall`) |
| 60 | Check Point VPN-1/FireWall-1 NG FP1 | `h` | `a` |
| 69 | Citrix XenApp 7.6 Platinum Edition | version `-` | product `XenApp`, version `7.6` (edition per D4) |
| 87 | Lexmark MS622 Single Function Printer… | product `ms622_single_function_printer` | product `MS622` |

## 7. Changelog

- v0 (2026-11-20): first draft from 100-title baseline run + NVD cache lookups. No rule validated yet.
- v0.1 (2026-11-21): decided D1 (resolver names firmware) and D2 (NVD majority, `o` fallback). Rules R2 and R3 updated. Open decisions left: D3 to D7.
- v0.2 (2026-11-21): added proposed defaults for D3-D7 (so the gold drafts and the codebook agree) and new open decisions D8-D10. Gold draft G013 aligned to R5 (device-class words stripped).
- v0.2b (2026-11-21): the 4 ambiguous gold titles (G031, G039, G047, G048) were replaced by clearer titles from the pool, so all 100 gold titles are scoreable. D6 still applies to future ambiguous titles.
- v1.0 (2026-11-21): all decisions D3-D10 confirmed as written; new D11 (ST prefix kept in chip names). The gold drafts already follow these rules.
