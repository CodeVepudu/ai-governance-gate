# AI Launch Gate & Audit Assurance Engine (BFSI & MedTech)

An executable AI governance and release-assurance platform built in Python and Streamlit for high-accountability environments across the DACH region and EU. It translates regulatory obligations into versioned policy-as-code, audits subgroup fairness and validation integrity before release sign-off, and records decisions in a tamper-evident SHA-256 hash-chained ledger.

---

## Why This Exists: Moving Beyond "Paper Compliance"

In regulated sectors such as banking, insurance, and medical technology, relying solely on aggregate evaluation scores or static policy PDFs can mask real operational and compliance risks:

- **Hidden Subgroup & Sample Gaps:** A model can pass top-level benchmark thresholds while underperforming on specific cohorts (such as young thin-file credit applicants or elderly/female clinical cohorts) or relying on an underpowered validation sample.
- **Disconnected Regulatory Controls:** Requirements across EU and German frameworks are often tracked manually in spreadsheets rather than enforced systematically at release time.
- **Mutable Audit Trails:** Standard logs or editable approval records make it difficult to prove non-repudiation and post-hoc integrity during supervisory or internal audits.

This project separates **Threshold Risk** from **Evaluation Integrity**, requiring explicit compensating controls and human sign-off whenever a release is placed on `CONDITIONAL_HOLD` or fails integrity checks.

---

## Regulatory Coverage & Risk Tiers

Policy rules, thresholds, minimum sample sizes, maximum allowed subgroup performance drops, compensating controls, and regulatory mappings are defined declaratively in `config/governance_rules.yaml`.

| Risk Tier | Target Use Cases | Key Regulatory Alignment | Core Gate Controls |
| :--- | :--- | :--- | :--- |
| **BFSI High Risk** (`bfsi_high_risk`) | Creditworthiness scoring, loan pricing, underwriting | EU AI Act (Annex III 5b/c), DORA (ICT resilience & logging), BaFin MaRisk, GDPR Art. 25 | Minimum sample size, subgroup drop ceiling, high audit logging coverage, compensating controls (e.g., exposure caps, explanation/reason-code controls, periodic re-validation) |
| **MedTech High Risk** (`medtech_high_risk`) | Clinical triage, diagnostic support, patient risk stratification | EU AI Act (Annex I / III), EU MDR 2017/745, ISO 13485, GDPR Art. 9 | Strict validation sample requirements, tight subgroup drop tolerance, high PII protection & logging, human/clinician oversight and fallback/abstention controls |
| **Limited Risk** (`limited_risk`) | Informational assistants and customer-facing support bots | EU AI Act Art. 50, GDPR Art. 5(1)(f) | Baseline thresholds, transparency/disclosure controls, and PII protection |

---

## Repository Structure

```text
ai-governance-gate/
├── app.py                        # Streamlit assurance console (4-tab workflow & sidebar status)
├── Launch_AI_Gate.bat            # Windows launcher script for virtual environment & Streamlit app
├── config/
│   └── governance_rules.yaml     # Policy-as-code thresholds, tiers, controls & regulatory mappings
├── data/
│   ├── sample_releases.json      # Sample BFSI, MedTech, and Limited Risk release candidates
│   └── audit_log.json            # Append-only SHA-256 hash-chained decision ledger
├── src/
│   ├── engine.py                 # Threshold evaluation, risk scoring & gate decision logic
│   ├── integrity_auditor.py      # Validation sample size & subgroup performance drop checks
│   ├── ledger.py                 # SHA-256 hash-chaining & chain integrity verification
│   └── model_card_gen.py         # Markdown model card generator incorporating controls & rationale
└── README.md
```

---

## Architecture & Assurance Workflow

1. **Release Selection & Metadata Inspection (`app.py`, `data/sample_releases.json`):** Load a release candidate with its risk tier, version, owner team, validation sample size, dataset hash, subgroup metrics, and benchmark metrics.
2. **Threshold & Regulatory Mapping (`src/engine.py`, `config/governance_rules.yaml`):** Evaluate technical metrics against tier-specific thresholds and map each check to relevant regulatory obligations.
3. **Evaluation Integrity & Subgroup Auditing (`src/integrity_auditor.py`):** Verify whether validation sample size meets tier minimums and detect subgroup drops beyond the allowed variance threshold.
4. **Compensating Controls, Sign-Off & Model Card (`src/model_card_gen.py`):** Capture selected compensating controls, reviewer rationale, and sign-off context, then generate a downloadable Model Card in Markdown.
5. **Tamper-Evident SHA-256 Audit Ledger (`src/ledger.py`, `data/audit_log.json`):** Commit each decision linked to the previous block's hash (`prev_hash`) and recompute digests on load to detect unauthorized edits or broken chain links.

---

## Getting Started

### Prerequisites

- Python 3.10+
- Dependencies installed in your virtual environment (`streamlit`, `pyyaml`, `pandas`)

### Run Locally

Using the Windows launcher:

```bat
Launch_AI_Gate.bat
```

Or directly from PowerShell / terminal inside the project directory:

```powershell
.\venv\Scripts\Activate.ps1
streamlit run app.py
```

---

## Testing Ledger Tamper Detection

1. Commit a sign-off entry in the **Sign-Off & Model Card** tab so `data/audit_log.json` contains at least one chained block.
2. Open `data/audit_log.json` and alter a signed field (such as `rationale`, `decision`, or `prev_hash`) without recomputing `entry_hash`.
3. Refresh the Streamlit app (`F5` or `Ctrl + R`).
4. Confirm that the sidebar and ledger view flag the hash mismatch and/or broken chain link.
5. Restore `data/audit_log.json` to a clean state before committing changes to version control.

---

## Roadmap & Extension Ideas

- **CI/CD Gate Integration:** Run `evaluate_release()` and integrity checks automatically in pull request / model registry pipelines before artifact promotion.
- **Role-Based Sign-Off & Export Bundles:** Add structured reviewer roles (e.g., Risk Officer, Clinical Safety Lead, Compliance Officer) and exportable audit evidence packages.
- **Expanded Regulatory Packs:** Add additional DACH/EU control profiles (such as post-market surveillance cadences or third-party vendor concentration checks).