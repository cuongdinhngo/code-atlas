"""The scheduled cross-repo job must be able to launch every adapter its manifest names (issue 285).

Task 150 added three `typescript` samples to `scripts/cross_repo_samples.json`, but
`cross-repo.yml` still installed PHP only. The TS adapter requires `typescript` at startup, so all
three samples failed with `adapter 'typescript' did not announce itself` — a build that never ran,
reported weekly as a validation failure. Nothing connected the manifest to the workflow, so a
manifest row could add a language the job could not run.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.cross_repo_validate import _ADAPTERS

REPO = Path(__file__).resolve().parent.parent
WORKFLOW = REPO / ".github" / "workflows" / "cross-repo.yml"
MANIFEST = REPO / "scripts" / "cross_repo_samples.json"

# What the workflow must contain for an adapter to be launchable — the install of its own runtime
# deps. Data, so adding a language is a row here beside the manifest row (mirrors `_ADAPTERS`).
INSTALL_MARKERS = {
    "php": "--working-dir=adapters/php",
    "typescript": "npm ci --prefix adapters/typescript",
    # Stdlib-only adapter (020/217/227): no package install — the launch env is the proof.
    "python": "CA_PYTHON_CMD",
}


def _manifest_languages() -> set[str]:
    samples = json.loads(MANIFEST.read_text(encoding="utf-8"))["samples"]
    return {str(sample["language"]) for sample in samples}


def test_every_manifest_language_has_a_known_install_marker() -> None:
    """A new language in the manifest must declare how the job installs its adapter."""
    unknown = sorted(_manifest_languages() - set(INSTALL_MARKERS))
    assert unknown == [], (
        f"manifest languages with no install marker: {unknown} — add the install step to "
        f"{WORKFLOW.name} and a row to INSTALL_MARKERS"
    )


def test_every_manifest_language_is_resolvable_by_the_harness() -> None:
    """The harness must know an adapter command for each language the manifest names."""
    unresolvable = sorted(_manifest_languages() - set(_ADAPTERS))
    assert unresolvable == [], unresolvable


@pytest.mark.parametrize("language", sorted(_manifest_languages()))
def test_the_workflow_installs_the_adapter_for_each_language(language: str) -> None:
    """Proving test (issue 285): the job installs every adapter its samples need.

    Red before the fix: `typescript` was in the manifest and no `npm ci` was in the workflow.
    """
    workflow = WORKFLOW.read_text(encoding="utf-8")
    marker = INSTALL_MARKERS[language]
    assert marker in workflow, (
        f"cross-repo.yml runs {language} samples but never installs that adapter "
        f"(no {marker!r}) — the adapter exits before announcing itself"
    )
