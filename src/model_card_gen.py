from datetime import datetime, timezone
from typing import Any


def generate_model_card(
    release: dict[str, Any],
    evaluation: dict[str, Any],
    selected_controls: list[str],
    latest_decision: str | None = None,
) -> str:
    effective_status = latest_decision or evaluation["status"]
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    metric_rows = []
    for item in evaluation["evaluations"]:
        outcome = "PASS" if item["passed"] else "GAP"
        metric_rows.append(
            f"| {item['metric_label']} | {item['actual']:.1f}% | {item['threshold']:.1f}% | "
            f"{item['delta']:+.1f} | {outcome} | {item['framework']} |"
        )

    controls_section = (
        "\n".join(f"- {ctrl}" for ctrl in selected_controls)
        if selected_controls
        else "- None recorded"
    )

    return f"""# Model Card: {release['model_name']}

- **Release ID:** `{release['release_id']}`
- **Owner Team:** {release['owner_team']}
- **Risk Tier:** {evaluation['tier_label']}
- **Computed Risk Score:** {evaluation['risk_score']} / 100
- **Governance Status:** **{effective_status}**
- **Generated:** {generated_at}

## Model & Data Summary
- **Architecture:** {release['model_architecture']}
- **Training Data Summary:** {release['training_data_summary']}
- **Risk Tier Scope:** {evaluation['tier_description']}

## Evaluation & Regulatory Mapping
| Metric | Actual | Threshold | Delta | Status | Mapped Framework |
| :--- | :---: | :---: | :---: | :---: | :--- |
{chr(10).join(metric_rows)}

## Compensating Controls & Mitigations
{controls_section}

## Known Limitations
{release['known_limitations']}
"""