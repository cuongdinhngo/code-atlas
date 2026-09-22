"""Task 263 — capability table never empty: toml → structural → entry → explained refusal."""

from __future__ import annotations

from pathlib import Path

from code_atlas.onboarding.capabilities import (
    EMPTY_REASON,
    SOURCE_EMPTY,
    SOURCE_ENTRY,
    SOURCE_STRUCTURAL,
    SOURCE_TOML,
    resolve_capability_map,
)
from code_atlas.onboarding.modules import find_business_modules


def _four_layout() -> list[str]:
    return [
        f"app/application/{name}/f{i}.x"
        for name in ("billing", "audit", "roster", "catering")
        for i in range(4)
    ]


def test_pinned_sample_without_toml_uses_entry_rows_not_empty_table() -> None:
    """AC: no toml + no structural modules → entry rows from CA_ENTRY_POINTS."""
    paths = [f"public/screen_{i}.php" for i in range(3)] + ["lib/util.php"]
    result = resolve_capability_map(
        paths,
        class_counts={p: 0 for p in paths},
        fan_in={p: 0 for p in paths},
        limit=50,
        declared_entry_points=("public/**",),
        outbound={"public/screen_0.php": ("lib/util.php",)},
    )
    assert result.source == SOURCE_ENTRY
    assert result.modules
    assert all(row.hub.startswith("public/") for row in result.modules)
    assert "- (no capability layout found)" not in str(result.as_dict())


def test_capabilities_toml_names_source_and_human_labels(tmp_path: Path) -> None:
    """AC: toml present → source capabilities_toml; rows carry human names."""
    cap = tmp_path / "docs" / "onboarding"
    cap.mkdir(parents=True)
    (cap / "capabilities.toml").write_text(
        '[[capability]]\nname = "billing"\npaths = ["app/billing/**"]\n'
        '[[capability]]\nname = "login"\npaths = ["app/login/**"]\n',
        encoding="utf-8",
    )
    paths = [
        "app/billing/Pay.php",
        "app/billing/Invoice.php",
        "app/login/Auth.php",
        "other/x.php",
    ]
    result = resolve_capability_map(
        paths,
        class_counts={p: 1 for p in paths},
        fan_in={"app/billing/Pay.php": 3, "app/billing/Invoice.php": 1, "app/login/Auth.php": 2},
        limit=50,
        repo_root=tmp_path,
    )
    assert result.source == SOURCE_TOML
    names = {row.module for row in result.modules}
    assert names == {"billing", "login"}
    assert result.as_dict()["source"] == SOURCE_TOML
    billing = next(row for row in result.modules if row.module == "billing")
    assert billing.hub == "app/billing/Pay.php"
    assert billing.files == 2


def test_all_three_empty_states_reason_and_candidate_globs() -> None:
    """AC: never silent empty table — reason + files_matched nominations."""
    paths = ["src/lib/helper.php", "docs/readme.md"]
    result = resolve_capability_map(
        paths,
        class_counts={p: 0 for p in paths},
        fan_in={p: 0 for p in paths},
        limit=50,
        declared_entry_points=(),
        repo_root=None,
    )
    assert result.source == SOURCE_EMPTY
    assert result.modules == ()
    assert result.empty_reason == EMPTY_REASON
    assert result.candidate_globs
    payload = result.as_dict()
    assert "empty_reason" in payload
    assert payload["candidate_globs"]
    assert not any(
        isinstance(row, dict) and not row for row in payload.get("modules", [])
    )


def test_no_directory_name_inference_without_human_name() -> None:
    """AC: structural path still refuses role-organised containers; no invented names."""
    # Role-organised container alone → structural empty → falls to entry/empty.
    paths = [
        f"src/{role}/f{i}.php"
        for role in ("controller", "model", "service", "repository")
        for i in range(4)
    ]
    structural = find_business_modules(
        paths, class_counts={p: 1 for p in paths}, fan_in={p: 0 for p in paths}, limit=50
    )
    assert structural.modules == ()
    resolved = resolve_capability_map(
        paths,
        class_counts={p: 1 for p in paths},
        fan_in={p: 0 for p in paths},
        limit=50,
        declared_entry_points=(),
    )
    assert resolved.source == SOURCE_EMPTY
    # Must not invent capability names from those role directories.
    assert not any(row.module in {"controller", "model"} for row in resolved.modules)


def test_http_layer_graph_entries_without_declared_globs() -> None:
    """AC: no toml, no structural → HTTP-layer zero-inbound files become entry rows."""
    paths = [
        "src/Controller/BillingController.php",
        "src/Controller/LoginController.php",
        "src/Service/Pay.php",
    ]
    result = resolve_capability_map(
        paths,
        class_counts={p: 1 for p in paths},
        fan_in={p: 0 for p in paths},
        limit=50,
        declared_entry_points=(),
        graph_entry_files=(
            "src/Controller/BillingController.php",
            "src/Controller/LoginController.php",
        ),
        outbound={
            "src/Controller/BillingController.php": ("src/Service/Pay.php",),
        },
    )
    assert result.source == SOURCE_ENTRY
    assert {row.module for row in result.modules} == {
        "BillingController",
        "LoginController",
    }


def test_empty_capabilities_toml_falls_through(tmp_path: Path) -> None:
    """Present-but-empty toml must not freeze a silent empty table."""
    cap = tmp_path / "docs" / "onboarding"
    cap.mkdir(parents=True)
    (cap / "capabilities.toml").write_text("# no capabilities yet\n", encoding="utf-8")
    paths = [f"public/screen_{i}.php" for i in range(2)]
    result = resolve_capability_map(
        paths,
        class_counts={p: 0 for p in paths},
        fan_in={p: 0 for p in paths},
        limit=50,
        declared_entry_points=("public/**",),
        repo_root=tmp_path,
    )
    assert result.source == SOURCE_ENTRY
    assert result.modules


def test_malformed_capabilities_toml_falls_through_and_is_named(tmp_path: Path) -> None:
    """A typo in the hand-written file must not crash the generate, nor vanish silently."""
    cap = tmp_path / "docs" / "onboarding"
    cap.mkdir(parents=True)
    (cap / "capabilities.toml").write_text("[[capability]\nname = 'Billing'\n", encoding="utf-8")
    paths = [f"public/screen_{i}.php" for i in range(2)]
    result = resolve_capability_map(
        paths,
        class_counts={p: 0 for p in paths},
        fan_in={p: 0 for p in paths},
        limit=50,
        declared_entry_points=("public/**",),
        repo_root=tmp_path,
    )
    assert result.source == SOURCE_ENTRY
    assert result.modules
    assert [container for container, _ in result.refused] == ["docs/onboarding/capabilities.toml"]
    assert "unreadable capabilities file" in result.refused[0][1]


def test_toml_coverage_counts_each_file_once(tmp_path: Path) -> None:
    """Two capabilities over the same file must not push coverage past 100 %."""
    cap = tmp_path / "docs" / "onboarding"
    cap.mkdir(parents=True)
    (cap / "capabilities.toml").write_text(
        "[[capability]]\nname = 'Billing'\npaths = ['app/**']\n\n"
        "[[capability]]\nname = 'Invoicing'\npaths = ['app/**']\n",
        encoding="utf-8",
    )
    paths = [f"app/file_{i}.php" for i in range(4)]
    result = resolve_capability_map(
        paths,
        class_counts={p: 1 for p in paths},
        fan_in={p: 0 for p in paths},
        limit=50,
        repo_root=tmp_path,
    )
    assert result.source == SOURCE_TOML
    assert result.covered == 4
    assert result.percent == 100.0


def test_structural_still_wins_when_layout_exists() -> None:
    """Structural modules remain source when toml is absent and layout is real."""
    paths = _four_layout()
    result = resolve_capability_map(
        paths,
        class_counts={p: 1 for p in paths},
        fan_in={p: 0 for p in paths},
        limit=50,
    )
    assert result.source == SOURCE_STRUCTURAL
    assert {row.module for row in result.modules} == {
        "billing",
        "audit",
        "roster",
        "catering",
    }
