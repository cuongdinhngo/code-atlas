"""Resolve a Python import specifier to a repo-relative path by filesystem arithmetic (no jedi)."""

from __future__ import annotations

from pathlib import Path


def _is_file(posix_path: str) -> bool:
    try:
        return Path(posix_path).is_file()
    except OSError:
        return False


def resolve_dotted_under(base_dir: str, dotted: str) -> str | None:
    """Resolve ``dotted`` as a module path rooted at ``base_dir`` (repo-relative posix)."""
    parts = dotted.split(".")
    rel = "/".join(parts)
    base = "" if base_dir in ("", ".") else base_dir.rstrip("/")
    for candidate in (
        f"{rel}.py" if not base else f"{base}/{rel}.py",
        f"{rel}/__init__.py" if not base else f"{base}/{rel}/__init__.py",
    ):
        if _is_file(candidate):
            return candidate
    return None


def package_dir(from_qpath: str) -> str:
    """Directory of the package that owns ``from_qpath`` (PEP 328 current package)."""
    parent = str(Path(from_qpath).parent.as_posix())
    if parent == ".":
        parent = ""
    return parent


def climb(dir_path: str, levels: int) -> str | None:
    """Walk ``levels`` parents up from ``dir_path``; ``None`` if that leaves the tree."""
    current = dir_path
    for _ in range(levels):
        if current in ("", "."):
            return None
        parent = str(Path(current).parent.as_posix())
        if parent == ".":
            parent = ""
        if parent == current:
            return None
        current = parent
    return current


def resolve_absolute(
    dotted: str,
    from_qpath: str,
    source_roots: tuple[str, ...] | list[str] | None = None,
) -> str | None:
    """Try repo root, importer ancestors, then configured source roots (task 230)."""
    hit = resolve_dotted_under("", dotted)
    if hit:
        return hit
    directory: str | None = package_dir(from_qpath)
    seen: set[str] = set()
    while directory is not None and directory not in seen:
        seen.add(directory)
        hit = resolve_dotted_under(directory, dotted)
        if hit:
            return hit
        if directory in ("", "."):
            break
        directory = climb(directory, 1)
    for root in source_roots or ():
        cleaned = root.strip().strip("/")
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        hit = resolve_dotted_under(cleaned, dotted)
        if hit:
            return hit
    return None


def resolve_import(
    *,
    module: str | None,
    level: int,
    from_qpath: str,
    name: str | None = None,
    source_roots: tuple[str, ...] | list[str] | None = None,
) -> str | None:
    """Resolve an ``import`` / ``from … import`` to a repo-relative path, or ``None``.

    ``name`` is used when ``from . import x`` (module is None) so ``x`` is the leaf.
    """
    if level > 0:
        start = climb(package_dir(from_qpath), level - 1)
        if start is None:
            return None
        if module:
            return resolve_dotted_under(start, module)
        if name and name != "*":
            return resolve_dotted_under(start, name)
        return None
    if module:
        return resolve_absolute(module, from_qpath, source_roots=source_roots)
    return None


def import_target_raw(
    *,
    module: str | None,
    level: int,
    from_qpath: str,
    name: str | None = None,
    source_roots: tuple[str, ...] | list[str] | None = None,
) -> str:
    """Resolved path when on disk; otherwise the dotted specifier the source wrote."""
    resolved = resolve_import(
        module=module,
        level=level,
        from_qpath=from_qpath,
        name=name,
        source_roots=source_roots,
    )
    if resolved:
        return resolved
    if level > 0:
        dots = "." * level
        if module and name and name != "*":
            return f"{dots}{module}.{name}"
        if module:
            return f"{dots}{module}"
        if name and name != "*":
            return f"{dots}{name}"
        return dots
    if module and name and name != "*":
        return f"{module}.{name}"
    return module or (name or "")
