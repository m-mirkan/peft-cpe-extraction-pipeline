# Gold set: DRAFT expected answers (review before use)

Format per title: `part vendor | product | version(s)`. `T` = target, `C` = companion. Confidence and notes show what I was unsure about.

## G001 [medium, other_hardware, confidence: low, status: labeled]
> Digital Tachograph - Vehicle Unit SE5000-8 Version E

- T `h` (no vendor) | Digital Tachograph Vehicle Unit SE5000-8 | E
- note: part ambiguous (hardware vs software); vendor not stated

## G002 [easy, epassport_applet, confidence: low, status: labeled]
> Xaica-Alpha PLUS ePassport Active Authentication

- T `a` (no vendor) | Xaica-Alpha PLUS ePassport | -
- note: eMRTD OS/applet: a vs o undecided; 'Active Authentication' treated as a feature, dropped

## G003 [easy, enterprise_sw, confidence: medium, status: labeled]
> DBsign for Client/Server Applications Version 3.0

- T `a` (no vendor) | DBsign for Client/Server Applications | 3.0
- note: vendor (DBsign Inc.) not in the title; product name contains a slash

## G004 [medium, other_hardware, confidence: medium, status: labeled]
> Wasion aMeter100 and aMeter300 Smart Energy Meters

- T `h` Wasion | aMeter100 | -
- T `h` Wasion | aMeter300 | -
- note: 'Smart Energy Meters' dropped as device-class words

## G005 [easy, smartcard_chip, confidence: medium, status: labeled]
> Philips Smart Card Controller P16WX064V0C

- T `h` Philips | P16WX064V0C | -
- note: Smart Card Controller dropped as device class

## G006 [medium, epassport_applet, confidence: low, status: labeled]
> KONA2 D2320N ePassport [EAC configuration] version 01 revision 03 patch 00

- T `a` (no vendor) | KONA2 D2320N ePassport | 01 revision 03 patch 00
- note: [EAC configuration] dropped; version text kept per R4; applet a per D8

## G007 [hard, epassport_applet, confidence: low, status: labeled]
> Passeport MorphoePass EAC CC with BAC, AA and EAC RSA or EAC ECC, on STMicroelectronics ST19NR66-A/1.1.0

- T `a` (no vendor) | MorphoePass | -
- C `h` STMicroelectronics | ST19NR66-A | 1.1.0
- note: French; Passeport / EAC / BAC / AA / RSA / ECC are features, dropped; split of ST19NR66-A/1.1.0 is a guess

## G008 [medium, network_security, confidence: medium, status: labeled]
> Fortinet FortiGate™-1240B Unified Threat Management Solutions and FortiOS 4.0 CC Compliant Firmware

- T `h` Fortinet | FortiGate-1240B | -
- C `o` Fortinet | FortiOS | 4.0
- note: 'Unified Threat Management Solutions' and 'CC Compliant Firmware' dropped

## G009 [medium, network_security, confidence: medium, status: labeled]
> Klas Fastnet Series Switches KlasOS 5.3

- T `h` Klas | Fastnet | -
- C `o` (no vendor) | KlasOS | 5.3
- note: Series Switches dropped per D3

## G010 [medium, enterprise_sw, confidence: medium, status: labeled]
> KnoWho Authentication Server v1.2.2 and Private ID v2.1.15

- T `a` KnoWho | Authentication Server | 1.2.2
- T `a` KnoWho | Private ID | 2.1.15
- note: vendor/product split of 'KnoWho Authentication Server' is a naming choice

## G011 [medium, smartcard_chip, confidence: low, status: labeled]
> MN67S150 Smart Card IC Version RV08 including IC Dedicated Software

- T `h` (no vendor) | MN67S150 | RV08
- C `o` (no vendor) | IC Dedicated Software | -
- note: RV08 read as a hardware revision (D10); vendor (Panasonic) not stated

## G012 [hard, epassport_applet, confidence: low, status: labeled]
> Idemia CombICAO Applet in PACE and CA configuration on ID-ONE Cosmo V9 Essential

- T `a` Idemia | CombICAO Applet | -
- C `o` (no vendor) | ID-One Cosmo | V9
- note: configuration (PACE and CA) dropped; Essential is an edition (D4), dropped

## G013 [hard, network_security, confidence: medium, status: labeled]
> Sidewinder G2 Security Appliance Models 210, 310, 315, 410, 415, 510, 515, 1100, 1150, 2150, 4150 and Sidewinder G2 Software v6.1

- T `h` (no vendor) | Sidewinder G2 210 | -
- T `h` (no vendor) | Sidewinder G2 310 | -
- T `h` (no vendor) | Sidewinder G2 315 | -
- T `h` (no vendor) | Sidewinder G2 410 | -
- T `h` (no vendor) | Sidewinder G2 415 | -
- T `h` (no vendor) | Sidewinder G2 510 | -
- T `h` (no vendor) | Sidewinder G2 515 | -
- T `h` (no vendor) | Sidewinder G2 1100 | -
- T `h` (no vendor) | Sidewinder G2 1150 | -
- T `h` (no vendor) | Sidewinder G2 2150 | -
- T `h` (no vendor) | Sidewinder G2 4150 | -
- C `o` (no vendor) | Sidewinder G2 Software | 6.1
- note: device-class words (Security Appliance) stripped per R5; software part follows D2 (o when not in NVD)

## G014 [easy, smartcard_chip, confidence: medium, status: labeled]
> ATMEL AT90SC9608R rev. E microcontroller

- T `h` Atmel | AT90SC9608R | E
- note: 'rev. E' read as hardware revision

## G015 [hard, printer_mfp, confidence: low, status: labeled]
> TOSHIBAe-STUDIO2525AC/3025AC/3525ACall of the above with FAX Unit and FIPS Hard Disk KitSYS V2.1

- T `h` TOSHIBA | e-STUDIO2525AC | -
- T `h` TOSHIBA | e-STUDIO3025AC | -
- T `h` TOSHIBA | e-STUDIO3525AC | -
- C `h` (no vendor) | FAX Unit | -
- C `h` (no vendor) | FIPS Hard Disk Kit | -
- C `o` (no vendor) | SYS | 2.1
- note: options/kits depend on D5; glued text 'ACall of the above'

## G016 [medium, printer_mfp, confidence: low, status: labeled]
> Canon imagePRESS C910/C810/C710/C660 2600 model1.0

- T `h` Canon | imagePRESS C910 | -
- T `h` Canon | imagePRESS C810 | -
- T `h` Canon | imagePRESS C710 | -
- T `h` Canon | imagePRESS C660 | -
- C `o` (no vendor) | Firmware | 2600
- note: '2600 model1.0' read as firmware 2600 (same convention as the earlier Canon title)

## G017 [easy, enterprise_sw, confidence: high, status: labeled]
> Voltage SecureMail Suite 2.0

- T `a` Voltage | SecureMail Suite | 2.0

## G018 [easy, enterprise_sw, confidence: high, status: labeled]
> McAfee Vulnerability Manager 7.0

- T `a` McAfee | Vulnerability Manager | 7.0

## G019 [medium, smartcard_chip, confidence: low, status: labeled]
> NXP J3A080 and J2A080 Secure Smart Card Controller Revision 3

- T `h` NXP | J3A080 | 3
- T `h` NXP | J2A080 | 3
- note: 'Revision 3' read as hardware revision

## G020 [hard, enterprise_sw, confidence: low, status: labeled]
> Oracle Database 11g Enterprise Edition with Oracle Database Vault Release 11.1.0.7 with Critical Patch Updates up to and including July 2009

- T `a` Oracle | Database | 11.1.0.7
- C `a` Oracle | Database Vault | 11.1.0.7
- note: edition (D4) dropped; critical patch update text dropped as noise

## G021 [hard, smartcard_chip, confidence: medium, status: labeled]
> Microcontrôleurs sécurisés SC23Z018, SC23ZD12, SC23ZD08, SC23ZD04, SB23ZD18, SB23ZD12, SB23ZD08 et SB23ZD04 incluant optionnellement la librairie cryptographique NesLib révision 3.1

- T `h` (no vendor) | SC23Z018 | -
- T `h` (no vendor) | SC23ZD12 | -
- T `h` (no vendor) | SC23ZD08 | -
- T `h` (no vendor) | SC23ZD04 | -
- T `h` (no vendor) | SB23ZD18 | -
- T `h` (no vendor) | SB23ZD12 | -
- T `h` (no vendor) | SB23ZD08 | -
- T `h` (no vendor) | SB23ZD04 | -
- C `a` (no vendor) | NesLib | 3.1
- note: French; vendor (ST) not stated; 'révision 3.1' is the NesLib version

## G022 [medium, printer_mfp, confidence: medium, status: labeled]
> Samsung SCX-8030 SCX-8040 SCX-8038 SCX-8048 CLX-9250 CLX-9350 CLX-9258 CLX-9358 MultiFunctionPrinter

- T `h` Samsung | SCX-8030 | -
- T `h` Samsung | SCX-8040 | -
- T `h` Samsung | SCX-8038 | -
- T `h` Samsung | SCX-8048 | -
- T `h` Samsung | CLX-9250 | -
- T `h` Samsung | CLX-9350 | -
- T `h` Samsung | CLX-9258 | -
- T `h` Samsung | CLX-9358 | -
- note: MultiFunctionPrinter dropped as device class; no version

## G023 [medium, printer_mfp, confidence: medium, status: labeled]
> Xerox D136 Copier/Printer Controller+PS ROM Ver. 1.200.15

- T `h` Xerox | D136 | -
- C `o` (no vendor) | Controller+PS ROM | 1.200.15
- note: Copier/Printer dropped as device class

## G024 [medium, network_security, confidence: medium, status: labeled]
> Nokia 7705 SAR Series with SAR OS 21.10R5

- T `h` Nokia | 7705 SAR | -
- C `o` (no vendor) | SAR OS | 21.10R5
- note: Series dropped per D3

## G025 [medium, mobile_embedded, confidence: low, status: ambiguous]
> Motorola Mobility LLC Mobile Devices on Android 14

- T `h` Motorola Mobility LLC | Mobile Devices | -
- C `o` (no vendor) | Android | 14
- note: 'Mobile Devices' is a generic device-class noun (R5), not a model: ambiguous per D6, excluded from scoring

## G026 [medium, network_security, confidence: low, status: labeled]
> Sidewinder® G2 Firewall, V6.0

- T `o` (no vendor) | Sidewinder G2 Firewall | 6.0
- note: part a/o/h depends on how D2 is applied; consider marking ambiguous

## G027 [hard, printer_mfp, confidence: low, status: labeled]
> MX-M6050 / M5050 / M4050 / M3550 / M3050 / M2630 HDD standard model with MX-FR56U and MX-FX15; and MX-M6050 / M5050 / M4050 / M3550 / M3050 / M2630 HDD option model with MX-FR56U, MX-HD16 and MX-FX150220zc00

- T `h` (no vendor) | MX-M6050 | -
- T `h` (no vendor) | MX-M5050 | -
- T `h` (no vendor) | MX-M4050 | -
- T `h` (no vendor) | MX-M3550 | -
- T `h` (no vendor) | MX-M3050 | -
- T `h` (no vendor) | MX-M2630 | -
- C `h` (no vendor) | MX-FR56U | -
- C `h` (no vendor) | MX-FX15 | -
- T `h` (no vendor) | MX-M6050 | -
- T `h` (no vendor) | MX-M5050 | -
- T `h` (no vendor) | MX-M4050 | -
- T `h` (no vendor) | MX-M3550 | -
- T `h` (no vendor) | MX-M3050 | -
- T `h` (no vendor) | MX-M2630 | -
- C `h` (no vendor) | MX-FR56U | -
- C `h` (no vendor) | MX-HD16 | -
- C `h` (no vendor) | MX-FX15 | 0220zc00
- note: standard vs option model are two clauses; glued MX-FX150220zc00 read as MX-FX15 + 0220zc00 (guess); vendor (Sharp) not stated

## G028 [hard, other_hardware, confidence: low, status: labeled]
> SSD Drives, Firmware Versions: SCPU13.0/ECPU13.0/SCQU15.0/ECQU15.0

- T `h` (no vendor) | SSD Drives | -
- C `o` (no vendor) | Firmware | SCPU13.0, ECPU13.0, SCQU15.0, ECQU15.0
- note: no vendor, generic product

## G029 [easy, epassport_applet, confidence: low, status: labeled]
> SOMA-ck022 Travel Document, Version 1.0

- T `a` (no vendor) | SOMA-ck022 Travel Document | 1.0
- note: eMRTD application: a vs o undecided

## G030 [medium, os_platform, confidence: medium, status: labeled]
> z/VM Version 6 Release 3

- T `o` (no vendor) | z/VM | 6 Release 3
- note: release text kept in version (rule R4); a model may write 6.3; vendor IBM not in the title (R9), so null

## G031 [medium, network_security, confidence: low, status: labeled]
> ZXR10 3900 Series Switches Running the ZXROS Operating System

- T `h` (no vendor) | ZXR10 3900 | -
- C `o` (no vendor) | ZXROS | -
- note: vendor (ZTE) not stated; no version; Switches/Series dropped per R5

## G032 [medium, smartcard_chip, confidence: medium, status: labeled]
> Secure Microcontrollers ST23ZR08A/ST23ZR04A/ST23ZR02A, ST23ZC08A/ST23ZC04A/ST23ZC02A

- T `h` (no vendor) | ST23ZR08A | -
- T `h` (no vendor) | ST23ZR04A | -
- T `h` (no vendor) | ST23ZR02A | -
- T `h` (no vendor) | ST23ZC08A | -
- T `h` (no vendor) | ST23ZC04A | -
- T `h` (no vendor) | ST23ZC02A | -
- note: vendor (ST) not stated

## G033 [medium, printer_mfp, confidence: medium, status: labeled]
> bizhub C252 / ineo+ 251 Control Software

- T `h` (no vendor) | bizhub C252 | -
- T `h` (no vendor) | ineo+ 251 | -
- C `o` (no vendor) | Control Software | -
- note: vendors (Konica Minolta / Develop) not stated

## G034 [medium, os_platform, confidence: low, status: labeled]
> IBM RACF for z/OS Version 2 Release 4

- T `a` IBM | RACF for z/OS | 2 Release 4
- note: RACF is a z/OS component; modelling as one product is a choice

## G035 [medium, printer_mfp, confidence: low, status: labeled]
> Xerox® VersaLink™ C625 and B625 with eMMC

- T `h` Xerox | VersaLink C625 | -
- T `h` Xerox | VersaLink B625 | -
- C `h` (no vendor) | eMMC | -
- note: option component (D5)

## G036 [hard, epassport_applet, confidence: low, status: labeled]
> Carte VITALE 2 - Application VITALE : Composant SB23ZL48 masqué par le logiciel SESAM VITALE v1.0.1 avec correctif version 1

- T `a` (no vendor) | Carte VITALE 2 Application VITALE | -
- C `h` (no vendor) | SB23ZL48 | -
- C `a` (no vendor) | SESAM VITALE | 1.0.1
- note: French; 'correctif version 1' (patch) dropped

## G037 [hard, epassport_applet, confidence: low, status: labeled]
> IAS ECC v2, version 1.3, in configuration #1 on ID-One Cosmo v8.2 open platform on NXP P6022M VB (Identification de l’application : F0 02 02 13) (ANSSI-CC-2020/50-R01)

- T `a` (no vendor) | IAS ECC v2 | 1.3
- C `o` (no vendor) | ID-One Cosmo | 8.2
- C `h` NXP | P6022M VB | -
- note: configuration #1, application id and certificate id dropped as noise

## G038 [easy, epassport_applet, confidence: low, status: labeled]
> NXP JCOP 4.5 P71

- T `o` NXP | JCOP | 4.5 P71
- note: JCOP naming (product vs version) undecided

## G039 [hard, smartcard_chip, confidence: medium, status: labeled]
> SA23YR18A and SB23YR18A Secure Microcontrollers, including the cryptographic library Neslib v3.1, in SA or SB configuration

- T `h` (no vendor) | SA23YR18A | -
- T `h` (no vendor) | SB23YR18A | -
- C `a` (no vendor) | Neslib | 3.1
- note: vendor (ST) not stated; 'in SA or SB configuration' dropped as noise

## G040 [medium, network_security, confidence: low, status: labeled]
> Cisco Adaptive Security Appliances and ASA Virtual Version 9.6

- T `h` Cisco | Adaptive Security Appliances | -
- T `a` Cisco | ASA Virtual | -
- C `o` Cisco | Adaptive Security Appliance Software | 9.6
- note: ASA software = o per D2 (NVD name: adaptive_security_appliance_software, o 1024 vs a 680); ASA Virtual is a virtual (software) appliance: a, as NVD adaptive_security_virtual_appliance (a 5 vs h 1); the hardware family stays h

## G041 [easy, smartcard_chip, confidence: medium, status: labeled]
> Renesas HD65256D smartcard integrated circuit V01

- T `h` Renesas | HD65256D | V01

## G042 [medium, os_platform, confidence: medium, status: labeled]
> Ubuntu LTS 16.04.4 with KVM and QEMU 2.5

- T `o` (no vendor) | Ubuntu | 16.04.4
- C `a` (no vendor) | KVM | -
- C `a` (no vendor) | QEMU | 2.5
- note: 'LTS' dropped from the version

## G043 [medium, enterprise_sw, confidence: medium, status: labeled]
> McAfee Endpoint Security 10.1.0 with ePolicy Orchestrator 5.3.1

- T `a` McAfee | Endpoint Security | 10.1.0
- C `a` McAfee | ePolicy Orchestrator | 5.3.1

## G044 [hard, smartcard_chip, confidence: low, status: labeled]
> IFX_CCI_000Dh, IFX_CCI_0020h, IFX_CCI_0031h, IFX_CCI_0032h, IFX_CCI_0034h design step T23 with optional HSL v2.62.7626, optional SCL v2.04.003, UMSLC lib v01.00.0234 with specific IC-dedicated firmware identifier 80.301.05.1 and user guidance

- T `h` (no vendor) | IFX_CCI_000Dh | T23
- T `h` (no vendor) | IFX_CCI_0020h | T23
- T `h` (no vendor) | IFX_CCI_0031h | T23
- T `h` (no vendor) | IFX_CCI_0032h | T23
- T `h` (no vendor) | IFX_CCI_0034h | T23
- C `a` (no vendor) | HSL | 2.62.7626
- C `a` (no vendor) | SCL | 2.04.003
- C `a` (no vendor) | UMSLC | 01.00.0234
- C `o` (no vendor) | Firmware | 80.301.05.1
- note: design step read as hardware version; user guidance dropped

## G045 [medium, smartcard_chip, confidence: low, status: labeled]
> STMicroelectronics NesLib 6.7.4 on ST33K1M5A and ST33K1M5M B03

- T `a` STMicroelectronics | NesLib | 6.7.4
- C `h` (no vendor) | ST33K1M5A | B03
- C `h` (no vendor) | ST33K1M5M | B03
- note: B03 attached to both chips

## G046 [hard, network_security, confidence: low, status: labeled]
> Cisco Wide Area Application Services Version 4.0, Wide Area Application Engine (WAE) 512, 612, 674, 7341, 7371 and WAE Network Module [NME-WAE] NME-WAE-502 and NME-WAE-522

- T `h` Cisco | Wide Area Application Engine 512 | -
- T `h` Cisco | Wide Area Application Engine 612 | -
- T `h` Cisco | Wide Area Application Engine 674 | -
- T `h` Cisco | Wide Area Application Engine 7341 | -
- T `h` Cisco | Wide Area Application Engine 7371 | -
- T `h` Cisco | NME-WAE-502 | -
- T `h` Cisco | NME-WAE-522 | -
- C `a` Cisco | Wide Area Application Services | 4.0
- note: bare numbers inherit WAE family name (D7); WAAS software kept as companion a

## G047 [hard, enterprise_sw, confidence: low, status: labeled]
> Connect:Direct® with Secure+ Option v3.7 running on UNIX and v4.2 on Windows

- T `a` (no vendor) | Connect:Direct | 3.7
- C `a` (no vendor) | Secure+ Option | -
- T `a` (no vendor) | Connect:Direct | 4.2
- C `a` (no vendor) | Secure+ Option | -
- note: two clauses with different versions; UNIX/Windows platforms dropped; vendor (IBM/Sterling) not stated

## G048 [hard, network_security, confidence: medium, status: labeled]
> CISCO IOS/IPSec release 12.4(6)T3, 12.4(7) & 12.2(33)SRA

- T `o` Cisco | IOS | 12.4(6)T3
- T `o` Cisco | IOS | 12.4(7)
- T `o` Cisco | IOS | 12.2(33)SRA
- note: IPSec is a feature of IOS, not a product; three releases of the same product

## G049 [medium, printer_mfp, confidence: high, status: labeled]
> Xerox WorkCentre 5030/5050 Multifunction Systems, System Software Version 5.003.07.000

- T `h` Xerox | WorkCentre 5030 | -
- T `h` Xerox | WorkCentre 5050 | -
- C `o` (no vendor) | System Software | 5.003.07.000

## G050 [hard, other_hardware, confidence: medium, status: labeled]
> Trusted Platform Modules ST33KTPM2XSPI & ST33KTPM2X (TPM Firmware 9.257) ( ANSSI-CC-2024/04)

- T `h` (no vendor) | ST33KTPM2XSPI | -
- T `h` (no vendor) | ST33KTPM2X | -
- C `o` (no vendor) | TPM Firmware | 9.257
- note: certificate id dropped

## G051 [medium, epassport_applet, confidence: low, status: labeled]
> MIFARE DESFire EV3 on ST31R480 A01(version 1.0.3) (ANSSI-CC-2025/31)

- T `a` (no vendor) | MIFARE DESFire EV3 | 1.0.3
- C `h` (no vendor) | ST31R480 | A01
- note: certificate id dropped

## G052 [medium, epassport_applet, confidence: low, status: labeled]
> NXP JCOP 5.2 on SN100.C58 Secure Element

- T `o` NXP | JCOP | 5.2
- C `h` (no vendor) | SN100.C58 | -
- note: JCOP naming undecided

## G053 [hard, enterprise_sw, confidence: low, status: labeled]
> EMC® Ionix™ for IT Operations Intelligence (SMARTS®) - SAM 8.1.1, IP 8.1.1, NPM 3.1, SIA 2.3.1.1, EISM 3.0, SAM Adapters 1.3

- T `a` EMC | SAM | 8.1.1
- T `a` EMC | IP | 8.1.1
- T `a` EMC | NPM | 3.1
- T `a` EMC | SIA | 2.3.1.1
- T `a` EMC | EISM | 3.0
- T `a` EMC | SAM Adapters | 1.3
- note: acronym product names; 'Ionix' prefix handling undecided

## G054 [hard, printer_mfp, confidence: medium, status: labeled]
> FUJIFILM Apeos C8180 / C7580 / C6580 models with Copy, Print, Fax, Scan and Overwrite StorageController ROM Ver. 1.0.20, Fax ROM Ver. 2.2.1

- T `h` FUJIFILM | Apeos C8180 | -
- T `h` FUJIFILM | Apeos C7580 | -
- T `h` FUJIFILM | Apeos C6580 | -
- C `o` (no vendor) | Storage Controller ROM | 1.0.20
- C `o` (no vendor) | Fax ROM | 2.2.1
- note: glued 'StorageController' split into 'Storage Controller ROM' (reviewer fix)

## G055 [easy, enterprise_sw, confidence: medium, status: labeled]
> Trellix Security Enterprise Security Manager v11.6.12

- T `a` Trellix | Enterprise Security Manager | 11.6.12
- note: 'Security' before 'Enterprise Security Manager' read as part of the vendor line

## G056 [easy, network_security, confidence: medium, status: labeled]
> Thinklogical TLX48 Matrix Switch

- T `h` Thinklogical | TLX48 | -
- note: 'Matrix Switch' dropped as device class

## G057 [medium, epassport_applet, confidence: low, status: labeled]
> KONA102J1 ePassport EAC, versión 1.1

- T `a` (no vendor) | KONA102J1 ePassport | 1.1
- note: Spanish (versión); EAC is a configuration, dropped

## G058 [hard, other_hardware, confidence: low, status: labeled]
> DERMALOG Fingerprint PAD Kit ZF1/F1 bestehend aus ZF1, Part-No. 9014-0005-02; F1, Part-No. 9024-0002-01; DermalogBPZF1Plugin, V 1.2.5.1817; DermalogFakeFingerDetectionZF1Plugin, V 1.3.1.1817; DermalogAuditLogger, V 1.0.1.1803

- T `h` DERMALOG | ZF1 | -
- T `h` DERMALOG | F1 | -
- C `a` DERMALOG | DermalogBPZF1Plugin | 1.2.5.1817
- C `a` DERMALOG | DermalogFakeFingerDetectionZF1Plugin | 1.3.1.1817
- C `a` DERMALOG | DermalogAuditLogger | 1.0.1.1803
- note: German; part numbers dropped

## G059 [medium, os_platform, confidence: medium, status: labeled]
> Microsoft Windows 10 (Creators Update)

- T `o` Microsoft | Windows 10 | Creators Update

## G060 [easy, enterprise_sw, confidence: high, status: labeled]
> EMC® ViPR® Controller v2.1.0.3

- T `a` EMC | ViPR Controller | 2.1.0.3

## G061 [medium, network_security, confidence: high, status: labeled]
> Cisco Catalyst 2960CX and 3560CX Series Compact Switches running IOS 15.2(3)E1

- T `h` Cisco | Catalyst 2960CX | -
- T `h` Cisco | Catalyst 3560CX | -
- C `o` Cisco | IOS | 15.2(3)E1

## G062 [easy, enterprise_sw, confidence: medium, status: labeled]
> Forescout v8.1

- T `a` (no vendor) | Forescout | 8.1
- note: vendor and product share the same name

## G063 [easy, mobile_embedded, confidence: high, status: labeled]
> Samsung Smart TV Security Solution V1.0

- T `a` Samsung | Smart TV Security Solution | 1.0

## G064 [easy, enterprise_sw, confidence: high, status: labeled]
> SolarWinds® Log and Event Manager v5.70

- T `a` SolarWinds | Log and Event Manager | 5.70

## G065 [easy, network_security, confidence: medium, status: labeled]
> Cisco 5915 Embedded Services Router

- T `h` Cisco | 5915 Embedded Services Router | -
- note: product kept as written; reorder to 'Embedded Services Router 5915' is possible

## G066 [medium, smartcard_chip, confidence: medium, status: labeled]
> Cortex M35P r1p1

- T `h` (no vendor) | Cortex M35P | r1p1
- note: vendor (Arm) not stated

## G067 [medium, smartcard_chip, confidence: low, status: labeled]
> ST33J2M0 including optional cryptographic library NESLIB (F02) (ANSSI-CC-2024/06-R01)

- T `h` (no vendor) | ST33J2M0 | F02
- C `a` (no vendor) | NESLIB | -
- note: (F02) read as chip revision; certificate id dropped

## G068 [medium, smartcard_chip, confidence: low, status: labeled]
> Shenzhen Goodix GEOP01 on GSEA01 Security Chip version 1.0

- T `o` Shenzhen Goodix | GEOP01 | 1.0
- C `h` (no vendor) | GSEA01 | -
- note: GEOP01 type (os vs applet) unclear

## G069 [medium, printer_mfp, confidence: medium, status: labeled]
> Samsung Multifunction MultiXpress X4220, X4250, X4300, X401, K4250, K4300, K4350, K401 Series

- T `h` Samsung | MultiXpress X4220 | -
- T `h` Samsung | MultiXpress X4250 | -
- T `h` Samsung | MultiXpress X4300 | -
- T `h` Samsung | MultiXpress X401 | -
- T `h` Samsung | MultiXpress K4250 | -
- T `h` Samsung | MultiXpress K4300 | -
- T `h` Samsung | MultiXpress K4350 | -
- T `h` Samsung | MultiXpress K401 | -
- note: 'Multifunction' and 'Series' dropped; prefix inherited

## G070 [easy, enterprise_sw, confidence: high, status: labeled]
> Oracle Weblogic Server 12.1.3

- T `a` Oracle | WebLogic Server | 12.1.3

## G071 [hard, smartcard_chip, confidence: medium, status: labeled]
> Infineon Smart Card IC (Security Controller) SLE66CX162PE / m1531-a25 and SLE66CX80PE / m1533-a25 all with optional libraries RSA V1.6, EC, V1.1, SHA-2 V1.0 and both with specific IC dedicated software

- T `h` Infineon | SLE66CX162PE | m1531-a25
- T `h` Infineon | SLE66CX80PE | m1533-a25
- C `a` (no vendor) | RSA | 1.6
- C `a` (no vendor) | EC | 1.1
- C `a` (no vendor) | SHA-2 | 1.0
- C `o` (no vendor) | IC Dedicated Software | -
- note: m15xx-a25 read as a mask/hardware version

## G072 [hard, mobile_embedded, confidence: low, status: labeled]
> Strong Customer Authentication for Apple Pay on Vision Pro with M2 running visionOS 2.4(visionOS 2.4 (build 22O238)) (ANSSI-CC-2026/05)

- T `a` Apple | Strong Customer Authentication for Apple Pay | -
- C `h` Apple | Vision Pro | -
- C `h` Apple | M2 | -
- C `o` Apple | visionOS | 2.4
- note: build number and certificate id dropped

## G073 [hard, network_security, confidence: low, status: labeled]
> Versa Networks Versa Secure SD-WAN Versa Operating System (VOS) 22.1 running on CSG1500, CSG2500, CSG3500, CSG5000, Dell PowerEdge R7515, and Dell VEP4600, Versa Director 22.1, and Versa Analytics 22.1

- T `h` Versa Networks | CSG1500 | -
- T `h` Versa Networks | CSG2500 | -
- T `h` Versa Networks | CSG3500 | -
- T `h` Versa Networks | CSG5000 | -
- T `h` Dell | PowerEdge R7515 | -
- T `h` Dell | VEP4600 | -
- C `o` Versa Networks | Versa Operating System | 22.1
- C `a` Versa Networks | Versa Director | 22.1
- C `a` Versa Networks | Versa Analytics | 22.1
- note: multi-vendor hardware; 'Versa Secure SD-WAN' dropped as the solution name

## G074 [easy, other_hardware, confidence: medium, status: labeled]
> Fort Fox Hardware Data Diode

- T `h` Fort Fox | Hardware Data Diode | -

## G075 [easy, network_security, confidence: low, status: labeled]
> CyberGuard Firewall/VPN Version 6.1.2

- T `o` CyberGuard | Firewall/VPN | 6.1.2
- note: part a vs o depends on D2

## G076 [medium, enterprise_sw, confidence: medium, status: labeled]
> Microsoft SQL Server 2022 Database Engine Enterprise Edition x64 (English) version 16.0.4105.2

- T `a` Microsoft | SQL Server | 16.0.4105.2
- note: '2022', edition, arch and language (D4) dropped

## G077 [easy, other_hardware, confidence: medium, status: labeled]
> ST33TPM12LPC

- T `h` (no vendor) | ST33TPM12LPC | -
- note: vendor (ST) not stated

## G078 [easy, enterprise_sw, confidence: high, status: labeled]
> Alacris OCSP Client Professional v4.0.0

- T `a` Alacris | OCSP Client Professional | 4.0.0

## G079 [hard, smartcard_chip, confidence: medium, status: labeled]
> STMicroelectronics Secured microcontroller ST33F1ME, ST33F768E, SC33F768E, ST33F640E, SC33F640E, ST33F512E, SC33F512E et SC33F384E all with optional cryptographic library NESLIB 3.0

- T `h` STMicroelectronics | ST33F1ME | -
- T `h` STMicroelectronics | ST33F768E | -
- T `h` STMicroelectronics | SC33F768E | -
- T `h` STMicroelectronics | ST33F640E | -
- T `h` STMicroelectronics | SC33F640E | -
- T `h` STMicroelectronics | ST33F512E | -
- T `h` STMicroelectronics | SC33F512E | -
- T `h` STMicroelectronics | SC33F384E | -
- C `a` (no vendor) | NESLIB | 3.0
- note: mixed French/English ('et')

## G080 [medium, other_hardware, confidence: high, status: labeled]
> ST33TPHF20 TPM Firmware 0x4A.0x14 & 0x4A.0x15

- T `h` (no vendor) | ST33TPHF20 | -
- C `o` (no vendor) | TPM Firmware | 0x4A.0x14, 0x4A.0x15

## G081 [medium, enterprise_sw, confidence: low, status: labeled]
> Voltage SecureData Appliance 7.0.2

- T `a` Voltage | SecureData Appliance | 7.0.2
- note: appliance kept as a for consistency with R2 (NVD: email_security_appliance a 104 vs h 11, web_security_appliance a 103 vs h 5); no NVD entry for SecureData

## G082 [easy, smartcard_chip, confidence: medium, status: labeled]
> Winbond Secure Flash Memory W75F32W version 1.0

- T `h` Winbond | W75F32W | 1.0

## G083 [hard, enterprise_sw, confidence: low, status: labeled]
> IBM WebSpherePortal 6.0.0.0 (with APAR PK67104 and APAR PK79436)

- T `a` IBM | WebSphere Portal | 6.0.0.0
- note: APARs (patches) dropped; glued 'WebSpherePortal' split

## G084 [easy, network_security, confidence: medium, status: labeled]
> Motorola AP-7131N Wireless Access Point

- T `h` Motorola | AP-7131N | -
- note: 'Wireless Access Point' dropped as device class

## G085 [easy, network_security, confidence: medium, status: labeled]
> Junos OS 20.3R1 for ACX5448-M

- T `h` (no vendor) | ACX5448-M | -
- C `o` (no vendor) | Junos OS | 20.3R1
- note: vendor Juniper not in the title (R9), so null

## G086 [easy, epassport_applet, confidence: low, status: labeled]
> ID-One CNS v2

- T `a` (no vendor) | ID-One CNS | 2
- note: card OS/application: a vs o undecided

## G087 [hard, printer_mfp, confidence: medium, status: labeled]
> HP Color LaserJet Enterprise M856, HP LaserJet Enterprise M610/M611/M612, HP LaserJet Enterprise M507, HP Color LaserJet Enterprise M751 and HP Color LaserJet Managed E75245 printers with HP FutureSmart 5.7.1.1 Firmware

- T `h` HP | Color LaserJet Enterprise M856 | -
- T `h` HP | LaserJet Enterprise M610 | -
- T `h` HP | LaserJet Enterprise M611 | -
- T `h` HP | LaserJet Enterprise M612 | -
- T `h` HP | LaserJet Enterprise M507 | -
- T `h` HP | Color LaserJet Enterprise M751 | -
- T `h` HP | Color LaserJet Managed E75245 | -
- C `o` HP | FutureSmart | 5.7.1.1
- note: family words (Color LaserJet Enterprise ...) kept in the product

## G088 [hard, network_security, confidence: low, status: labeled]
> Hewlett-Packard Networking A-Series Switches: 12500, 9500, 7500, 5820, 5800, 5500, and 5120

- T `h` Hewlett-Packard | A-Series 12500 | -
- T `h` Hewlett-Packard | A-Series 9500 | -
- T `h` Hewlett-Packard | A-Series 7500 | -
- T `h` Hewlett-Packard | A-Series 5820 | -
- T `h` Hewlett-Packard | A-Series 5800 | -
- T `h` Hewlett-Packard | A-Series 5500 | -
- T `h` Hewlett-Packard | A-Series 5120 | -
- note: bare numbers expanded with the family prefix (D7)

## G089 [easy, epassport_applet, confidence: low, status: labeled]
> DNIe version 4.0

- T `a` (no vendor) | DNIe | 4.0
- note: national eID application: a vs o undecided (D8: application = a)

## G090 [easy, network_security, confidence: high, status: labeled]
> A10 Networks Thunder TPS 3030S

- T `h` A10 Networks | Thunder TPS 3030S | -

## G091 [medium, smartcard_chip, confidence: medium, status: labeled]
> Infineon smartcard IC (Security Controller) M7791 B12 and G11 with specific IC-dedicated firmware

- T `h` Infineon | M7791 | B12
- T `h` Infineon | M7791 | G11
- C `o` (no vendor) | IC-dedicated firmware | -
- note: B12 and G11 read as two steppings

## G092 [easy, mobile_embedded, confidence: medium, status: labeled]
> BlackBerry® Device Software 5.0.0

- T `o` BlackBerry | Device Software | 5.0.0

## G093 [easy, enterprise_sw, confidence: high, status: labeled]
> BMC Server Automation v8.3

- T `a` BMC | Server Automation | 8.3

## G094 [hard, network_security, confidence: medium, status: labeled]
> Cisco ASA 5505, 5510, 5520, 5540, and 5550 (Release 7.2(4)), Cisco VPN Client Release 5.0.03.0560

- T `h` Cisco | ASA 5505 | -
- T `h` Cisco | ASA 5510 | -
- T `h` Cisco | ASA 5520 | -
- T `h` Cisco | ASA 5540 | -
- T `h` Cisco | ASA 5550 | -
- C `o` Cisco | Adaptive Security Appliance Software | 7.2(4)
- C `a` Cisco | VPN Client | 5.0.03.0560
- note: ASA software = o per D2 (NVD name: adaptive_security_appliance_software, o 1024 vs a 680)

## G095 [medium, other_hardware, confidence: low, status: labeled]
> xFusion Server intelligent Baseboard Management Controller iBMC version 3.3.10.7

- T `o` xFusion | iBMC | 3.3.10.7
- note: iBMC is firmware of the server; modelled as an o target

## G096 [medium, network_security, confidence: medium, status: labeled]
> Alcatel-Lucent Enterprise OmniSwitch with AOS 8.6.4.R11

- T `h` Alcatel-Lucent Enterprise | OmniSwitch | -
- C `o` (no vendor) | AOS | 8.6.4.R11

## G097 [hard, network_security, confidence: low, status: labeled]
> Huawei NetEngine AR6700&AR8000 Series Routers’ Yunshan Software V600R021C10SPC100

- T `h` Huawei | NetEngine AR6700 | -
- T `h` Huawei | NetEngine AR8000 | -
- C `o` (no vendor) | Yunshan | V600R021C10SPC100
- note: 'Yunshan Software' naming

## G098 [hard, printer_mfp, confidence: low, status: labeled]
> Ricoh Aficio SP 5200S/5210SF/5210SR, Savin SP 5200S/5210SF/5210SR, Lanier SP 5200S/5210SF/5210SR, nashuatec SP 5200S/5210SF/5210SR, Rex-Rotary SP 5200S/5210SF/5210SR, Gestetner SP 5200S/5210SF/5210SR all of above with Facsimile Function Version: - Software: System/Copy 2.02, Network Support 10.63, Fax 02.00.00, RemoteFax 01.00.00, NetworkDocBox 1.04, Web Support 1.02, Web Uapl 1.02, animation 1.01, Scanner 01.03, Printer 1.02.1, PCL 1.02, PCL Font 1.05, Data Erase Std 1.01m, GWFCU3-24(WW) 02.00.00, Engine A2.0:20, Engine(Scanner) 1.01:00, OpePanel 1.02, LANG0 1.02, LANG1 1.02 Hardware: Ic Key 01020714, Ic Hdd 01

- T `h` Ricoh | Aficio SP 5200S | -
- T `h` Ricoh | Aficio SP 5210SF | -
- T `h` Ricoh | Aficio SP 5210SR | -
- T `h` Savin | SP 5200S | -
- T `h` Savin | SP 5210SF | -
- T `h` Savin | SP 5210SR | -
- T `h` Lanier | SP 5200S | -
- T `h` Lanier | SP 5210SF | -
- T `h` Lanier | SP 5210SR | -
- T `h` nashuatec | SP 5200S | -
- T `h` nashuatec | SP 5210SF | -
- T `h` nashuatec | SP 5210SR | -
- T `h` Rex-Rotary | SP 5200S | -
- T `h` Rex-Rotary | SP 5210SF | -
- T `h` Rex-Rotary | SP 5210SR | -
- T `h` Gestetner | SP 5200S | -
- T `h` Gestetner | SP 5210SF | -
- T `h` Gestetner | SP 5210SR | -
- C `o` (no vendor) | System/Copy | 2.02
- C `o` (no vendor) | Network Support | 10.63
- C `o` (no vendor) | Fax | 02.00.00
- C `o` (no vendor) | RemoteFax | 01.00.00
- C `o` (no vendor) | NetworkDocBox | 1.04
- C `o` (no vendor) | Web Support | 1.02
- C `o` (no vendor) | Web Uapl | 1.02
- C `o` (no vendor) | animation | 1.01
- C `o` (no vendor) | Scanner | 01.03
- C `o` (no vendor) | Printer | 1.02.1
- C `o` (no vendor) | PCL | 1.02
- C `o` (no vendor) | PCL Font | 1.05
- C `o` (no vendor) | Data Erase Std | 1.01m
- C `o` (no vendor) | GWFCU3-24(WW) | 02.00.00
- C `o` (no vendor) | Engine | A2.0:20
- C `o` (no vendor) | Engine(Scanner) | 1.01:00
- C `o` (no vendor) | OpePanel | 1.02
- C `o` (no vendor) | LANG0 | 1.02
- C `o` (no vendor) | LANG1 | 1.02
- C `h` (no vendor) | Ic Key | 01020714
- C `h` (no vendor) | Ic Hdd | 01
- note: very long stress test (6 brands x 3 models + 21 modules); the title itself appears cut at 'Ic Hdd 01'

## G099 [easy, network_security, confidence: high, status: labeled]
> Sophos Firewall OS Version 17.01

- T `o` Sophos | Firewall OS | 17.01

## G100 [medium, network_security, confidence: medium, status: labeled]
> Cisco IronPort S-Series Web Security Appliance (WSA) (S160, S360, S660) running AsyncOS 5.6.1

- T `h` Cisco | IronPort S160 | -
- T `h` Cisco | IronPort S360 | -
- T `h` Cisco | IronPort S660 | -
- C `o` Cisco | AsyncOS | 5.6.1
- note: 'Web Security Appliance (WSA)' dropped as device class
