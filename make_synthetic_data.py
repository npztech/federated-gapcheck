"""
Generate synthetic technical-file documents for three simulated manufacturer nodes.

IMPORTANT: every document here is fabricated for demonstration purposes.
Never place real client technical files in this repository.
"""

from pathlib import Path

ROOT = Path(__file__).parent / "nodes"

# Manufacturer A - Ningbo. Complete file, registration-ready.
A = {
    "01_device_description_and_specification.md": """# Device description and specification

Product: Single-use sterile infusion set, model NB-IS-200 series
Variants: NB-IS-200, NB-IS-210 (with Y-site), NB-IS-220 (light-protected)
Classification: Class IIa, Rule 2 (UK MDR 2002, Annex IX)
Intended purpose: Administration of intravenous fluids to patients in
clinical settings, by trained healthcare professionals.
Accessories: none supplied separately.
Shelf life: 36 months.
""",
    "02_labelling_and_ifu_en.md": """# Labelling and instructions for use (English)

Outer carton label content, unit label content and full IFU text.
Includes UKCA mark placement, UKRP name and GB address block,
lot number, expiry date, single-use symbol, sterilisation method symbol.
Language: English.
""",
    "03_essential_requirements_checklist.md": """# Essential requirements checklist

Conformity assessed against UK MDR 2002 Annex I (essential requirements
as retained in GB law). Each requirement addressed with method of
conformity, standard applied, and reference to evidence in the file.
Not applicable items are justified individually.
""",
    "04_risk_management_report_iso14971.md": """# Risk management report

Prepared to ISO 14971:2019. Contains risk management plan, hazard
identification, risk estimation and evaluation, risk control measures,
residual risk evaluation and overall risk/benefit conclusion.
Reviewed and approved 2025-11-04.
""",
    "05_biocompatibility_iso10993.md": """# Biological evaluation report

ISO 10993-1 categorisation: external communicating device, blood path
indirect, limited duration contact.
Testing performed: cytotoxicity (10993-5), sensitisation (10993-10),
irritation (10993-23), haemocompatibility (10993-4).
All results pass. Test house report references included.
""",
    "06_sterilisation_validation_eo.md": """# Sterilisation validation

Method: ethylene oxide. Validated to ISO 11135.
SAL 10^-6 demonstrated. EO and ECH residuals within ISO 10993-7 limits.
Includes bioburden monitoring and quarterly revalidation schedule.
""",
    "07_clinical_evaluation_report.md": """# Clinical evaluation report

Prepared to MEDDEV 2.7/1 rev 4 methodology.
Route: equivalence to predicate device plus literature review.
Literature search date: 2025-09-18. Next scheduled update: 2027-09.
Conclusion: clinical evidence supports the intended purpose.
""",
    "08_iso13485_certificate.md": """# Quality management system certificate

Standard: ISO 13485:2016
Scope: design, development and manufacture of single-use infusion sets.
Valid until 2027-06-30.
""",
    "09_approved_body_certificate.md": """# Approved Body certificate

UK Approved Body certificate covering Annex II conformity assessment
for Class IIa devices. Certificate valid until 2028-02-14.
""",
    "10_declaration_of_conformity.md": """# Declaration of conformity

We declare under our sole responsibility that the device described
above is in conformity with the Medical Devices Regulations 2002
(SI 2002 No 618, as amended).
Signed by the authorised signatory, dated 2026-01-22.
Includes UKRP name and GB address.
""",
    "11_ukrp_designation_letter.md": """# UK Responsible Person designation

Letter of designation appointing the UKRP for GB market, listing the
device models covered, effective date and the scope of tasks delegated
under regulation 7A.
Countersigned by both parties.
""",
    "12_post_market_surveillance_plan.md": """# Post-market surveillance plan

Describes proactive and reactive data collection, complaint handling,
trend reporting thresholds, vigilance reporting route to the MHRA,
and the periodic review cycle.
""",
}

# Manufacturer B - Shenzhen. Two clear gaps, one incomplete item.
B = {
    "device_description.md": """# Device description

Product: Digital clinical thermometer, model SZ-DT-15
Classification: Class IIa
Intended purpose: measurement of human body temperature, home and
clinical use.
""",
    "labelling_and_ifu.md": """# Labelling and IFU

Carton artwork and IFU text supplied in English.
UKCA mark applied. UKRP address block present.
""",
    "essential_requirements.md": """# Essential requirements checklist

Assessed against UK MDR 2002 Annex I.
NOTE: sections on electrical safety and EMC are marked "to be completed"
and no evidence references have been entered against requirements 12.x.
This document is a partial draft.
""",
    "risk_management_iso14971.md": """# Risk management report

Prepared to ISO 14971:2019. Hazard analysis, risk controls and residual
risk evaluation complete. Approved 2026-02-11.
""",
    "iso13485_cert.md": """# ISO 13485:2016 certificate

Scope: manufacture of electronic medical thermometers.
Valid until 2028-03-15.
""",
    "approved_body_cert.md": """# Approved Body certificate

Certificate covering Class IIa conformity assessment.
Valid until 2027-11-30.
""",
    "declaration_of_conformity.md": """# Declaration of conformity

Declares conformity with the Medical Devices Regulations 2002.
Signed 2026-03-02.
""",
    "ukrp_agreement.md": """# UKRP agreement

Agreement appointing the UK Responsible Person, including letter of
designation and scope of delegated tasks.
""",
    # deliberately absent: clinical evaluation report, PMS plan,
    # biocompatibility, sterilisation (last two are not applicable anyway)
}

# Manufacturer C - Guangzhou. Early stage, roughly half the file exists.
C = {
    "product_spec_v2.md": """# Product specification

Product: Orthopaedic knee support with adjustable hinge, model GZ-KS-4
Classification: Class I (proposed) - classification under review
Intended purpose: immobilisation and support of the knee joint
following injury or surgery.
""",
    "ifu_draft_english.md": """# Instructions for use (DRAFT)

English text drafted from the Chinese original.
NOTE: this is a draft. Not yet reviewed by a native speaker.
Carton artwork not yet produced. UKRP address block not yet inserted.
""",
    "risk_file.md": """# Risk management file

Prepared to ISO 14971. Hazard analysis complete.
Risk control verification in progress.
""",
    "biocompatibility_report.md": """# Biological evaluation

Skin-contacting materials assessed under ISO 10993-1.
Cytotoxicity, sensitisation and irritation testing completed and passed.
""",
    "iso13485_certificate.md": """# ISO 13485:2016 certificate

Scope: manufacture of orthopaedic supports and braces.
Valid until 2027-09-01.
""",
    "declaration_of_conformity_draft.md": """# Declaration of conformity (DRAFT)

DRAFT ONLY - unsigned.
NOTE: current text cites Regulation (EU) 2017/745. This must be
corrected to the Medical Devices Regulations 2002 for the GB market.
No authorised signatory named. No date.
""",
    # deliberately absent: essential requirements checklist, CER,
    # UKRP designation, PMS plan, sterilisation validation
}


def write(folder: str, docs: dict) -> None:
    target = ROOT / folder
    target.mkdir(parents=True, exist_ok=True)
    for name, body in docs.items():
        (target / name).write_text(body, encoding="utf-8")
    print(f"{folder}: {len(docs)} documents written")


if __name__ == "__main__":
    write("manufacturer_a", A)
    write("manufacturer_b", B)
    write("manufacturer_c", C)
    print("\nSynthetic data ready. All content is fabricated.")
