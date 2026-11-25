import pandas as pd
import streamlit as st

from src.engine import (
    evaluate_release,
    load_audit_log,
    load_releases,
    load_rules,
    record_decision,
)
from src.model_card_gen import generate_model_card

st.set_page_config(
    page_title="AI Launch Gate & Compliance Engine",
    layout="wide",
)

rules = load_rules()
releases = load_releases()

st.title("AI Launch Gate & Compliance Engine")
st.caption("Bridging engineering telemetry, regulatory obligations, and executive risk sign-offs")

# Sidebar: Intake & Triage
st.sidebar.header("Release Intake")
release_options = {
    f"{r['release_id']} — {r['model_name']}": r for r in releases
}
selected_label = st.sidebar.selectbox(
    "Select Model Release",
    options=list(release_options.keys()),
)
release = release_options[selected_label]
evaluation = evaluate_release(release, rules)

st.sidebar.divider()
st.sidebar.subheader("Risk Classification")
st.sidebar.write(f"**Tier:** {evaluation['tier_label']}")
st.sidebar.write(evaluation["tier_description"])
st.sidebar.write(
    f"**Human Sign-Off Required:** {'Yes' if evaluation['requires_human_signoff'] else 'No'}"
)

# Top KPI Strip
col1, col2, col3, col4 = st.columns(4)
col1.metric("Governance Status", evaluation["status"])
col2.metric("Risk Score", f"{evaluation['risk_score']} / 100")
col3.metric("Threshold Gaps", evaluation["gaps_count"])
col4.metric("Owner Team", release["owner_team"])

st.divider()

# Main Split View: Engineering Metrics vs. Regulatory Mapping
left_col, right_col = st.columns(2)

with left_col:
    st.subheader("Engineering Evaluation vs. Thresholds")
    metrics_df = pd.DataFrame(
        [
            {
                "Metric": item["metric_label"],
                "Actual (%)": item["actual"],
                "Threshold (%)": item["threshold"],
                "Delta": item["delta"],
                "Result": "PASS" if item["passed"] else "GAP",
            }
            for item in evaluation["evaluations"]
        ]
    )
    st.dataframe(metrics_df, use_container_width=True, hide_index=True)

    chart_df = metrics_df.set_index("Metric")[["Actual (%)", "Threshold (%)"]]
    st.bar_chart(chart_df)

with right_col:
    st.subheader("Regulatory & Framework Mapping")
    for item in evaluation["evaluations"]:
        badge = "PASS" if item["passed"] else "GAP DETECTED"
        with st.container(border=True):
            st.markdown(f"**{item['metric_label']}** — `{badge}`")
            st.write(f"**Framework:** {item['framework']}")
            st.write(f"**Obligation:** {item['requirement']}")

st.divider()

# Compensating Controls, Sign-Off & Model Card
st.subheader("Compensating Controls & Governance Decision")
selected_controls = st.multiselect(
    "Select Compensating Controls / Mitigations",
    options=evaluation["compensating_controls"],
)

with st.form("decision_form"):
    decision_type = st.selectbox(
        "Governance Decision",
        options=[
            "Approved",
            "Approved with Compensating Controls",
            "Hold / Remediation Required",
            "Blocked",
        ],
    )
    reviewer_name = st.text_input("Reviewer Name & Role (e.g., Governance Lead / Legal)")
    rationale = st.text_area("Decision Rationale & Conditions")
    submitted = st.form_submit_button("Record Governance Decision")

if submitted:
    saved = record_decision(
        release=release,
        decision_type=decision_type,
        reviewer_name=reviewer_name,
        rationale=rationale,
        selected_controls=selected_controls,
    )
    st.success(f"Recorded `{saved['decision']}` for {saved['release_id']} at {saved['timestamp_utc']}.")

st.subheader("Generated Model Card Preview")
model_card_md = generate_model_card(
    release=release,
    evaluation=evaluation,
    selected_controls=selected_controls,
)
st.markdown(model_card_md)
st.download_button(
    label="Download Model Card (.md)",
    data=model_card_md,
    file_name=f"{release['release_id'].lower()}_model_card.md",
    mime="text/markdown",
)

st.divider()

# Audit Log
st.subheader("Audit Trail (Persisted Sign-Offs)")
audit_entries = load_audit_log()
if audit_entries:
    st.dataframe(pd.DataFrame(audit_entries), use_container_width=True, hide_index=True)
else:
    st.info("No governance decisions recorded yet.")