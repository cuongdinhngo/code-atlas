"""Versioned Change Assurance evidence bundle — portable wrap of a 303 check result (task 305).

``EVIDENCE_BUNDLE_VERSION`` versions this document only (R3.5). Writer/renderer never query the
graph; they wrap a result object already produced by ``code_atlas.check``.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

from code_atlas.build_info import server_provenance
from code_atlas.config import Config
from code_atlas.tools.nav_result import REASON_OK

# Bump only when this document's shape moves — not CONTRACT/DATASET/ARTIFACT (R3.5).
EVIDENCE_BUNDLE_VERSION = 1

REASON_UNSUPPORTED_VERSION = "unsupported_bundle_version"
REASON_MALFORMED = "malformed_bundle"
REASON_CROSS_REPOSITORY = "cross_repository_bundle"
REASON_CAVEAT_DROPPED = "caveat_not_attested"


def wrap_check_result(
    check_result: Mapping[str, object],
    config: Config,
    *,
    graph_completeness: str | None = None,
) -> dict[str, object]:
    """Wrap a 303 result in the versioned bundle schema. No graph I/O."""
    provenance = server_provenance()
    raw_caveats = check_result.get("caveats")
    caveats = list(raw_caveats) if isinstance(raw_caveats, list) else []
    completeness = graph_completeness
    if completeness is None:
        impact = check_result.get("impact")
        if isinstance(impact, Mapping) and impact.get("staleness"):
            completeness = str(impact["staleness"])
        else:
            completeness = "unknown"
    return {
        "base": check_result.get("base"),
        "bundle_version": EVIDENCE_BUNDLE_VERSION,
        "candidate_count": check_result.get("candidate_count"),
        "caveats": caveats,
        "check": dict(check_result),
        "claims": _collect_claims(check_result),
        "confidence": _collect_confidence(check_result),
        "config_build": config.identity,
        "confirmed_count": check_result.get("confirmed_count"),
        "graph_completeness": completeness,
        "head": check_result.get("head"),
        "head_ref": check_result.get("head_ref"),
        "index_root": config.index_root,
        "mode": check_result.get("mode"),
        "reason": check_result.get("reason"),
        "server": {
            "package_version": provenance.get("server_version"),
            "server_build": provenance.get("server_build"),
            "server_build_kind": provenance.get("server_build_kind"),
        },
        "truncation": _collect_truncation(check_result),
    }


def _collect_claims(check_result: Mapping[str, object]) -> list[str]:
    """Every signed claim string present in the 303 result."""
    found: list[str] = []
    impact = check_result.get("impact")
    if isinstance(impact, Mapping) and impact.get("claim"):
        found.append(str(impact["claim"]))
    return found


def _collect_confidence(check_result: Mapping[str, object]) -> dict[str, object]:
    """Named confidence summary — confirmed RESOLVED vs HEURISTIC candidates."""
    rules = check_result.get("architecture_rules")
    tiers: dict[str, int] = {}
    if isinstance(rules, Mapping):
        for row in rules.get("results") or []:
            if isinstance(row, Mapping):
                tier = str(row.get("confidence_tier") or "RESOLVED")
                tiers[tier] = tiers.get(tier, 0) + 1
        for row in rules.get("candidates") or []:
            if isinstance(row, Mapping):
                tier = str(row.get("confidence_tier") or "HEURISTIC")
                tiers[tier] = tiers.get(tier, 0) + 1
    return {
        "confirmed_count": check_result.get("confirmed_count"),
        "candidate_count": check_result.get("candidate_count"),
        "tiers": dict(sorted(tiers.items())),
    }


def _collect_truncation(check_result: Mapping[str, object]) -> dict[str, bool]:
    """Named truncation flags from each evidence section."""
    out: dict[str, bool] = {}
    for label in ("impact", "architecture_rules", "architecture_diff"):
        section = check_result.get(label)
        out[label] = bool(isinstance(section, Mapping) and section.get("truncated"))
    return out


def _named_bullets(label: str, section: object) -> list[str]:
    """A mapping section as nested bullets — the same names the JSON carries."""
    if not isinstance(section, Mapping):
        return [f"- {label}: `{section}`"]
    rows = [f"- {label}:"]
    for key, value in section.items():
        rows.append(f"  - {key}: `{value}`")
    return rows


def render_json(bundle: Mapping[str, object]) -> str:
    """Deterministic canonical JSON (R4.2)."""
    return json.dumps(bundle, sort_keys=True, ensure_ascii=False, indent=2) + "\n"


def render_markdown(bundle: Mapping[str, object]) -> str:
    """Markdown view of the same schema — every caveat must appear or attestation is refused."""
    caveats = bundle.get("caveats")
    if not isinstance(caveats, list):
        return (
            "# Change Assurance evidence — refused\n\n"
            f"- reason: `{REASON_CAVEAT_DROPPED}`\n"
            "- caveats field is not a list; Markdown will not attest this bundle.\n"
        )
    lines = [
        "# Change Assurance evidence bundle",
        "",
        f"- bundle_version: `{bundle.get('bundle_version')}`",
        f"- index_root: `{bundle.get('index_root')}`",
        f"- base: `{bundle.get('base')}`",
        f"- head: `{bundle.get('head')}` ({bundle.get('head_ref')})",
        f"- mode: `{bundle.get('mode')}`",
        f"- reason: `{bundle.get('reason')}`",
        f"- confirmed_count: `{bundle.get('confirmed_count')}`",
        f"- candidate_count: `{bundle.get('candidate_count')}`",
        f"- graph_completeness: `{bundle.get('graph_completeness')}`",
        f"- config_build: `{bundle.get('config_build')}`",
    ]
    lines.extend(_named_bullets("confidence", bundle.get("confidence")))
    lines.extend(_named_bullets("truncation", bundle.get("truncation")))
    claims = bundle.get("claims")
    if isinstance(claims, list) and claims:
        lines.append("- claims:")
        lines.extend(f"  - `{claim}`" for claim in claims)
    else:
        lines.append("- claims: _none signed._")
    server = bundle.get("server")
    if isinstance(server, Mapping):
        lines.append(f"- server_build: `{server.get('server_build')}`")
        lines.append(f"- package_version: `{server.get('package_version')}`")
    lines.append("")
    lines.append("## Caveats")
    lines.append("")
    if not caveats:
        lines.append("_None._")
    else:
        for caveat in caveats:
            lines.append(f"- {caveat}")
    lines.append("")
    check = bundle.get("check")
    if isinstance(check, Mapping):
        brief = check.get("agent_brief")
        if isinstance(brief, str) and brief.strip():
            lines.append("## Agent change brief")
            lines.append("")
            lines.append(brief.rstrip())
            lines.append("")
        lines.append("## Check summary")
        lines.append("")
        indexed = check.get("changed_indexed")
        dirty = check.get("dirty_unindexed")
        lines.append(
            f"- changed_indexed: `{len(indexed) if isinstance(indexed, list) else 0}`"
        )
        lines.append(
            f"- dirty_unindexed: `{len(dirty) if isinstance(dirty, list) else 0}`"
        )
        claim = None
        impact = check.get("impact")
        if isinstance(impact, Mapping):
            claim = impact.get("claim")
        if claim:
            lines.append(f"- impact_claim: `{claim}`")
        lines.append("")
    return "\n".join(lines) + "\n"


def write_bundle(
    bundle: Mapping[str, object],
    *,
    json_path: Path | None = None,
    markdown_path: Path | None = None,
) -> tuple[str, ...]:
    """Write only to explicitly selected paths — never a default repo location."""
    written: list[str] = []
    if json_path is not None:
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(render_json(bundle), encoding="utf-8", newline="\n")
        written.append(str(json_path))
    if markdown_path is not None:
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        markdown_path.write_text(render_markdown(bundle), encoding="utf-8", newline="\n")
        written.append(str(markdown_path))
    return tuple(written)


def load_bundle(path: Path) -> dict[str, object]:
    """Load JSON; raise ValueError on non-object root."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"bundle must be a JSON object, got {type(raw).__name__}")
    return raw


def validate_bundle(
    bundle: Mapping[str, object],
    *,
    expected_index_root: str | None = None,
) -> dict[str, object]:
    """Offline validator — refuses unsupported, malformed, or cross-repository bundles."""
    version = bundle.get("bundle_version")
    if not isinstance(version, int):
        return {
            "ok": False,
            "reason": REASON_MALFORMED,
            "message": "bundle_version missing or not an int",
        }
    if version > EVIDENCE_BUNDLE_VERSION:
        return {
            "ok": False,
            "reason": REASON_UNSUPPORTED_VERSION,
            "message": (
                f"bundle_version {version} is newer than supported "
                f"{EVIDENCE_BUNDLE_VERSION} — upgrade the reader"
            ),
            "direction": "newer",
            "bundle_version": version,
            "supported_version": EVIDENCE_BUNDLE_VERSION,
        }
    if version < 1:
        return {
            "ok": False,
            "reason": REASON_MALFORMED,
            "message": f"bundle_version {version} is not a recognised older artifact",
        }
    required = ("index_root", "base", "head", "check", "caveats", "reason", "mode")
    missing = [key for key in required if key not in bundle]
    if missing:
        return {
            "ok": False,
            "reason": REASON_MALFORMED,
            "message": f"missing required fields: {', '.join(missing)}",
        }
    if not isinstance(bundle.get("check"), Mapping):
        return {
            "ok": False,
            "reason": REASON_MALFORMED,
            "message": "check must be an object",
        }
    if not isinstance(bundle.get("caveats"), list):
        return {
            "ok": False,
            "reason": REASON_MALFORMED,
            "message": "caveats must be a list",
        }
    if expected_index_root is not None and bundle.get("index_root") != expected_index_root:
        return {
            "ok": False,
            "reason": REASON_CROSS_REPOSITORY,
            "message": (
                f"bundle index_root={bundle.get('index_root')!r} does not match "
                f"expected {expected_index_root!r}"
            ),
        }
    # Markdown attestation guard: every caveat string must appear in the markdown view.
    md = render_markdown(bundle)
    caveats = bundle["caveats"]
    assert isinstance(caveats, list)
    for caveat in caveats:
        if str(caveat) not in md:
            return {
                "ok": False,
                "reason": REASON_CAVEAT_DROPPED,
                "message": f"caveat not attested in Markdown: {caveat!r}",
            }
    return {
        "ok": True,
        "reason": REASON_OK,
        "bundle_version": version,
        "index_root": bundle.get("index_root"),
    }
