from typing import Dict, Any, List


def audit_evaluation_integrity(release: Dict[str, Any], tier_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Audits evaluation metadata to detect 'paper compliance' before trusting top-line metrics:
    1. Minimum statistical sample size check
    2. Worst-slice subgroup collapse detection against aggregate demographic parity
    3. Suspicious ceiling / identical metric anomaly check
    """
    metadata = release.get("evaluation_metadata", {})
    metrics = release.get("metrics", {})
    findings: List[Dict[str, str]] = []

    min_samples = tier_config.get("min_sample_size", 1000)
    actual_samples = metadata.get("validation_sample_size", 0)

    # 1. Sample Size Check
    if actual_samples < min_samples:
        findings.append({
            "severity": "HIGH",
            "check": "Statistical Sample Size",
            "detail": (
                f"Validation sample size ({actual_samples:,}) is below the required minimum "
                f"({min_samples:,}) for {tier_config.get('label', 'this tier')}."
            ),
        })

    # 2. Subgroup Collapse Check
    subgroups = metadata.get("subgroups", {})
    aggregate_parity = metrics.get("demographic_parity", 100.0)
    max_allowed_drop = tier_config.get("max_subgroup_drop", 3.0)

    worst_group = None
    worst_score = None
    if subgroups:
        worst_group = min(subgroups, key=subgroups.get)
        worst_score = subgroups[worst_group]
        drop = round(aggregate_parity - worst_score, 2)

        if drop > max_allowed_drop:
            findings.append({
                "severity": "CRITICAL",
                "check": "Subgroup Slice Collapse",
                "detail": (
                    f"Aggregate demographic parity is {aggregate_parity}%, but cohort '{worst_group}' "
                    f"scored {worst_score}% (a {drop}% drop, exceeding the {max_allowed_drop}% max variance)."
                ),
            })

    # 3. Metric Gaming / Suspicious Uniformity Check
    metric_values = list(metrics.values())
    if len(metric_values) >= 3 and len(set(metric_values)) == 1:
        findings.append({
            "severity": "MEDIUM",
            "check": "Metric Uniformity Anomaly",
            "detail": "All reported evaluation metrics share an identical value; verify raw test logs.",
        })

    # 4. Dataset Lineage Hash Presence
    if not metadata.get("dataset_hash"):
        findings.append({
            "severity": "HIGH",
            "check": "Missing Dataset Lineage Hash",
            "detail": "No cryptographic dataset fingerprint provided for reproducibility.",
        })

    has_critical = any(f["severity"] == "CRITICAL" for f in findings)
    has_high = any(f["severity"] == "HIGH" for f in findings)

    if has_critical or has_high:
        integrity_status = "FAILED_INTEGRITY"
    elif findings:
        integrity_status = "WARNING"
    else:
        integrity_status = "VERIFIED"

    return {
        "integrity_status": integrity_status,
        "sample_size": actual_samples,
        "min_sample_size": min_samples,
        "worst_subgroup": worst_group,
        "worst_subgroup_score": worst_score,
        "findings": findings,
    }