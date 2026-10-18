# Clinical Verification Audit & v2 Rebuild Plan

**Project:** Symptom Assistant: Hybrid Clinical Decision-Support & RAG System  
**Lead Engineer:** Syed Ayaan Ahmed ([github.com/Ayai1](https://github.com/Ayai1))  
**Status:** v1 Audited | v2 Rebuild Specification Active  

## 1. Mathematical Proof of Data Leakage (304 / 4,920 Rows)
- Total Rows: 4,920 across 41 classes
- Unique Symptom Vectors: 304 (93.82% duplication rate, ~16.2 copies per vector)
- Test Partition Overlap: 100.0% of test vectors are identical twins in train set, inflating test accuracy to 100.0%.

## 2. The 18-Defect Verification Log
Cataloging 18 defects across Data Integrity (DEF-01 to 04), Clinical Safety & Escalation (DEF-05 to 09), RAG & Explainability Guardrails (DEF-10 to 13), and Architecture (DEF-14 to 18).

## 3. The 15 Architectural Decision Records (ADRs)
Governing deterministic red-flag triage, hash-based deduplication, ternary symptom encoding, country-aware dispatch, and Pydantic v2 contracts.

## 4. The 23 Deterministic Clinical Escalation Rules (39 Warning Signals)
1. Acute Coronary Syndrome (crushing substernal pain radiating to arm/jaw or diaphoresis)
2. Pulmonary Embolism (sharp pleuritic pain + acute dyspnea + hemoptysis)
3. Acute Stroke - FAST (facial droop + arm weakness + slurred speech)
4. Anaphylaxis (angioedema + stridor/wheezing + hypotension)
5. Severe Sepsis (fever/hypothermia + systolic BP < 90 + altered mental state)
...and 18 additional acute clinical emergency rules.

### Verified Emergency Dispatch Numbers
- India: 112 (National Emergency), 108 (Ambulance), 102 (Maternal/Child)
- United States: 911 (Emergency), 988 (Crisis Lifeline)
- United Kingdom: 999 (Emergency), 111 (NHS Urgent Care)

## 5. The 8-Phase Rebuild Plan & Acceptance Gates
Phases 1-8 covering deduplicated splits, deterministic triage, calibrated priors, constrained Tree-of-Thoughts, PubMed grounding, and automated safety regression suites.
