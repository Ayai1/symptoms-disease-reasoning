# Hybrid Medical Reasoning System (Tree-of-Thoughts + RAG)

A modular AI diagnostic reasoning framework that combines **symbolic reasoning**, **machine learning priors**, and **retrieval-augmented explanations** to assist symptom-to-disease analysis.

Unlike traditional classifiers, this system performs structured reasoning using adaptive questioning, severity-aware scoring, and explainable retrieval pipelines.

---

## Key Features

* Tree-of-Thoughts guided diagnostic questioning
* Rule-based severity scoring with medical weighting
* Random Forest / XGBoost ensemble priors
* Retrieval-Augmented Generation (RAG) for medical explanations
* Modular architecture for experimentation and research

---

## System Architecture

The pipeline integrates multiple reasoning layers:

1. **Symptom Normalization**
   Semantic normalization aligns user input with canonical symptom space.

2. **Rule-Based Reasoning**
   Severity-weighted scoring generates interpretable disease priors.

3. **ML Ensemble Prior**
   Random Forest and XGBoost models provide probabilistic signals.

4. **Tree-of-Thoughts Reasoning**
   Adaptive follow-up questioning refines diagnostic confidence.

5. **RAG Explainability**
   PubMed-based retrieval modules provide contextual medical explanations.

---

## Project Structure

```
src/                 Core reasoning modules
data/                Lightweight symptom datasets
rag_*.py             Retrieval & explanation utilities
run_training.py      Model training entrypoint
run_diagnosis.py     Interactive diagnostic pipeline
api_server.py        API interface
```

---

## Dataset

This project uses curated symptom–disease datasets and severity metadata.

Included:

* dataset.csv
* Symptom-severity.csv
* symptom_description.csv
* symptom_precaution.csv

Large retrieval indexes are **not included** due to size (~6GB).

To rebuild RAG data:

```
python rag_pubmed_loader.py
python rag_pubmed_index.py
```

---

## Installation

```
pip install -r requirements.txt
```

---

## Usage

Run interactive diagnosis:

```
python run_diagnosis.py
```

Train models:

```
python run_training.py
```

Start API server:

```
python api_server.py
```

---

Example Interactive Run
$ python run_diagnosis.py

Diagnosing symptoms: 'high, fever', 'cough', 'chest, pain'
Use interactive mode? yes

--- Iteration 1 ---
Top Hypotheses:
1. GERD — 33.2%
2. Bronchial Asthma — 24.9%
3. Pneumonia — 23.5%

Follow-up Questions:
Do you have stomach pain? → yes
Do you have vomiting? → yes

FINAL DIAGNOSIS
Most Likely: GERD (90.0% confidence)
Matched Symptoms: CHEST_PAIN, COUGH, STOMACH_PAIN, VOMITING

This demonstrates Tree-of-Thoughts guided questioning, ensemble reasoning, and explainable diagnostic output from the hybrid medical reasoning system.

## Notes

This system is intended for **research and educational purposes only**
and does not provide medical advice.

---

## License

MIT License
