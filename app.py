import json
from pathlib import Path
import yaml
import pandas as pd
import streamlit as st

from src.engine import evaluate_release
from src.integrity_auditor import audit_evaluation_integrity
from src.ledger import load_ledger, append_ledger_entry, verify_ledger_integrity
from src.model_card_gen import generate_model_card

BASE_DIR = Path(__file__).resolve().parent
RULES_PATH = BASE_DIR / "config" / "governance_rules.yaml"
RELEASES_PATH = BASE_DIR / "data" / "sample_releases.json"
LEDGER_PATH = BASE_DIR / "data" / "audit_log.json"

st.set_page_config(page_title="AI Launch Gate & Audit Engine", layout="wide")


def load_yaml(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


rules = load_yaml(RULES_PATH)
releases = load_json(RELEASES_PATH)

st.title("🛡️ AI Launch Gate & Audit Assurance Engine (BFSI & MedTech)")
st.caption("EU AI Act • DORA / BaFin MaRisk • EU MDR 2017/745 • Tamper-Evident SHA-256 Ledger")

# Sidebar: Release Selection & Live Ledger Integrity Banner
st.sidebar.header("1. Release Candidate")
release_labels = [f"{r['release_id']} — {r['model_name']}" for r in releases]
selected_label = st.sidebar.selectbox("Select Model Release", release_labels)
selected_idx = release_labels.index(selected_label)
release = releases[selected_idx]

tier_key = release["risk_tier"]
tier_cfg = rules["risk_tiers"][tier_key]

st.sidebar.markdown(f"**Owner:** {release['owner']}")
st.sidebar.markdown(f"**Version:** `{release['version']}`")
st.sidebar.markdown(f"**Tier:** {tier_cfg['label']}")
st.sidebar.markdown(f"**Dataset Hash:** `{release.get('evaluation_metadata', {}).get('dataset_hash', 'N/A')[:16]}...`")

st.sidebar.divider()
st.sidebar.header("2. Ledger Integrity Status")
ledger_entries = load_ledger(LEDGER_PATH)
is_chain_valid, tamper_alerts = verify_ledger_integrity(ledger_entries)
if is_chain_valid:
    st.sidebar.success(f"SHA-256 Chain Verified ({len(ledger_entries)} entries)")
else:
    st.sidebar.error("LEDGER TAMPERING DETECTED")
    for alert in tamper_alerts:
        st.sidebar.warning(alert)

# Run Core Threshold Engine + Evaluation Integrity Auditor
eval_result = evaluate_release(release, rules)
integrity_result = audit_evaluation_integrity(release, tier_cfg)

# Effective Gate Status escalates if Evaluation Integrity fails
effective_status = eval_result["status"]
if integrity_result["integrity_status"] == "FAILED_INTEGRITY" and effective_status == "APPROVED":
    effective_status = "CONDITIONAL_HOLD"

# Top KPI Cards
col1, col2, col3, col4 = st.columns(4)
col1.metric("Effective Gate Status", effective_status)
col2.metric("Threshold Risk Score", f"{eval_result['risk_score']} / 100")
col3.metric("Evaluation Integrity", integrity_result["integrity_status"])
col4.metric(
    "Validation Sample Size",
    f"{integrity_result['sample_size']:,}",
    delta=f"Min: {integrity_result['min_sample_size']:,}",
)

st.divider()

# Tabs for Thresholds, Integrity/Subgroups, Sign-Off, and Tamper-Evident Ledger
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Threshold & Regulatory Mapping",
    "🔍 Evaluation Integrity & Subgroups",
    "✍️ Sign-Off & Model Card",
    "⛓️ Tamper-Evident Audit Ledger",
])

with tab1:
    st.subheader("Technical Metrics vs. Regulatory Thresholds")
    raw_checks = (
        eval_result.get("checks")
        or eval_result.get("results")
        or eval_result.get("metric_results")
        or eval_result.get("evaluations")
        or eval_result.get("metric_checks")
    )

    rows = []
    if isinstance(raw_checks, dict):
        items = list(raw_checks.items())
    elif isinstance(raw_checks, list):
        items = []
        for i, item in enumerate(raw_checks):
            if isinstance(item, dict):
                m_name = (
                    item.get("metric")
                    or item.get("metric_name")
                    or item.get("key")
                    or item.get("id")
                    or item.get("name")
                    or f"Metric {i+1}"
                )
                items.append((m_name, item))
    else:
        items = []
   

    for metric_name, details in items:
        reg_info = details.get("regulation") or details.get("framework") or "EU AI Act / NIST AI RMF"
        reg_label = reg_info.get("framework", "EU AI Act / NIST AI RMF") if isinstance(reg_info, dict) else str(reg_info)
        passed_flag = details.get("passed", details.get("status") == "PASS")
        rows.append({
            "Metric": metric_name,
            "Actual (%)": details.get("actual", details.get("value", "N/A")),
            "Threshold (%)": details.get("threshold", "N/A"),
            "Delta": details.get("delta", "N/A"),
            "Status": "PASS" if passed_flag else "GAP",
            "Regulatory Mapping": reg_label,
        })

    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("Expand below to inspect raw engine output keys.")
        with st.expander("Raw Engine Output"):
            st.json(eval_result)

with tab2:
    st.subheader("Anti-Gaming & Subgroup Slice Audit")
    if integrity_result["findings"]:
        for finding in integrity_result["findings"]:
            if finding["severity"] in ("CRITICAL", "HIGH"):
                st.error(f"**[{finding['severity']}] {finding['check']}:** {finding['detail']}")
            else:
                st.warning(f"**[{finding['severity']}] {finding['check']}:** {finding['detail']}")
    else:
        st.success("All sample size, subgroup variance, and lineage integrity checks passed.")

    subgroups = release.get("evaluation_metadata", {}).get("subgroups", {})
    if subgroups:
        st.markdown("#### Subgroup Performance Breakdown (%)")
        sg_df = pd.DataFrame({
            "Cohort / Slice": list(subgroups.keys()),
            "Score (%)": list(subgroups.values()),
        })
        st.bar_chart(sg_df.set_index("Cohort / Slice"))

with tab3:
    st.subheader("Governance Sign-Off & Compensating Controls")
    selected_controls = st.multiselect(
        "Select Mandatory Compensating Controls / Mitigations",
        options=tier_cfg.get("compensating_controls", []),
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        decision = st.selectbox(
            "Governance Decision",
            ["APPROVED", "CONDITIONAL_APPROVAL", "REJECTED"],
            index=1 if effective_status != "APPROVED" else 0,
        )
    with c2:
        reviewer = st.text_input("Accountable Reviewer (Name / Role)", value="Sreedhar Kala (AI Governance Lead)")
    with c3:
        waiver_days = st.number_input("Waiver Sunset SLA (Days)", min_value=7, max_value=90, value=30)

    rationale = st.text_area(
        "Audit Rationale & Risk Acceptance Justification",
        placeholder="Document regulatory justification, subgroup mitigation plan, or BaFin/MDR audit notes...",
    )

    if st.button("🔒 Commit Signed Record to SHA-256 Ledger", type="primary"):
        if not rationale.strip():
            st.error("Audit rationale is required before committing to the ledger.")
        else:
            record = append_ledger_entry(
                ledger_path=LEDGER_PATH,
                release=release,
                evaluation=eval_result,
                integrity=integrity_result,
                decision=decision,
                reviewer=reviewer.strip(),
                rationale=rationale.strip(),
                selected_controls=selected_controls,
                waiver_days=int(waiver_days),
            )
            st.success(f"Committed Block #{record['index']} | SHA-256: `{record['entry_hash'][:24]}...`")
            st.rerun()

    st.divider()
    st.subheader("Standardized Model Card Preview")
    mc_markdown = generate_model_card(release, eval_result, selected_controls, rationale)
    st.download_button(
        label="⬇️ Download Model Card (.md)",
        data=mc_markdown,
        file_name=f"{release['release_id']}_ModelCard.md",
        mime="text/markdown",
    )
    with st.expander("View Generated Model Card"):
        st.markdown(mc_markdown)

with tab4:
    st.subheader("Cryptographic Hash-Chained Audit Ledger")
    if not is_chain_valid:
        st.error("CRITICAL AUDIT ALERT: One or more historical records in `data/audit_log.json` have been modified!")
        for alert in tamper_alerts:
            st.write(f"- {alert}")
    else:
        st.success("Cryptographic verification passed: Every block hash and prev_hash pointer is intact.")

    if ledger_entries:
        display_rows = []
        for e in ledger_entries:
            display_rows.append({
                "Block #": e.get("index"),
                "Timestamp (UTC)": e.get("timestamp_utc"),
                "Release": e.get("release_id"),
                "Integrity": e.get("integrity_status"),
                "Decision": e.get("decision"),
                "Waiver Expires": e.get("waiver_expires_utc") or "N/A",
                "Reviewer": e.get("reviewer"),
                "Entry Hash": str(e.get("entry_hash", ""))[:16] + "...",
                "Prev Hash": str(e.get("prev_hash", ""))[:16] + "...",
            })
        st.dataframe(pd.DataFrame(display_rows), use_container_width=True, hide_index=True)
    else:
        st.info("No ledger blocks committed yet. Record a sign-off in Tab 3 to create Genesis Block #1.")