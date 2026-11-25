# AI Launch Gate & Compliance Engine

A working proof-of-concept (**Governance-as-Workflow**) built with Python and Streamlit that translates AI evaluation telemetry into risk-tiered launch decisions, maps technical metrics to regulatory obligations, captures compensating controls and audit sign-offs, and generates standardized Model Cards.

## Why This Exists
AI governance often stalls when compliance policies live in static PDFs while engineering evaluation results live in raw test logs or ad-hoc spreadsheets. This prototype operationalizes pre-launch risk gating so engineering, legal, and risk leads can evaluate readiness consistently before deployment.

## Key Capabilities
- **Risk-Tiered Thresholds (`config/governance_rules.yaml`):** Applies stricter thresholds and human sign-off requirements to higher-risk use cases (e.g., EU AI Act Annex III) than lower-risk use cases (e.g., EU AI Act Art. 50).
- **Automated Gap & Risk Scoring (`src/engine.py`):** Evaluates actual metrics against tier thresholds, calculates variance deltas, computes a composite risk score, and determines baseline status (`APPROVED`, `CONDITIONAL_HOLD`, or `BLOCKED`).
- **Regulatory & Framework Mapping:** Connects evaluation dimensions—jailbreak resistance, PII leakage prevention, demographic parity, and audit logging coverage—to obligations across the EU AI Act, GDPR, NIST AI RMF, and Google SAIF principles.
- **Compensating Controls & Audit Trail (`data/audit_log.json`):** Allows reviewers to select mitigations, record decisions and rationales, and persist a timestamped audit log.
- **Model Card Generation (`src/model_card_gen.py`):** Produces a downloadable Markdown Model Card summarizing evaluation results, framework mappings, compensating controls, and known limitations.

## Project Structure
```text
ai-governance-gate/
├── config/
│   └── governance_rules.yaml
├── data/
│   ├── audit_log.json
│   └── sample_releases.json
├── src/
│   ├── __init__.py
│   ├── engine.py
│   └── model_card_gen.py
├── app.py
└── requirements.txt

Try it. It looks like this -> https://ai-governance-gate-skala.streamlit.app/
