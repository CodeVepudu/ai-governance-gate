from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any
import yaml


BASE_DIR = Path(__file__).resolve().parent.parent
RULES_PATH = BASE_DIR / "config" / "governance_rules.yaml"
RELEASES_PATH = BASE_DIR / "data" / "sample_releases.json"
AUDIT_LOG_PATH = BASE_DIR / "data" / "audit_log.json"

METRIC_LABELS = {
    "jailbreak_resistance": "Jailbreak Resistance (%)",
    "pii_leakage_prevention": "PII Leakage Prevention (%)",
    "demographic_parity": "Demographic Parity (%)",
    "audit_logging_coverage": "Audit Logging Coverage (%)",
}


def load_rules() -> dict[str, Any]:
    with open(RULES_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_releases() -> list[dict[str, Any]]:
    with open(RELEASES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_audit_log() -> list[dict[str, Any]]:
    if not AUDIT_LOG_PATH.exists():
        return []
    with open(AUDIT_LOG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def evaluate_release(release: dict[str, Any], rules: dict[str, Any]) -> dict[str, Any]:
    tier_key = release["risk_tier"]
    tier_cfg = rules["risk_tiers"][tier_key]
    thresholds = tier_cfg["thresholds"]
    reg_map = rules["regulatory_mapping"]
    metrics = release["metrics"]

    evaluations = []
    gaps_count = 0
    weighted_gap_penalty = 0.0

    for metric_key, threshold_val in thresholds.items():
        actual_val = float(metrics.get(metric_key, 0.0))
        passed = actual_val >= float(threshold_val)
        delta = round(actual_val - float(threshold_val), 2)

        if not passed:
            gaps_count += 1
            weighted_gap_penalty += abs(delta) * 4.0

        reg_info = reg_map.get(metric_key, {})
        evaluations.append({
            "metric_key": metric_key,
            "metric_label": METRIC_LABELS.get(metric_key, metric_key),
            "actual": actual_val,
            "threshold": float(threshold_val),
            "delta": delta,
            "passed": passed,
            "framework": reg_info.get("framework", "Internal Standard"),
            "requirement": reg_info.get("requirement", ""),
        })

    base_score = 75.0 if tier_key == "high_risk" else 30.0
    risk_score = round(min(100.0, max(5.0, base_score + weighted_gap_penalty - (4 - gaps_count) * 4.0)), 1)

    if gaps_count == 0:
        status = "APPROVED"
    elif tier_key == "high_risk" and weighted_gap_penalty >= 25.0:
        status = "BLOCKED"
    else:
        status = "CONDITIONAL_HOLD"

    return {
        "tier_key": tier_key,
        "tier_label": tier_cfg["label"],
        "tier_description": tier_cfg["description"],
        "requires_human_signoff": tier_cfg["requires_human_signoff"],
        "compensating_controls": tier_cfg["compensating_controls"],
        "evaluations": evaluations,
        "gaps_count": gaps_count,
        "risk_score": risk_score,
        "status": status,
    }


def record_decision(
    release: dict[str, Any],
    decision_type: str,
    reviewer_name: str,
    rationale: str,
    selected_controls: list[str],
) -> dict[str, Any]:
    entries = load_audit_log()
    record = {
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "release_id": release["release_id"],
        "model_name": release["model_name"],
        "risk_tier": release["risk_tier"],
        "decision": decision_type,
        "reviewer": reviewer_name.strip() or "Unlisted Reviewer",
        "rationale": rationale.strip() or "No rationale provided.",
        "compensating_controls": selected_controls,
    }
    entries.insert(0, record)
    with open(AUDIT_LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2)
    return record