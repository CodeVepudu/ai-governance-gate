import hashlib
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, List, Tuple

GENESIS_HASH = "0" * 64


def _compute_entry_hash(entry_without_hash: Dict[str, Any]) -> str:
    """Computes a deterministic SHA-256 digest over canonical JSON."""
    canonical = json.dumps(entry_without_hash, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def load_ledger(ledger_path: Path) -> List[Dict[str, Any]]:
    if not ledger_path.exists():
        return []
    try:
        content = ledger_path.read_text(encoding="utf-8").strip()
        if not content:
            return []
        data = json.loads(content)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def append_ledger_entry(
    ledger_path: Path,
    release: Dict[str, Any],
    evaluation: Dict[str, Any],
    integrity: Dict[str, Any],
    decision: str,
    reviewer: str,
    rationale: str,
    selected_controls: List[str],
    waiver_days: int = 30,
) -> Dict[str, Any]:
    """Appends a cryptographically chained audit record with optional waiver expiry."""
    entries = load_ledger(ledger_path)
    prev_hash = entries[-1].get("entry_hash", GENESIS_HASH) if entries else GENESIS_HASH

    now = datetime.now(timezone.utc)
    expires_at = (
        (now + timedelta(days=waiver_days)).isoformat()
        if decision == "CONDITIONAL_APPROVAL"
        else None
    )

    # Fingerprint the exact release telemetry and rules evaluated
    evidence_fingerprint = hashlib.sha256(
        json.dumps(
            {
                "release_id": release.get("release_id"),
                "version": release.get("version"),
                "metrics": release.get("metrics"),
                "evaluation_metadata": release.get("evaluation_metadata"),
            },
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()

    record: Dict[str, Any] = {
        "index": len(entries) + 1,
        "timestamp_utc": now.isoformat(),
        "prev_hash": prev_hash,
        "evidence_sha256": evidence_fingerprint,
        "release_id": release.get("release_id"),
        "model_name": release.get("model_name"),
        "version": release.get("version"),
        "risk_tier": release.get("risk_tier"),
        "baseline_gate_status": evaluation.get("status"),
        "integrity_status": integrity.get("integrity_status"),
        "risk_score": evaluation.get("risk_score"),
        "decision": decision,
        "reviewer": reviewer,
        "rationale": rationale,
        "compensating_controls": selected_controls,
        "waiver_expires_utc": expires_at,
    }

    record["entry_hash"] = _compute_entry_hash(record)
    entries.append(record)

    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_text(json.dumps(entries, indent=2), encoding="utf-8")
    return record


def verify_ledger_integrity(entries: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
    """
    Verifies every block's SHA-256 hash and prev_hash linkage.
    Returns (is_valid, list_of_tamper_alerts).
    """
    if not entries:
        return True, []

    alerts: List[str] = []
    expected_prev = GENESIS_HASH

    for idx, entry in enumerate(entries):
        recorded_hash = entry.get("entry_hash")
        if not recorded_hash:
            alerts.append(f"Entry #{idx + 1}: Legacy unhashed record detected (missing entry_hash).")
            continue

        if entry.get("prev_hash") != expected_prev:
            alerts.append(
                f"Entry #{idx + 1} ({entry.get('release_id')}): Broken chain link! "
                f"Expected prev_hash {expected_prev[:12]}..., found {str(entry.get('prev_hash'))[:12]}..."
            )

        copy_for_hash = {k: v for k, v in entry.items() if k != "entry_hash"}
        recomputed = _compute_entry_hash(copy_for_hash)
        if recomputed != recorded_hash:
            alerts.append(
                f"Entry #{idx + 1} ({entry.get('release_id')}): TAMPER DETECTED! "
                f"Stored hash {recorded_hash[:12]}... does not match recomputed digest {recomputed[:12]}..."
            )

        expected_prev = recorded_hash

    return len(alerts) == 0, alerts