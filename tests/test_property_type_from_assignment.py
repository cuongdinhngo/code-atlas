"""Task 447 — an untyped property assigned `new X`, or `@var`-documented, types its receiver."""

from __future__ import annotations

import json
import shlex
import shutil
import subprocess
from pathlib import Path

import pytest

from code_atlas.config import Config, load_config
from code_atlas.indexer import full_build
from code_atlas.store import GraphStore
from code_atlas.tools import find_callers

REPO = Path(__file__).resolve().parent.parent
PHP_ENTRY = REPO / "adapters" / "php" / "index.php"
PHP_AUTOLOAD = REPO / "adapters" / "php" / "vendor" / "autoload.php"
PHP = shutil.which("php")
needs_php = pytest.mark.skipif(
    PHP is None or not PHP_AUTOLOAD.is_file(),
    reason="needs the PHP CLI and `composer install` in adapters/php",
)

# Two classes declare `m`, so no bare-name fallback can stand in for the property's type.
FILES = {
    "src/Model.php": "<?php\nnamespace App;\nclass Model {\n    public function m() {}\n}\n",
    "src/Other.php": "<?php\nnamespace App;\nclass Other {\n    public function m() {}\n}\n",
    "src/Ctl.php": (
        "<?php\nnamespace App;\nclass Ctl {\n    private $model;\n"
        "    public function __construct() { $this->model = new Model(); }\n"
        "    public function run() { $this->model->m(); }\n}\n"
    ),
    "src/Twice.php": (
        "<?php\nnamespace App;\nclass Twice {\n    private $p;\n"
        "    public function a() { $this->p = new Model(); }\n"
        "    public function b() { $this->p = new Other(); }\n"
        "    public function run() { $this->p->m(); }\n}\n"
    ),
    "src/Doc.php": (
        "<?php\nnamespace App;\nclass Doc {\n    /** @var Model */\n    private $model;\n"
        "    public function run() { $this->model->m(); }\n}\n"
    ),
}


def _built(root: Path, files: dict[str, str]) -> Config:
    for rel, body in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(body, encoding="utf-8")
    for args in (("init", "-q"), ("add", "-A"), ("commit", "-qm", "init")):
        subprocess.run(
            ["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
            cwd=root,
            check=True,
            capture_output=True,
        )
    config = load_config(
        root,
        {"CA_WORKERS": "2", "CA_PHP_CMD": shlex.join([str(PHP), str(PHP_ENTRY), "--server"])},
    )
    with GraphStore(config.db_path) as store:
        assert full_build(config, store).failed == 0
    return config


def _callers(config: Config, subject: str) -> dict[str, object]:
    return find_callers.create(config)(subject, detail_level="minimal")


def _rows(payload: dict[str, object]) -> list[tuple[str, str]]:
    """Linked callers only: a `candidate_of` row is an unlinked same-name call shown for proximity."""
    rows = payload["results"]
    assert isinstance(rows, list)
    return [
        (str(row["qname"]), str(row["confidence_tier"])) for row in rows if "candidate_of" not in row
    ]


def _target(config: Config, source: str) -> str | None:
    with GraphStore(config.db_path) as store:
        edges = store.edges_by_source(source, kinds=["CALLS"], limit=10)
    assert len(edges) == 1, edges
    return edges[0]["target_qname"]


@needs_php
def test_ac1_a_constructor_assignment_types_the_property_at_heuristic(tmp_path: Path) -> None:
    config = _built(tmp_path, FILES)
    assert ("\\App\\Ctl::run", "HEURISTIC") in _rows(_callers(config, "\\App\\Model::m"))
    assert ("\\App\\Ctl::run", "HEURISTIC") not in _rows(_callers(config, "\\App\\Other::m"))


@needs_php
def test_ac1_unresolved_receivers_drops_by_one(tmp_path: Path) -> None:
    """Before 447, Ctl and Doc both counted; Twice is the one call still on an untyped receiver."""
    payload = _callers(_built(tmp_path, FILES), "\\App\\Model::m")
    assert payload["unresolved_receivers"] == 1, payload


@needs_php
def test_ac2_two_different_new_assignments_leave_it_untyped(tmp_path: Path) -> None:
    config = _built(tmp_path, FILES)
    assert _target(config, "\\App\\Twice::run") is None
    for subject in ("\\App\\Model::m", "\\App\\Other::m"):
        assert "\\App\\Twice::run" not in {qname for qname, _ in _rows(_callers(config, subject))}


@needs_php
def test_ac3_a_var_docblock_types_the_property(tmp_path: Path) -> None:
    config = _built(tmp_path, FILES)
    assert ("\\App\\Doc::run", "HEURISTIC") in _rows(_callers(config, "\\App\\Model::m"))


@needs_php
def test_scope2_a_declared_type_stays_resolved(tmp_path: Path) -> None:
    typed = (
        "<?php\nnamespace App;\nclass Typed {\n    private Model $model;\n"
        "    public function __construct() { $this->model = new Model(); }\n"
        "    public function run() { $this->model->m(); }\n}\n"
    )
    config = _built(tmp_path, {**FILES, "src/Typed.php": typed})
    assert ("\\App\\Typed::run", "RESOLVED") in _rows(_callers(config, "\\App\\Model::m"))


# W1: what keeps a property untyped — a value, a reference, `new $v`, a non-null default, promotion.
UNTYPED = {
    "src/Value.php": (
        "<?php\nnamespace App;\nclass Value {\n    private $p;\n"
        "    public function a($x) { $this->p = new Model(); $this->p = $x; }\n"
        "    public function run() { $this->p->m(); }\n}\n"
    ),
    "src/Ref.php": (
        "<?php\nnamespace App;\nclass Ref {\n    private $p;\n"
        "    public function a($x) { $this->p = new Model(); $this->p = &$x; }\n"
        "    public function run() { $this->p->m(); }\n}\n"
    ),
    "src/Dyn.php": (
        "<?php\nnamespace App;\nclass Dyn {\n    private $p;\n"
        "    public function a($c) { $this->p = new $c(); }\n"
        "    public function run() { $this->p->m(); }\n}\n"
    ),
    "src/Defaulted.php": (
        "<?php\nnamespace App;\nclass Defaulted {\n    private $p = [];\n"
        "    public function a() { $this->p = new Model(); }\n"
        "    public function run() { $this->p->m(); }\n}\n"
    ),
    "src/Promoted.php": (
        "<?php\nnamespace App;\nclass Promoted {\n"
        "    public function __construct(private $p) { $this->p = new Model(); }\n"
        "    public function run() { $this->p->m(); }\n}\n"
    ),
}
# W1: what still types it — a `null` default and a lazy `??=`, and `new self` names the class.
TYPED = {
    "src/Lazy.php": (
        "<?php\nnamespace App;\nclass Lazy {\n    private $p = null;\n"
        "    public function get() { $this->p ??= new Model(); return $this->p; }\n"
        "    public function run() { $this->p->m(); }\n}\n"
    ),
}


@needs_php
def test_w1_any_other_write_leaves_it_untyped(tmp_path: Path) -> None:
    config = _built(tmp_path, {**FILES, **UNTYPED, **TYPED})
    callers = {qname for qname, _ in _rows(_callers(config, "\\App\\Model::m"))}
    for rel in UNTYPED:
        assert f"\\App\\{Path(rel).stem}::run" not in callers, rel
    assert "\\App\\Lazy::run" in callers


@needs_php
def test_w2_a_var_docblock_wins_over_the_assignments(tmp_path: Path) -> None:
    both = (
        "<?php\nnamespace App;\nclass Both {\n    /** @var Other */\n    private $p;\n"
        "    public function __construct() { $this->p = new Model(); }\n"
        "    public function run() { $this->p->m(); }\n}\n"
    )
    config = _built(tmp_path, {**FILES, "src/Both.php": both})
    assert ("\\App\\Both::run", "HEURISTIC") in _rows(_callers(config, "\\App\\Other::m"))


@needs_php
def test_scope3_a_child_assigning_its_parents_property_leaves_it_untyped(tmp_path: Path) -> None:
    """The parent declares `$model` in another file; the child's write is not the declarer's (W4)."""
    files = {
        **FILES,
        "src/Base.php": "<?php\nnamespace App;\nclass Base {\n    protected $model;\n}\n",
        "src/Child.php": (
            "<?php\nnamespace App;\nclass Child extends Base {\n"
            "    public function __construct() { $this->model = new Model(); }\n"
            "    public function run() { $this->model->m(); }\n}\n"
        ),
    }
    assert _target(_built(tmp_path, files), "\\App\\Child::run") is None


@needs_php
def test_deviation_a_parent_typing_its_own_property_reaches_the_child(tmp_path: Path) -> None:
    """The parent's file makes the claim; the graph carries it to a child in another file (P3)."""
    files = {
        **FILES,
        "src/Base.php": (
            "<?php\nnamespace App;\nclass Base {\n    protected $model;\n"
            "    public function __construct() { $this->model = new Model(); }\n}\n"
        ),
        "src/Child.php": (
            "<?php\nnamespace App;\nclass Child extends Base {\n"
            "    public function run() { $this->model->m(); }\n}\n"
        ),
    }
    rows = _rows(_callers(_built(tmp_path, files), "\\App\\Model::m"))
    assert ("\\App\\Child::run", "HEURISTIC") in rows


@needs_php
def test_the_property_node_carries_the_inferred_type(tmp_path: Path) -> None:
    """The adapter's claim is a `doc_type`, never `type` — the core reads it as a docblock (393)."""
    config = _built(tmp_path, FILES)
    with GraphStore(config.db_path) as store:
        found = store.nodes_by_qualified_names(["\\App\\Ctl::$model", "\\App\\Twice::$p"], limit=1)
    ctl = json.loads(str(found["\\App\\Ctl::$model"][0]["extra"]))
    assert ctl["doc_type"] == "\\App\\Model"
    assert "type" not in ctl
    assert "doc_type" not in str(found["\\App\\Twice::$p"][0].get("extra") or "")


# Challenger round 1 (F1–F3): writes the first cut did not see, so a wrong class was claimed.
MISSED_WRITES = {
    "src/Destr.php": (
        "<?php\nnamespace App;\nclass Destr {\n    private $p;\n"
        "    public function a() { $this->p = new Model(); }\n"
        "    public function b($xs) { [$this->p] = $xs; }\n"
        "    public function run() { $this->p->m(); }\n}\n"
    ),
    "src/Each.php": (
        "<?php\nnamespace App;\nclass Each {\n    private $p;\n"
        "    public function a() { $this->p = new Model(); }\n"
        "    public function b($xs) { foreach ($xs as $this->p) {} }\n"
        "    public function run() { $this->p->m(); }\n}\n"
    ),
    "src/UsesTr.php": (
        "<?php\nnamespace App;\ntrait Tr {\n    public function w() { $this->p = new Other(); }\n}\n"
        "class UsesTr {\n    use Tr;\n    private $p;\n"
        "    public function a() { $this->p = new Model(); }\n"
        "    public function run() { $this->p->m(); }\n}\n"
    ),
    "src/Kin.php": (
        "<?php\nnamespace App;\nclass Kin {\n    protected $p;\n"
        "    public function __construct() { $this->p = new Model(); }\n}\n"
        "class Kid extends Kin {\n    public function w() { $this->p = new Other(); }\n"
        "    public function run() { $this->p->m(); }\n}\n"
    ),
}


@needs_php
def test_challenger_a_destructure_foreach_trait_or_subclass_write_untypes_it(tmp_path: Path) -> None:
    config = _built(tmp_path, {**FILES, **MISSED_WRITES})
    for source in ("Destr", "Each", "UsesTr", "Kid"):
        assert _target(config, f"\\App\\{source}::run") is None, source
