"""Bounded agent change brief from explicit graph seeds (task 306).

Composes impact / impact_modules / architecture-rules factories — no new traversal, no LLM.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from code_atlas.config import Config
from code_atlas.tokens import estimate_tokens
from code_atlas.tools import check_architecture_rules, impact, impact_modules

# Measured ceiling for the Markdown brief (fixture + sample reporter pin this).
DEFAULT_BRIEF_TOKEN_CEILING = 800

TIER_RANK = {"RESOLVED": 0, "HEURISTIC": 1, "DYNAMIC": 2}

# Pinned synthetic sample for the committed token reporter (not a repo name — graph-shaped only).
PINNED_BRIEF_SAMPLE: dict[str, object] = {
    "base": "pinned-base",
    "head": "pinned-head",
    "paths": ["src/a.aa", "src/b.aa"],
    "qnames": [],
    "impact": {
        "claim": "subject=src/a.aa,src/b.aa question=impact answer=3",
        "results": [
            {
                "qname": "\\A",
                "file": "src/a.aa",
                "confidence_tier": "RESOLVED",
                "score": 1.0,
            },
            {
                "qname": "\\B",
                "file": "src/b.aa",
                "confidence_tier": "HEURISTIC",
                "score": 0.5,
            },
        ],
    },
    "impact_modules": {
        "results": [
            {
                "module": "src",
                "symbols": 2,
                "assigned": True,
                "exemplar": "src/a.aa:1",
            }
        ],
        "note": "pinned sample note",
    },
    "architecture_rules": {
        "results": [
            {
                "rule_id": "a-must-not-b",
                "source_file": "src/a.aa",
                "forbidden_file": "src/b.aa",
                "confidence_tier": "RESOLVED",
            }
        ],
        "candidates": [],
    },
    "ranked_impact": [],
    "modules": [],
    "confirmed_rules": [],
    "candidate_rules": [],
    "caveats": ["pinned:note=sample"],
    "token_ceiling": DEFAULT_BRIEF_TOKEN_CEILING,
}


def report_token_ceiling(
    *,
    sections: Mapping[str, object] | None = None,
    sample: str = "pinned",
) -> dict[str, object]:
    """Committed reporter: tokens vs ceiling for fixture sections or the pinned sample."""
    label = "fixture"
    if sections is None:
        if sample != "pinned":
            raise ValueError(f"unknown sample {sample!r}")
        label = "pinned"
        payload: dict[str, object] = dict(PINNED_BRIEF_SAMPLE)
        impact = payload["impact"]
        assert isinstance(impact, Mapping)
        ranked = _rank_impact_rows(
            [r for r in _as_list(impact.get("results")) if isinstance(r, Mapping)]
        )
        payload["ranked_impact"] = ranked
        modules_payload = payload["impact_modules"]
        assert isinstance(modules_payload, Mapping)
        payload["modules"] = _as_list(modules_payload.get("results"))
        rules_payload = payload["architecture_rules"]
        assert isinstance(rules_payload, Mapping)
        payload["confirmed_rules"] = _as_list(rules_payload.get("results"))
        sections = payload
    text = render_brief(sections)
    body = text.split("<!--")[0]
    tokens = estimate_tokens(body)
    ceiling = sections.get("token_ceiling")
    if not isinstance(ceiling, int):
        ceiling = DEFAULT_BRIEF_TOKEN_CEILING
    return {
        "sample": label,
        "tokens": tokens,
        "ceiling": ceiling,
        "truncated": "truncated:true" in text,
        "within_ceiling": tokens <= ceiling,
    }


def _as_list(value: object) -> list[object]:
    return list(value) if isinstance(value, list) else []


def build_brief_sections(
    config: Config,
    *,
    paths: Sequence[str] | None = None,
    qnames: Sequence[str] | None = None,
    base: str | None = None,
    head: str | None = None,
    token_ceiling: int = DEFAULT_BRIEF_TOKEN_CEILING,
) -> dict[str, object]:
    """Collect ranked sections from existing tools. Pure composition."""
    path_list = list(paths) if paths else None
    qname_list = list(qnames) if qnames else None
    impact_payload = impact.create(config)(paths=path_list, qnames=qname_list, sign=True)
    modules_payload = impact_modules.create(config)(paths=path_list, qnames=qname_list, sign=True)
    rules_payload = check_architecture_rules.create(config)()

    rows = [r for r in _as_list(impact_payload.get("results")) if isinstance(r, Mapping)]
    ranked = _rank_impact_rows(rows)  # type: ignore[arg-type]
    modules = _as_list(modules_payload.get("results"))
    confirmed = _as_list(rules_payload.get("results"))
    candidates = _as_list(rules_payload.get("candidates"))

    caveats = _compose_caveats(impact_payload, modules_payload, rules_payload)
    return {
        "base": base,
        "head": head,
        "paths": path_list or [],
        "qnames": qname_list or [],
        "impact": impact_payload,
        "impact_modules": modules_payload,
        "architecture_rules": rules_payload,
        "ranked_impact": ranked,
        "modules": modules,
        "confirmed_rules": confirmed,
        "candidate_rules": candidates,
        "caveats": caveats,
        "token_ceiling": token_ceiling,
    }


def render_brief(sections: Mapping[str, object]) -> str:
    """Markdown brief: rank before truncate; state what each cap removed."""
    raw_ceiling = sections.get("token_ceiling")
    ceiling = raw_ceiling if isinstance(raw_ceiling, int) else DEFAULT_BRIEF_TOKEN_CEILING
    lines: list[str] = [
        "# Agent change brief",
        "",
        f"- base: `{sections.get('base')}`",
        f"- head: `{sections.get('head')}`",
        f"- paths: `{sections.get('paths')}`",
        f"- qnames: `{sections.get('qnames')}`",
        f"- token_ceiling: `{ceiling}`",
        "",
    ]
    impact_payload = sections.get("impact")
    if isinstance(impact_payload, Mapping) and impact_payload.get("claim"):
        lines.append("## Change identity")
        lines.append("")
        lines.append(f"- claim: `{impact_payload['claim']}`")
        lines.append("")

    ranked = _as_list(sections.get("ranked_impact"))
    lines.append("## Likely blast radius (strongest first)")
    lines.append("")
    kept, removed = _cap_rows(ranked, max_rows=12)
    if not kept:
        lines.append("_No walkable seeds — see caveats._")
    else:
        for row in kept:
            if isinstance(row, Mapping):
                lines.append(
                    f"- `{row.get('qname') or row.get('qualified_name')}` "
                    f"tier=`{row.get('confidence_tier')}` "
                    f"file=`{row.get('file') or row.get('file_path')}`"
                )
    if removed:
        lines.append(
            f"- _cap removed {removed} lower-ranked row(s) from blast radius_"
        )
    lines.append("")

    lines.append("## Affected modules")
    lines.append("")
    modules = _as_list(sections.get("modules"))
    kept_m, removed_m = _cap_rows(modules, max_rows=8)
    if not kept_m:
        lines.append("_No module rollup — see caveats._")
    else:
        for row in kept_m:
            if isinstance(row, Mapping):
                lines.append(
                    f"- `{row.get('module')}` symbols=`{row.get('symbols')}` "
                    f"assigned=`{row.get('assigned')}`"
                )
    if removed_m:
        lines.append(f"- _cap removed {removed_m} module row(s)_")
    lines.append("")

    lines.append("## Confirmed architecture rules")
    lines.append("")
    confirmed = _as_list(sections.get("confirmed_rules"))
    if not confirmed:
        lines.append("_None confirmed._")
    else:
        for row in confirmed:
            if isinstance(row, Mapping):
                lines.append(
                    f"- `{row.get('rule_id')}`: "
                    f"{row.get('source_file')} -> {row.get('forbidden_file')} "
                    f"({row.get('confidence_tier')})"
                )
    lines.append("")

    lines.append("## Suggested first files")
    lines.append("")
    suggestions = _suggest_files(
        [r for r in ranked if isinstance(r, Mapping)],  # type: ignore[list-item]
        [r for r in modules if isinstance(r, Mapping)],  # type: ignore[list-item]
    )
    if not suggestions:
        lines.append("_No ranked file suggestion — seeds may be missing._")
    else:
        for path, why in suggestions:
            lines.append(f"- `{path}` — {why}")
    lines.append("")

    lines.append("## Caveats")
    lines.append("")
    caveats = _as_list(sections.get("caveats"))
    if not caveats:
        lines.append("_None._")
    else:
        for caveat in caveats:
            lines.append(f"- {caveat}")
    lines.append("")

    text = "\n".join(lines)
    tokens = estimate_tokens(text)
    if tokens <= ceiling:
        return text + f"<!-- tokens:{tokens} ceiling:{ceiling} -->\n"

    truncated = _truncate_to_ceiling(text, ceiling)
    return truncated


def _rank_impact_rows(rows: Sequence[Mapping[str, object] | Any]) -> list[dict[str, object]]:
    """RESOLVED before HEURISTIC; stable secondary by qname."""
    shaped: list[dict[str, object]] = []
    for row in rows:
        if isinstance(row, Mapping):
            shaped.append(dict(row))
    shaped.sort(
        key=lambda r: (
            TIER_RANK.get(str(r.get("confidence_tier") or "HEURISTIC"), 9),
            str(r.get("qname") or r.get("qualified_name") or ""),
        )
    )
    return shaped


def _cap_rows(
    rows: Sequence[object], *, max_rows: int
) -> tuple[list[object], int]:
    if len(rows) <= max_rows:
        return list(rows), 0
    return list(rows[:max_rows]), len(rows) - max_rows


def _suggest_files(
    ranked: Sequence[Mapping[str, object]],
    modules: Sequence[Mapping[str, object]],
) -> list[tuple[str, str]]:
    """Suggest files from graph ranks only — never hard-coded repo/framework names."""
    seen: set[str] = set()
    out: list[tuple[str, str]] = []
    for row in ranked:
        path = str(row.get("file") or row.get("file_path") or "")
        if not path or path in seen:
            continue
        tier = str(row.get("confidence_tier") or "")
        if tier != "RESOLVED" and out:
            continue
        seen.add(path)
        out.append((path, f"ranked blast-radius hit ({tier})"))
        if len(out) >= 5:
            break
    for row in modules:
        if not isinstance(row, Mapping):
            continue
        exemplar = str(row.get("exemplar") or "")
        path = exemplar.split(":")[0] if exemplar else str(
            row.get("primary_file") or row.get("file") or ""
        )
        if path and path not in seen:
            seen.add(path)
            out.append((path, f"module rollup `{row.get('module')}`"))
        if len(out) >= 5:
            break
    return out


def _compose_caveats(
    impact_payload: Mapping[str, object],
    modules_payload: Mapping[str, object],
    rules_payload: Mapping[str, object],
) -> list[str]:
    caveats: list[str] = []
    for label, payload in (
        ("impact", impact_payload),
        ("impact_modules", modules_payload),
        ("architecture_rules", rules_payload),
    ):
        reason = payload.get("reason")
        if reason and reason not in {"ok", "no_matches"}:
            caveats.append(f"{label}:reason={reason}")
        if payload.get("truncated") or payload.get("walk_truncated"):
            caveats.append(f"{label}:truncated")
        if payload.get("module_table_truncated"):
            caveats.append(f"{label}:module_table_truncated")
        staleness = payload.get("staleness")
        if staleness and staleness != "current":
            caveats.append(f"{label}:staleness={staleness}")
        note = payload.get("note")
        if isinstance(note, str) and note:
            caveats.append(f"{label}:note={note}")
        for note_key in ("notes", "message"):
            extra = payload.get(note_key)
            if isinstance(extra, str) and extra:
                caveats.append(f"{label}:{note_key}={extra}")
            elif isinstance(extra, list):
                for item in extra:
                    caveats.append(f"{label}:{item}")
    if not (impact_payload.get("results") or []):
        dropped = impact_payload.get("seeds_dropped")
        if isinstance(dropped, int) and dropped > 0:
            caveats.append("impact:seeds_dropped — missing or unindexed roots")
    return caveats


def _truncate_to_ceiling(text: str, ceiling: int) -> str:
    lines = text.splitlines()
    # Drop blast-radius bullets from the bottom until under ceiling; always keep header+caveats.
    caveats_idx = next((i for i, ln in enumerate(lines) if ln == "## Caveats"), len(lines))
    body = lines[:caveats_idx]
    tail = lines[caveats_idx:]
    note = "- _additional blast-radius rows removed to meet token_ceiling_"
    while body and estimate_tokens("\n".join(body + tail) + "\n") > ceiling:
        # Drop the lowest-ranked blast-radius row, leaving one note in its place (rank-then-cap).
        drop_at = None
        for i in range(len(body) - 1, -1, -1):
            if body[i].startswith("- `") and "tier=" in body[i]:
                drop_at = i
                break
        if drop_at is None:
            break
        body.pop(drop_at)
        if note not in body:
            body.insert(drop_at, note)
    out = "\n".join(body + tail) + "\n"
    tokens = estimate_tokens(out)
    return out + f"<!-- tokens:{tokens} ceiling:{ceiling} truncated:true -->\n"
