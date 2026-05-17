# Evidence Corpus

This directory holds the clinical evidence documents that power ToothTrust's RAG pipeline. It currently contains 30 seeded summary documents covering restorative dentistry, endodontics, periodontics, insurance/coding, and diagnosis/imaging.

## What belongs here

- ADA clinical practice guidelines (PDF or markdown summaries)
- Cochrane systematic reviews (PDF or HTML)
- Journal articles on evidence-based dentistry
- AAP periodontal guidelines
- AAPD pediatric dentistry guidelines

## What does NOT belong here

- Patient records or any PHI
- Proprietary content without a license to use it

## Ingestion

Run `src/ingest.py` (or notebook `01_corpus_ingestion.ipynb`) to chunk and embed documents into ChromaDB:

```bash
python -m src.ingest --source data/corpus/ --collection dental_evidence
```

## Licensing notes

Verify licensing before adding any document. ADA guidelines may require a license for commercial use. Cochrane abstracts are open-access; full text requires a subscription or author permission. The seeded markdown files in this corpus are demonstration summaries, not reproductions of copyrighted primary sources.

---

## Corpus Index

### Restorative Dentistry (8 documents)

| File | Title | Source Org |
|------|-------|-----------|
| [crown_indications_ada.md](crown_indications_ada.md) | Crown Indications — ADA Guidance | ADA |
| [composite_vs_crown_decision_criteria.md](composite_vs_crown_decision_criteria.md) | Composite vs. Crown — Decision Criteria | ADA / JEBDP |
| [amalgam_to_composite_replacement.md](amalgam_to_composite_replacement.md) | Amalgam-to-Composite Replacement — Clinical Criteria | ADA / FDA |
| [caries_classification_icdas.md](caries_classification_icdas.md) | Caries Classification — ICDAS System | ICDAS Coordinating Committee |
| [caries_risk_assessment_cambra.md](caries_risk_assessment_cambra.md) | Caries Risk Assessment — CAMBRA Protocol | CDA / UCSF |
| [minimally_invasive_dentistry_principles.md](minimally_invasive_dentistry_principles.md) | Minimally Invasive Dentistry — Core Principles | FDI World Dental Federation |
| [pulp_capping_indirect_direct.md](pulp_capping_indirect_direct.md) | Pulp Capping — Indirect and Direct Techniques | AAE / AAPD |
| [post_and_core_indications.md](post_and_core_indications.md) | Post and Core — Indications and Selection Criteria | ACP |

### Endodontics (6 documents)

| File | Title | Source Org |
|------|-------|-----------|
| [aae_retreatment_position_statement.md](aae_retreatment_position_statement.md) | AAE Position Statement — Endodontic Retreatment | AAE |
| [endo_vs_extraction_decision_framework.md](endo_vs_extraction_decision_framework.md) | Endodontic Treatment vs. Extraction — Decision Framework | AAE |
| [apical_periodontitis_diagnosis.md](apical_periodontitis_diagnosis.md) | Apical Periodontitis — Diagnosis and Classification | AAE |
| [endodontic_success_rates_literature.md](endodontic_success_rates_literature.md) | Endodontic Success Rates — Literature Review | AAE / J Endodontics |
| [cracked_tooth_diagnosis_treatment.md](cracked_tooth_diagnosis_treatment.md) | Cracked Tooth — Diagnosis and Treatment | AAE |
| [root_canal_outcomes_meta_analysis.md](root_canal_outcomes_meta_analysis.md) | Root Canal Treatment Outcomes — Meta-Analysis Summary | IEJ / J Endodontics |

### Periodontics (6 documents)

| File | Title | Source Org |
|------|-------|-----------|
| [aap_2017_classification_system.md](aap_2017_classification_system.md) | AAP/EFP 2017 Classification of Periodontal Diseases | AAP / EFP |
| [srp_medical_necessity_criteria.md](srp_medical_necessity_criteria.md) | Scaling and Root Planing — Medical Necessity Criteria | AAP |
| [periodontal_charting_requirements.md](periodontal_charting_requirements.md) | Periodontal Charting — Clinical Requirements and Standards | AAP / ADA |
| [gingivitis_vs_periodontitis_diagnosis.md](gingivitis_vs_periodontitis_diagnosis.md) | Gingivitis vs. Periodontitis — Differential Diagnosis | AAP |
| [maintenance_therapy_protocols.md](maintenance_therapy_protocols.md) | Periodontal Maintenance Therapy — Protocols and Evidence | AAP |
| [bone_loss_radiographic_interpretation.md](bone_loss_radiographic_interpretation.md) | Bone Loss — Radiographic Interpretation in Periodontics | AAP / AAOMR |

### Insurance & Coding (5 documents)

| File | Title | Source Org |
|------|-------|-----------|
| [cdt_code_reference_common_procedures.md](cdt_code_reference_common_procedures.md) | CDT Code Reference — Common Dental Procedures | ADA CDT 2024 |
| [dental_insurance_medical_necessity_overview.md](dental_insurance_medical_necessity_overview.md) | Dental Insurance — Medical Necessity Overview | ADA / NADP |
| [common_denial_reasons_appeals.md](common_denial_reasons_appeals.md) | Common Denial Reasons and Appeal Strategies | ADA |
| [pre_authorization_requirements.md](pre_authorization_requirements.md) | Pre-Authorization Requirements in Dental Insurance | ADA / NADP |
| [documentation_standards_clinical_notes.md](documentation_standards_clinical_notes.md) | Documentation Standards for Dental Clinical Notes | ADA / State Practice Acts |

### Diagnosis & Imaging (5 documents)

| File | Title | Source Org |
|------|-------|-----------|
| [bitewing_radiograph_interpretation.md](bitewing_radiograph_interpretation.md) | Bitewing Radiograph — Interpretation Guide | AAOMR / ADA |
| [periapical_radiograph_interpretation.md](periapical_radiograph_interpretation.md) | Periapical Radiograph — Interpretation Guide | AAOMR |
| [cbct_indications_guidelines.md](cbct_indications_guidelines.md) | CBCT — Indications and Clinical Guidelines | AAOMR / AAE / AAP |
| [common_radiographic_findings_pathology.md](common_radiographic_findings_pathology.md) | Common Radiographic Findings and Pathology | AAOMR |
| [aae_glossary_endodontic_terms.md](aae_glossary_endodontic_terms.md) | AAE Glossary — Key Endodontic Terms | AAE |

---

## Document Structure

Each file follows this schema:

```yaml
---
title: <Document Title>
source_org: <Authoring Organization>
topic: <Clinical Category>
last_reviewed: <YYYY-MM>
---
```

Followed by sections: **Summary** · **Clinical Indications** · **Contraindications** · **Evidence Notes** · **Source Attribution** · **Demo Disclaimer**

---

> **Corpus Disclaimer:** This entire corpus is a curated set of summaries prepared for the ToothTrust prototype. No document in this corpus constitutes clinical advice or replaces primary guidelines. All content is for demonstration purposes only.
