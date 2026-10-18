import streamlit as st
import pandas as pd

st.set_page_config(page_title="Symptom Assistant Triage", layout="wide", page_icon="ðŸ©º")
st.title("ðŸ©º Symptom Assistant: Clinical Decision-Support & Triage")

col1, col2 = st.columns([1, 2])
with col1:
    age = st.slider("Patient Age", 1, 100, 25)
    country = st.selectbox("Dispatch Region", ["IN (India)", "US (United States)", "UK (United Kingdom)"])
    symptoms = st.multiselect("Presenting Symptoms", ["chest pain", "shortness of breath", "left arm pain", "facial droop", "slurred speech", "cough", "fatigue"], default=["cough", "fatigue"])
    run_btn = st.button("Run Diagnostic Triage", type="primary")

with col2:
    if run_btn or symptoms:
        norm = [s.lower().replace(" ", "_") for s in symptoms]
        if "chest_pain" in norm and any(s in norm for s in ["shortness_of_breath", "left_arm_pain"]):
            st.error("ðŸš¨ CRITICAL ESCALATION: Suspected Acute Coronary Syndrome. Call 112 / 108 immediately.")
        elif any(s in norm for s in ["facial_droop", "slurred_speech"]):
            st.error("ðŸš¨ CRITICAL ESCALATION: Suspected Acute Stroke (FAST Protocol). Seek immediate emergency care.")
        else:
            st.success("âœ… No acute red-flag life threats detected.")

        chart_data = pd.DataFrame({"Condition": ["Viral Upper Respiratory", "Bronchitis", "Allergic Rhinitis"], "Probability": [0.60, 0.25, 0.15]})
        st.bar_chart(chart_data.set_index("Condition"))
