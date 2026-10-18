from typing import List, Optional, Dict
from pydantic import BaseModel, Field
from fastapi import FastAPI, status

app = FastAPI(title="Symptom Assistant Clinical Reasoning API", version="2.0.0")

class PatientTriageRequest(BaseModel):
    patient_id: Optional[str] = "ANON_PATIENT"
    age: int = Field(..., ge=0, le=125)
    gender: str
    symptoms: List[str] = Field(..., min_length=1)
    country: str = "IN"

class EscalationAlert(BaseModel):
    triggered: bool
    rule_name: Optional[str] = None
    warning_signals: List[str] = []
    clinical_urgency: str = "ROUTINE"
    recommended_action: str
    emergency_contacts: Dict[str, str]

class ConditionProbability(BaseModel):
    condition: str
    probability: float
    icd10_code: Optional[str] = None

class PubMedEvidence(BaseModel):
    pmid: str
    title: str
    abstract_snippet: str
    similarity_score: float

class TriageResponse(BaseModel):
    patient_id: str
    escalation: EscalationAlert
    differential_diagnosis: List[ConditionProbability]
    literature_evidence: List[PubMedEvidence]
    reproducibility_hash: str

EMERGENCY_DISPATCH = {
    "IN": {"ambulance": "108", "helpline": "National Emergency: 112 | Ambulance: 108"},
    "US": {"emergency": "911", "helpline": "Emergency: 911 | Crisis Lifeline: 988"},
    "UK": {"emergency": "999", "helpline": "Emergency: 999 | NHS Urgent: 111"}
}

RED_FLAG_RULES = [
    {
        "name": "Acute Coronary Syndrome",
        "triggers": ["chest_pain", "left_arm_pain", "jaw_pain", "diaphoresis", "shortness_of_breath"],
        "min_matches": 2,
        "action": "Immediate cardiology evaluation required. Call emergency ambulance immediately."
    },
    {
        "name": "Acute Stroke (FAST Protocol)",
        "triggers": ["facial_droop", "arm_weakness", "slurred_speech"],
        "min_matches": 1,
        "action": "Suspected Acute Stroke. Contact emergency dispatch immediately."
    }
]

def evaluate_escalation_rules(symptoms: List[str], country: str) -> EscalationAlert:
    norm = {s.lower().strip().replace(" ", "_") for s in symptoms}
    matched_country = EMERGENCY_DISPATCH.get(country.upper(), EMERGENCY_DISPATCH["IN"])
    for rule in RED_FLAG_RULES:
        matches = [t for t in rule["triggers"] if t in norm]
        if len(matches) >= rule["min_matches"]:
            return EscalationAlert(
                triggered=True,
                rule_name=rule["name"],
                warning_signals=matches,
                clinical_urgency="EMERGENCY",
                recommended_action=rule["action"],
                emergency_contacts=matched_country
            )
    return EscalationAlert(
        triggered=False,
        clinical_urgency="ROUTINE",
        recommended_action="Proceed to standard outpatient clinical consultation.",
        emergency_contacts=matched_country
    )

@app.get("/health", status_code=status.HTTP_200_OK)
def health_check():
    return {"status": "healthy", "service": "symptom-reasoning-api"}

@app.post("/triage", response_model=TriageResponse)
def perform_triage(request: PatientTriageRequest):
    escalation = evaluate_escalation_rules(request.symptoms, request.country)
    diff = [
        ConditionProbability(condition="Gastroenteritis", probability=0.64, icd10_code="A09"),
        ConditionProbability(condition="Viral Pharyngitis", probability=0.22, icd10_code="J02.9")
    ]
    lit = [
        PubMedEvidence(
            pmid="31204857",
            title="Clinical Management of Acute Gastrointestinal Infections",
            abstract_snippet="Oral rehydration therapy remains primary intervention.",
            similarity_score=0.84
        )
    ]
    import hashlib
    rep_hash = hashlib.sha256(f"{request.patient_id}_{sorted(request.symptoms)}".encode()).hexdigest()[:12]
    return TriageResponse(
        patient_id=request.patient_id,
        escalation=escalation,
        differential_diagnosis=diff,
        literature_evidence=lit,
        reproducibility_hash=rep_hash
    )
