"""Business modules read out of the directory tree — the bridge from "fix screen X" to a file (114).

A newcomer's only real question is which file to open for a named capability, and an artifact
organised by files, symbols and edges answers a different one. This module derives the capability
level from the paths themselves: the directory fanning out widest into peer subtrees is the
container, and its children are the modules.

Nothing is named. The mockup prototype used a container word list, a region list, a library list
and hardcoded tree prefixes — four separate R2.2 violations. Here the container, the module names
and the trees are all read from the path set, and 110's already-ratified responsibility vocabulary
is used only as a *negative* filter. Pure: no SQL, no LLM, no language branch (R1.1/R1.4/R4);
sorted throughout, so identical input yields byte-identical output (R4.2).
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace

from code_atlas.ignore import translate_path_pattern
from code_atlas.onboarding.layers import responsibility_layer, responsibility_of_segment
from code_atlas.onboarding.prose import SLOT_MODULE, ProseRequest, ProseRun
from code_atlas.onboarding.scope import in_working_scope

# A child directory must hold this many candidate files to count as a peer of its siblings — the
# floor
# that says "this holds real code". The LAYOUT decision is MIN_CONTAINER_MODULES' job, not this one.
MIN_MODULE_FILES = 3
# A capability layout has many peer features; a library's internal split has two or three.
# Measured on
# the pinned public samples: a two-way split of 10 + 7 files must report ZERO modules, which a
# file-count floor alone cannot do (task 114 analysis).
MIN_CONTAINER_MODULES = 4

# The 110 layers whose files are not candidates at all. Excluding these is what stops a 200-package
# dependency directory being elected the widest container and reported as 200 business modules.
EXCLUDED_LAYERS = ("Vendor / Framework", "Tests")

REFUSED_ROLE_ORGANISED = (
    "container groups by responsibility, not by capability — at least half its "
    "subdirectories name a role, so its children are not business modules"
)
COVERAGE_NOTE = (
    "Files outside every module directory are not covered by this table — search for them "
    "by name; a table that looks exhaustive and is not would be worse than a smaller honest one."
)

__all__ = [
    "COVERAGE_NOTE",
    "directory_owners",
    "module_of_path",
    "EXCLUDED_LAYERS",
    "MIN_CONTAINER_MODULES",
    "MIN_MODULE_FILES",
    "REFUSED_ROLE_ORGANISED",
    "BusinessModule",
    "ModuleMap",
    "find_business_modules",
]


@dataclass(frozen=True)
class BusinessModule:
    """One capability read out of the tree: its size, where it lives, and its busiest file."""

    module: str
    label: str
    files: int
    classes: int
    trees: tuple[str, ...]
    directories: tuple[str, ...]
    hub: str
    hub_fan_in: int
    single_tree: bool

    def as_dict(self) -> dict[str, object]:
        """Order-stable dict view — what every renderer serialises (R4.2)."""
        return {
            "classes": self.classes,
            "directories": list(self.directories),
            "files": self.files,
            "hub": self.hub,
            "hub_fan_in": self.hub_fan_in,
            "label": self.label,
            "module": self.module,
            "single_tree": self.single_tree,
            "trees": list(self.trees),
        }


@dataclass(frozen=True)
class ModuleMap:
    """The module table plus the coverage it does **not** claim, and every container it refused."""

    modules: tuple[BusinessModule, ...]
    containers: tuple[str, ...]
    refused: tuple[tuple[str, str], ...]
    covered: int
    total: int
    excluded: int
    truncated: bool
    # 263 — which of the three sources answered; empty_explained carries nominations.
    source: str = "structural"
    empty_reason: str | None = None
    candidate_globs: tuple[tuple[str, int], ...] = ()

    @property
    def percent(self) -> float:
        """Share of every indexed file this table accounts for, one decimal place (AC2)."""
        return 0.0 if not self.total else round(100.0 * self.covered / self.total, 1)

    def as_dict(self) -> dict[str, object]:
        """Order-stable dict view; coverage rides with the rows so no renderer can drop it."""
        payload: dict[str, object] = {
            "containers": list(self.containers),
            "coverage": {
                "covered": self.covered,
                "excluded": self.excluded,
                "note": COVERAGE_NOTE,
                "percent": self.percent,
                "total": self.total,
            },
            "modules": [module.as_dict() for module in self.modules],
            "refused": [{"container": path, "reason": reason} for path, reason in self.refused],
            "source": self.source,
            "truncated": self.truncated,
        }
        if self.empty_reason is not None:
            payload["empty_reason"] = self.empty_reason
        if self.candidate_globs:
            payload["candidate_globs"] = [
                {"glob": pattern, "files_matched": count}
                for pattern, count in self.candidate_globs
            ]
        return payload


def _candidates(
    file_paths: Sequence[str], stub_roots: Sequence[str] | None
) -> tuple[tuple[str, ...], int]:
    """Indexed paths that could belong to a capability, plus how many were excluded (task 113's
    signals)."""
    rules = tuple(
        re.compile(f"{translate_path_pattern(f'{root}/**')}$") for root in stub_roots or ()
    )
    kept: list[str] = []
    for path in file_paths:
        if any(rule.match(path) for rule in rules):
            continue
        if responsibility_layer(path) in EXCLUDED_LAYERS:
            continue
        kept.append(path)
    return tuple(sorted(kept)), len(file_paths) - len(kept)


def _subtree_files(candidates: Sequence[str]) -> dict[str, int]:
    """Candidate file count for every directory, counted over its whole subtree."""
    counts: dict[str, int] = {}
    for path in candidates:
        prefix = ""
        for segment in path.split("/")[:-1]:
            prefix = f"{prefix}/{segment}" if prefix else segment
            counts[prefix] = counts.get(prefix, 0) + 1
    return counts


def _child_dirs(candidates: Sequence[str]) -> dict[str, set[str]]:
    """The immediate child DIRECTORIES of every directory (a leaf filename is not a child dir)."""
    children: dict[str, set[str]] = {}
    for path in candidates:
        segments = path.split("/")[:-1]
        for index in range(len(segments) - 1):
            parent = "/".join(segments[: index + 1])
            children.setdefault(parent, set()).add(segments[index + 1])
    return children


def _containers(
    candidates: Sequence[str], *, min_files: int, min_modules: int
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """Directories fanning out into >= ``min_modules`` peer subtrees, shallowest-wins (no nesting).

    The container level is DERIVED here — never a word list. A container nested inside another is
    dropped, so a module can never contain modules.
    """
    subtree = _subtree_files(candidates)
    found: list[tuple[str, tuple[str, ...]]] = []
    for parent, children in sorted(_child_dirs(candidates).items()):
        qualifying = tuple(
            sorted(name for name in children if subtree.get(f"{parent}/{name}", 0) >= min_files)
        )
        if len(qualifying) >= min_modules:
            found.append((parent, qualifying))
    kept: list[tuple[str, tuple[str, ...]]] = []
    for parent, qualifying in found:
        if any(parent.startswith(f"{other}/") for other, _ in found):
            continue  # a container inside a container: keep the shallowest only
        kept.append((parent, qualifying))
    return tuple(kept)


def _is_role_organised(qualifying: Sequence[str]) -> bool:
    """Does this container group by responsibility, not capability? (>= half its children.)

    Classified ONCE per container, so a capability-organised container keeps a role-named member —
    the anchor's `api` and `reports` are genuine capabilities there — while a container whose
    children are mostly role names contributes nothing (measured on a pinned sample: 4 of 7).
    """
    roles = sum(1 for name in qualifying if responsibility_of_segment(name) is not None)
    return roles * 2 >= len(qualifying)


def _tree_of(container: str) -> str:
    """The tree a container belongs to: its parent path, or ``(root)`` when it has none.

    Derived, so region and container names cannot become modules — both sit ABOVE the module level.
    """
    head, _, _ = container.rpartition("/")
    return head or "(root)"


def find_business_modules(
    file_paths: Sequence[str],
    *,
    class_counts: Mapping[str, int],
    fan_in: Mapping[str, int],
    stub_roots: Sequence[str] | None = None,
    working_roots: Sequence[str] | None = None,
    limit: int,
    prose: ProseRun | None = None,
    min_files: int = MIN_MODULE_FILES,
    min_modules: int = MIN_CONTAINER_MODULES,
) -> ModuleMap:
    """Read the capability map out of the tree (task 114).

    ``class_counts``/``fan_in`` are per-file, from ``store.file_class_counts()`` and 083's module
    metrics. A repo with no capability layout yields **no** modules and the containers it refused,
    rather than inventing groups (AC5).
    """
    candidates, excluded = _candidates(file_paths, stub_roots)
    containers = _containers(candidates, min_files=min_files, min_modules=min_modules)
    accepted: list[tuple[str, tuple[str, ...]]] = []
    refused: list[tuple[str, str]] = []
    for container, qualifying in containers:
        if _is_role_organised(qualifying):
            refused.append((container, REFUSED_ROLE_ORGANISED))
        else:
            accepted.append((container, qualifying))

    # Group by lowercased name so the same capability under two trees is one row (the divergence
    # signal); the first-seen spelling is what a reader is shown.
    label: dict[str, str] = {}
    trees: dict[str, set[str]] = {}
    directories: dict[str, set[str]] = {}
    for container, qualifying in accepted:
        for name in qualifying:
            key = name.lower()
            label.setdefault(key, name)
            trees.setdefault(key, set()).add(_tree_of(container))
            directories.setdefault(key, set()).add(f"{container}/{name}")

    # Directory -> module key, so a file finds its owner by walking its own prefixes (O(depth)),
    # not by scanning every module (O(modules) per file would be 40k x 24 on the anchor).
    owner_of_dir = {
        directory: key for key, dirs in directories.items() for directory in dirs
    }
    files: dict[str, int] = {}
    classes: dict[str, int] = {}
    hubs: dict[str, tuple[int, str]] = {}
    covered = 0
    for path in candidates:
        owner = _owner(path, owner_of_dir)
        if owner is None:
            continue
        covered += 1
        files[owner] = files.get(owner, 0) + 1
        classes[owner] = classes.get(owner, 0) + class_counts.get(path, 0)
        if not in_working_scope(path, working_roots):
            continue
        score = (fan_in.get(path, 0), path)
        # Highest fan-in wins; the path breaks ties, so the busiest file is chosen
        # deterministically. working_roots (206) restrict the hub pick, not the module set.
        if owner not in hubs or score > hubs[owner]:
            hubs[owner] = score

    # A single container makes every module trivially single-tree, so the divergence signal is only
    # claimed where there is a sibling container to diverge from (H5).
    comparable = len(accepted) > 1
    rows = [
        BusinessModule(
            module=label[key],
            label=label[key],
            files=files.get(key, 0),
            classes=classes.get(key, 0),
            trees=tuple(sorted(trees[key])),
            directories=tuple(sorted(directories[key])),
            hub=hubs.get(key, (0, ""))[1],
            hub_fan_in=hubs.get(key, (0, ""))[0],
            single_tree=comparable and len(trees[key]) == 1,
        )
        for key in sorted(directories)
    ]
    # Largest first — the table's reading order; the name breaks ties (R4.2).
    rows.sort(key=lambda row: (-row.files, row.module))
    return ModuleMap(
        modules=_labelled(tuple(rows[:limit]), prose),
        containers=tuple(sorted(container for container, _ in accepted)),
        refused=tuple(sorted(refused)),
        covered=covered,
        total=len(file_paths),
        excluded=excluded,
        truncated=len(rows) > limit,
    )


def _labelled(
    rows: tuple[BusinessModule, ...], prose: ProseRun | None
) -> tuple[BusinessModule, ...]:
    """Word each module's label through the 117 seam (198). Membership is already decided.

    Applied AFTER the table is built, ranked and cut, so the seam cannot add, drop or re-order a
    module however it answers — it only replaces a string. With no writer injected every label is
    the directory name the table already carried, byte for byte (R4/R4.1).
    """
    if prose is None or not prose.enabled:
        return rows
    return tuple(
        replace(
            row,
            label=prose.text(
                ProseRequest(
                    slot=SLOT_MODULE,
                    key=row.module,
                    names=(row.module, row.hub, *row.trees),
                    facts=(
                        ("files", str(row.files)),
                        ("classes", str(row.classes)),
                        ("busiest file", row.hub),
                        ("directories", ", ".join(row.directories)),
                    ),
                    default=row.module,
                )
            ),
        )
        for row in rows
    )


def directory_owners(modules: Sequence[BusinessModule]) -> dict[str, str]:
    """Directory → module name, straight off the published table (114).

    The assignment a consumer joins on, so nothing has to re-derive which directory belongs to
    which capability — a second derivation is a second module notion, which PLAN §1 forbids.
    """
    return {directory: module.module for module in modules for directory in module.directories}


def module_of_path(path: str, owner_of_dir: Mapping[str, str]) -> str | None:
    """The module owning ``path``, or None when the table does not cover it.

    Public name for the rule the table was built with, so a join uses it rather than a lookalike.
    """
    return _owner(path, owner_of_dir)


def _owner(path: str, owner_of_dir: Mapping[str, str]) -> str | None:
    """The module owning ``path``, found by walking its ancestor directories. Deepest wins."""
    segments = path.split("/")[:-1]
    for depth in range(len(segments), 0, -1):
        owner = owner_of_dir.get("/".join(segments[:depth]))
        if owner is not None:
            return owner
    return None
