"""AC2: the ignore matcher over built-ins, ``.gitignore`` and ``.codeatlasignore`` (task 003, §11).

Every source is covered by matches **and** near-miss non-matches, so a matcher that ignored
everything would fail here rather than pass a match-only suite.
"""

from pathlib import Path

import pytest

from code_atlas.ignore import (
    ATLAS_IGNORE_FILE,
    BUILTIN_PATTERNS,
    COMPOSED_IGNORE_FILES,
    GITIGNORE_FILE,
    SOURCE_BUILTIN,
    composed_source_names,
    load_ignore,
    source_name,
)


def write(root: Path, name: str, *lines: str) -> None:
    (root / name).write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_the_builtin_list_matches_the_plan_inventory() -> None:
    # Guards the guard: an empty or trimmed list would make the cases below pass vacuously.
    assert BUILTIN_PATTERNS == (
        "vendor/",
        "var/",
        "uploads/",
        "log/",
        "node_modules/",
        ".git/",
        "*.blade.*",
    )


@pytest.mark.parametrize("pattern", BUILTIN_PATTERNS, ids=lambda pattern: pattern.rstrip("/"))
def test_a_builtin_directory_is_ignored_at_root_and_nested(tmp_path: Path, pattern: str) -> None:
    matcher = load_ignore(tmp_path)
    directory = pattern.rstrip("/")

    assert matcher.is_ignored(directory, is_dir=True)
    assert matcher.is_ignored(f"{directory}/file.php")
    assert matcher.is_ignored(f"src/deep/{directory}/file.php")


@pytest.mark.parametrize(
    "path",
    ["vendored/file.php", "src/vendor.php", "logger/app.php", "var_dump.php"],
    ids=["prefix-of-a-builtin", "file-named-like-a-builtin", "longer-name", "underscore-name"],
)
def test_a_near_miss_is_not_ignored(tmp_path: Path, path: str) -> None:
    assert not load_ignore(tmp_path).is_ignored(path)


def test_comments_and_blank_lines_are_skipped(tmp_path: Path) -> None:
    write(tmp_path, GITIGNORE_FILE, "# build output", "", "   ", "build/")
    matcher = load_ignore(tmp_path)

    assert matcher.is_ignored("build/app.js")
    assert not matcher.is_ignored("comment.php")


def test_a_glob_matches_at_any_depth(tmp_path: Path) -> None:
    write(tmp_path, GITIGNORE_FILE, "*.log")
    matcher = load_ignore(tmp_path)

    assert matcher.is_ignored("app.log")
    assert matcher.is_ignored("src/deep/app.log")
    assert not matcher.is_ignored("app.logic")


def test_a_leading_slash_anchors_to_the_root(tmp_path: Path) -> None:
    write(tmp_path, GITIGNORE_FILE, "/build")
    matcher = load_ignore(tmp_path)

    assert matcher.is_ignored("build")
    assert not matcher.is_ignored("src/build")


def test_a_trailing_slash_matches_directories_only(tmp_path: Path) -> None:
    write(tmp_path, GITIGNORE_FILE, "dist/")
    matcher = load_ignore(tmp_path)

    assert matcher.is_ignored("dist", is_dir=True)
    assert matcher.is_ignored("src/dist/app.js")
    assert not matcher.is_ignored("dist")


def test_a_character_class_and_single_char_wildcard_match(tmp_path: Path) -> None:
    write(tmp_path, GITIGNORE_FILE, "cache[0-9].txt", "tmp?.txt")
    matcher = load_ignore(tmp_path)

    assert matcher.is_ignored("cache7.txt")
    assert matcher.is_ignored("tmpa.txt")
    assert not matcher.is_ignored("cachex.txt")
    assert not matcher.is_ignored("tmpab.txt")


def test_a_double_star_crosses_directories(tmp_path: Path) -> None:
    write(tmp_path, GITIGNORE_FILE, "docs/**/draft.md")
    matcher = load_ignore(tmp_path)

    assert matcher.is_ignored("docs/draft.md")  # /**/ matches zero dirs
    assert matcher.is_ignored("docs/a/b/draft.md")
    assert not matcher.is_ignored("other/a/draft.md")


def test_a_negation_re_includes_a_file(tmp_path: Path) -> None:
    write(tmp_path, GITIGNORE_FILE, "*.log", "!keep.log")
    matcher = load_ignore(tmp_path)

    assert matcher.is_ignored("app.log")
    assert not matcher.is_ignored("keep.log")


def test_the_last_matching_rule_wins_across_sources(tmp_path: Path) -> None:
    write(tmp_path, GITIGNORE_FILE, "*.md")
    write(tmp_path, ATLAS_IGNORE_FILE, "!README.md")
    matcher = load_ignore(tmp_path)

    assert matcher.is_ignored("notes.md")
    assert not matcher.is_ignored("README.md")


def test_the_project_ignore_file_adds_to_the_other_sources(tmp_path: Path) -> None:
    write(tmp_path, GITIGNORE_FILE, "*.log")
    write(tmp_path, ATLAS_IGNORE_FILE, "generated/")
    matcher = load_ignore(tmp_path)

    assert matcher.is_ignored("app.log")
    assert matcher.is_ignored("generated/api.php")
    assert matcher.is_ignored("vendor/lib.php")


def test_an_excluded_directory_cannot_be_re_included(tmp_path: Path) -> None:
    # The rule that lets the indexer prune a whole subtree instead of testing every file under it.
    write(tmp_path, ATLAS_IGNORE_FILE, "!vendor/keep.php")
    assert load_ignore(tmp_path).is_ignored("vendor/keep.php")


def test_missing_ignore_files_leave_the_builtins_in_force(tmp_path: Path) -> None:
    matcher = load_ignore(tmp_path)

    assert not (tmp_path / GITIGNORE_FILE).exists()
    assert not (tmp_path / ATLAS_IGNORE_FILE).exists()
    assert matcher.is_ignored("node_modules/lib/index.js")
    assert not matcher.is_ignored("src/app.php")


def test_rules_keep_their_source_order(tmp_path: Path) -> None:
    write(tmp_path, GITIGNORE_FILE, "*.log")
    write(tmp_path, ATLAS_IGNORE_FILE, "!keep.log")
    first = load_ignore(tmp_path).rules
    second = load_ignore(tmp_path).rules

    assert [rule.regex.pattern for rule in first] == [rule.regex.pattern for rule in second]
    assert len(first) == len(BUILTIN_PATTERNS) + 2


def test_ignore_source_names_the_last_excluding_source(tmp_path: Path) -> None:
    write(tmp_path, ATLAS_IGNORE_FILE, "vendor/")
    matcher = load_ignore(tmp_path)

    assert matcher.ignore_source("vendor/lib.php") == source_name(ATLAS_IGNORE_FILE)
    assert matcher.ignore_source("src/app.php") is None
    assert matcher.is_ignored("vendor/lib.php")
    assert not matcher.is_ignored("src/app.php")


def test_every_loaded_rule_stamps_a_composed_source(tmp_path: Path) -> None:
    write(tmp_path, GITIGNORE_FILE, "*.log")
    write(tmp_path, ATLAS_IGNORE_FILE, "generated/")
    allowed = composed_source_names()
    matcher = load_ignore(tmp_path)

    assert {rule.source for rule in matcher.rules} <= allowed
    assert SOURCE_BUILTIN in {rule.source for rule in matcher.rules}
    assert source_name(GITIGNORE_FILE) in {rule.source for rule in matcher.rules}
    assert source_name(ATLAS_IGNORE_FILE) in {rule.source for rule in matcher.rules}
    assert COMPOSED_IGNORE_FILES == (GITIGNORE_FILE, ATLAS_IGNORE_FILE)
