"""Walk a ``.py`` file with stdlib ``ast`` and emit contract nodes/edges (task 020 + 217)."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from src.imports import import_target_raw, resolve_import

MEMBER_SEP = "::"

_MODIFIER_DECORATORS = frozenset({"staticmethod", "classmethod", "property"})
# Matched on the leaf, so a bare `Protocol`, `typing.Protocol` and `t.ABC` all classify alike.
_INTERFACE_LEAVES = frozenset({"Protocol", "ABC"})
_ENUM_LEAVES = frozenset({"Enum"})
_STRIP_CONTAINERS = frozenset(
    {"Optional", "Union", "list", "dict", "List", "Dict", "tuple", "Tuple", "set", "Set"}
)
_SKIP_TYPE_NAMES = frozenset(
    {
        "int",
        "str",
        "bool",
        "bytes",
        "float",
        "complex",
        "None",
        "Any",
        "object",
        "Optional",
        "Union",
        "list",
        "dict",
        "List",
        "Dict",
        "tuple",
        "Tuple",
        "set",
        "Set",
        "Callable",
        "Iterable",
        "Sequence",
        "Mapping",
        "Type",
        "ClassVar",
        "Final",
        "Literal",
        "Self",
    }
)


def to_posix(path: str) -> str:
    return path.replace("\\", "/")


def module_name(qpath: str) -> str:
    """Repo-relative path → dotted module (``a/b/__init__.py`` → ``a.b``, ``a/b.py`` → ``a.b``)."""
    p = to_posix(qpath)
    if p.endswith("/__init__.py"):
        p = p[: -len("/__init__.py")]
    elif p.endswith(".py"):
        p = p[: -len(".py")]
    return p.replace("/", ".") if p else ""


def member(container: str, name: str) -> str:
    return f"{container}{MEMBER_SEP}{name}"


def dotted(container: str, name: str) -> str:
    return f"{container}.{name}" if container else name


def _decorator_leaf_name(deco: ast.expr) -> str | None:
    node: ast.expr = deco.func if isinstance(deco, ast.Call) else deco
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _decorator_names(node: ast.AST) -> list[str]:
    names: list[str] = []
    for deco in getattr(node, "decorator_list", []) or []:
        leaf = _decorator_leaf_name(deco)
        if leaf:
            names.append(leaf)
    return names


def _method_modifiers(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    mods: list[str] = []
    if isinstance(node, ast.AsyncFunctionDef):
        mods.append("async")
    for name in _decorator_names(node):
        if name in _MODIFIER_DECORATORS and name not in mods:
            mods.append(name)
    return mods


def _function_modifiers(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    return ["async"] if isinstance(node, ast.AsyncFunctionDef) else []


def _annotation_text(ann: ast.expr | None) -> str | None:
    """Source spelling of a type annotation, or None when absent (R5.2 — never invent)."""
    if ann is None:
        return None
    return ast.unparse(ann)


def _callable_params(
    node: ast.FunctionDef | ast.AsyncFunctionDef, *, skip_receiver: bool
) -> list[dict[str, str | None]]:
    """Contract ``params`` entries: name + declared type text (null when unannotated)."""
    args = node.args
    entries: list[ast.arg] = [*args.posonlyargs, *args.args, *args.kwonlyargs]
    out: list[dict[str, str | None]] = []
    for i, arg in enumerate(entries):
        if skip_receiver and i == 0 and arg.arg in ("self", "cls"):
            continue
        out.append({"name": arg.arg, "type": _annotation_text(arg.annotation)})
    if args.vararg is not None:
        out.append({"name": f"*{args.vararg.arg}", "type": _annotation_text(args.vararg.annotation)})
    if args.kwarg is not None:
        out.append({"name": f"**{args.kwarg.arg}", "type": _annotation_text(args.kwarg.annotation)})
    return out


def _literal_kind(node: ast.expr) -> str | None:
    """Contract ``args`` category for one call argument — shape, never value (049)."""
    if isinstance(node, ast.Constant):
        if node.value is None:
            return "null"
        if node.value is True:
            return "true"
        if node.value is False:
            return "false"
        if isinstance(node.value, (int, float, complex)):
            return "number"
        if isinstance(node.value, str):
            return "string"
        if isinstance(node.value, (bytes, bytearray)):
            return "string"
        return None
    if isinstance(node, ast.JoinedStr):
        return "string"
    if isinstance(node, (ast.List, ast.Tuple, ast.Set, ast.Dict)):
        return "array"
    return None


def _arg_literals(call: ast.Call) -> list[str | None] | None:
    """One category per positional arg; starred args drop the whole list (unknown arity)."""
    if any(isinstance(a, ast.Starred) for a in call.args):
        return None
    # Keyword-only calls still record positionals; keywords are not positional slots.
    return [_literal_kind(a) for a in call.args]


def _dict_string_keys(node: ast.Dict) -> list[str]:
    keys: list[str] = []
    for key in node.keys:
        if isinstance(key, ast.Constant) and isinstance(key.value, str):
            keys.append(key.value)
    return keys


def _arg_keys(call: ast.Call) -> list[list[str] | None]:
    """Parallel to ``args``: string keys of a dict literal, else null (063)."""
    out: list[list[str] | None] = []
    for arg in call.args:
        if isinstance(arg, ast.Dict):
            out.append(_dict_string_keys(arg))
        elif isinstance(arg, (ast.List, ast.Tuple, ast.Set)):
            out.append([])
        else:
            out.append(None)
    return out



def _is_upper_const(name: str) -> bool:
    return name.isupper() and any(c.isalpha() for c in name)


def _attr_dotted(expr: ast.Attribute) -> str:
    parts: list[str] = []
    cur: ast.expr = expr
    while isinstance(cur, ast.Attribute):
        parts.append(cur.attr)
        cur = cur.value
    # The loop exits only on a non-Attribute, so a Name is the only spelling left to keep.
    parts.append(cur.id if isinstance(cur, ast.Name) else "(dynamic)")
    parts.reverse()
    return ".".join(parts)


def _unwrap_base(base: ast.expr) -> ast.expr:
    """Peel ``Protocol[T]`` / ``Enum[…]`` to the named base expression."""
    return base.value if isinstance(base, ast.Subscript) else base


def _marker_from_base_expr(
    base: ast.expr,
    *,
    import_aliases: dict[str, str],
) -> str | None:
    """Return a classification marker (Protocol/ABC/Enum/…) for a base expression."""
    node = _unwrap_base(base)
    if isinstance(node, ast.Name):
        name = node.id
        return import_aliases.get(name, name)
    if isinstance(node, ast.Attribute):
        return _attr_dotted(node)
    return None


def _is_interface_marker(marker: str) -> bool:
    return marker.rsplit(".", 1)[-1] in _INTERFACE_LEAVES


def _is_enum_marker(marker: str) -> bool:
    return marker.rsplit(".", 1)[-1] in _ENUM_LEAVES


def _type_name_worthy(raw: str) -> bool:
    if not raw or raw == "(dynamic)":
        return False
    leaf = raw.rsplit(".", 1)[-1]
    if leaf in _SKIP_TYPE_NAMES or raw in _SKIP_TYPE_NAMES:
        return False
    if "." in raw:
        return True
    return bool(leaf) and leaf[0].isupper()


def parse_file(path: str, declarations_only: bool = False) -> dict[str, Any]:
    qpath = to_posix(path)
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        return {"path": qpath, "ok": False, "error": f"cannot read file: {exc}"}

    try:
        tree = ast.parse(text, filename=qpath)
    except SyntaxError as exc:
        msg = exc.msg or "invalid syntax"
        return {"path": qpath, "ok": False, "error": f"syntax error: {msg}"}

    # ast.Module has no end_lineno; File/Namespace spans cover the source text (PHP/TS do the same).
    line_end = max(len(text.splitlines()), 1)
    mod = module_name(qpath)
    is_package_init = qpath.endswith("/__init__.py") or qpath == "__init__.py"
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []

    nodes.append(
        {
            "kind": "File",
            "name": Path(qpath).name,
            "qualified_name": qpath,
            "file_path": qpath,
            "line_start": 1,
            "line_end": line_end,
        }
    )

    # Graph container for module-level symbols: Namespace for a package __init__, else the File.
    root_container = qpath
    if is_package_init and mod:
        pkg_name = mod.rsplit(".", 1)[-1]
        nodes.append(
            {
                "kind": "Namespace",
                "name": pkg_name,
                "qualified_name": mod,
                "file_path": qpath,
                "line_start": 1,
                "line_end": line_end,
            }
        )
        edges.append(
            {
                "kind": "CONTAINS",
                "source_qname": qpath,
                "target_raw": mod,
                "file_path": qpath,
                "line": 1,
            }
        )
        root_container = mod

    # Same-file name → qname map (ambiguous names fall back to bare).
    declared: dict[str, str | None] = {}
    method_qnames: set[str] = set()
    # Same-file base qnames for ``super().m()`` resolution (020).
    class_bases: dict[str, list[str]] = {}
    # Classification markers per class (Protocol/ABC/Enum / import aliases / bare names).
    class_base_markers: dict[str, list[str]] = {}
    # Local import name → marker (Protocol/ABC/Enum) or imported symbol name.
    import_aliases: dict[str, str] = {}
    class_kind: dict[str, str] = {}
    interface_qnames: set[str] = set()

    def remember(name: str, qname: str) -> None:
        if name in declared:
            declared[name] = None
        else:
            declared[name] = qname

    def note_import_alias(local: str, imported: str, module: str | None) -> None:
        leaf = imported.rsplit(".", 1)[-1]
        if module in ("typing", "abc") and leaf in ("Protocol", "ABC"):
            import_aliases[local] = f"{module}.{leaf}"
        elif module == "enum" and leaf == "Enum":
            import_aliases[local] = "enum.Enum"
        elif leaf in ("Protocol", "ABC", "Enum"):
            import_aliases[local] = leaf
        else:
            import_aliases[local] = imported

    def collect_imports(stmt: ast.AST) -> None:
        if isinstance(stmt, ast.Import):
            for alias in stmt.names:
                local = alias.asname or alias.name.split(".", 1)[0]
                # ``import typing`` / ``import enum as e`` — Attribute bases use the module name.
                import_aliases[local] = alias.name
            return
        if isinstance(stmt, ast.ImportFrom):
            module = stmt.module
            for alias in stmt.names:
                if alias.name == "*":
                    continue
                local = alias.asname or alias.name
                note_import_alias(local, alias.name, module)

    def collect(stmt: ast.AST, class_qname: str | None, func_qname: str | None) -> None:
        if isinstance(stmt, (ast.Import, ast.ImportFrom)):
            collect_imports(stmt)
            return
        if isinstance(stmt, ast.ClassDef):
            qn = (
                member(class_qname, stmt.name)
                if class_qname is not None
                else dotted(mod, stmt.name)
            )
            remember(stmt.name, qn)
            bases: list[str] = []
            markers: list[str] = []
            for base in stmt.bases:
                marker = _marker_from_base_expr(base, import_aliases=import_aliases)
                if marker is not None:
                    markers.append(marker)
                node = _unwrap_base(base)
                if isinstance(node, ast.Name):
                    local = declared.get(node.id)
                    bases.append(local if local else node.id)
                elif isinstance(node, ast.Attribute):
                    bases.append(_attr_dotted(node))
            class_bases[qn] = bases
            class_base_markers[qn] = markers
            for child in stmt.body:
                collect(child, qn, None)
        elif isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if class_qname is not None:
                qn = member(class_qname, stmt.name)
                method_qnames.add(qn)
            elif func_qname is not None:
                qn = member(func_qname, stmt.name)
            else:
                qn = dotted(mod, stmt.name)
            remember(stmt.name, qn)
            for child in stmt.body:
                collect(child, class_qname, qn)
        elif isinstance(stmt, (ast.Assign, ast.AnnAssign)):
            targets: list[ast.expr] = []
            if isinstance(stmt, ast.Assign):
                targets = list(stmt.targets)
            elif isinstance(stmt, ast.AnnAssign) and stmt.target is not None:
                targets = [stmt.target]
            for target in targets:
                if isinstance(target, ast.Name):
                    if class_qname is not None:
                        remember(target.id, member(class_qname, target.id))
                    elif _is_upper_const(target.id):
                        remember(target.id, dotted(mod, target.id))
        elif isinstance(stmt, ast.If):
            for nested in (*stmt.body, *stmt.orelse):
                collect(nested, class_qname, func_qname)
        elif isinstance(stmt, (ast.For, ast.AsyncFor, ast.While)):
            for nested in (*stmt.body, *stmt.orelse):
                collect(nested, class_qname, func_qname)
        elif isinstance(stmt, (ast.With, ast.AsyncWith)):
            for nested in stmt.body:
                collect(nested, class_qname, func_qname)
        elif isinstance(stmt, ast.Try):
            for nested in stmt.body:
                collect(nested, class_qname, func_qname)
            for handler in stmt.handlers:
                for nested in handler.body:
                    collect(nested, class_qname, func_qname)
            for nested in (*stmt.orelse, *stmt.finalbody):
                collect(nested, class_qname, func_qname)

    for stmt in tree.body:
        collect(stmt, None, None)

    # Classify ClassDefs after the full collect (bases + aliases available).
    for qn, markers in class_base_markers.items():
        kind = "Class"
        for marker in markers:
            if _is_interface_marker(marker):
                kind = "Interface"
                break
            if _is_enum_marker(marker):
                kind = "Enum"
                break
        class_kind[qn] = kind
        if kind == "Interface":
            interface_qnames.add(qn)

    def resolve_name(name: str) -> str:
        local = declared.get(name)
        if local:
            return local
        if name in declared:
            return name
        return name

    def add_node(
        kind: str,
        name: str,
        qname: str,
        node: ast.AST,
        *,
        modifiers: list[str] | None = None,
        params: list[dict[str, str | None]] | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        row: dict[str, Any] = {
            "kind": kind,
            "name": name,
            "qualified_name": qname,
            "file_path": qpath,
            "line_start": getattr(node, "lineno", 1) or 1,
            "line_end": getattr(node, "end_lineno", None) or getattr(node, "lineno", 1) or 1,
        }
        if modifiers:
            row["modifiers"] = modifiers
        if params is not None:
            row["params"] = params
        if extra:
            row["extra"] = extra
        nodes.append(row)

    def add_edge(
        kind: str,
        source: str,
        target_raw: str,
        node: ast.AST,
        tier: str | None = None,
        *,
        call: ast.Call | None = None,
    ) -> None:
        row: dict[str, Any] = {
            "kind": kind,
            "source_qname": source,
            "target_raw": target_raw,
            "file_path": qpath,
            "line": getattr(node, "lineno", 1) or 1,
        }
        if tier:
            row["confidence_tier"] = tier
        if call is not None and kind in ("CALLS", "NEW"):
            args = _arg_literals(call)
            if args is not None:
                row["args"] = args
                row["arg_keys"] = _arg_keys(call)
        edges.append(row)

    def decorator_target_raw(deco: ast.expr) -> str | None:
        node: ast.expr = deco.func if isinstance(deco, ast.Call) else deco
        if isinstance(node, ast.Name):
            return resolve_name(node.id)
        if isinstance(node, ast.Attribute):
            return _attr_dotted(node)
        return None

    def emit_decorator_refs(owner_qname: str, node: ast.AST) -> None:
        for deco in getattr(node, "decorator_list", []) or []:
            leaf = _decorator_leaf_name(deco)
            if leaf in _MODIFIER_DECORATORS:
                continue
            target = decorator_target_raw(deco)
            if target:
                add_edge("REFERENCES", owner_qname, target, deco)

    def annotation_type_targets(ann: ast.expr) -> list[str]:
        found: list[str] = []

        def consider(raw: str) -> None:
            if _type_name_worthy(raw) and raw not in found:
                found.append(raw)

        def walk(expr: ast.expr) -> None:
            if isinstance(expr, ast.Name):
                consider(resolve_name(expr.id))
                return
            if isinstance(expr, ast.Attribute):
                consider(_attr_dotted(expr))
                return
            if isinstance(expr, ast.Constant):
                return
            if isinstance(expr, ast.BinOp) and isinstance(expr.op, ast.BitOr):
                walk(expr.left)
                walk(expr.right)
                return
            if isinstance(expr, ast.Subscript):
                value = expr.value
                slice_node = expr.slice
                container_name: str | None = None
                if isinstance(value, ast.Name):
                    container_name = value.id
                elif isinstance(value, ast.Attribute):
                    container_name = value.attr
                if container_name not in _STRIP_CONTAINERS:
                    walk(value)
                if isinstance(slice_node, ast.Tuple):
                    for elt in slice_node.elts:
                        walk(elt)
                else:
                    walk(slice_node)
                return
            if isinstance(expr, ast.Tuple):
                for elt in expr.elts:
                    walk(elt)

        walk(ann)
        return found

    def emit_annotation_refs(owner_qname: str, ann: ast.expr | None, at: ast.AST) -> None:
        if ann is None:
            return
        for target in annotation_type_targets(ann):
            add_edge("REFERENCES", owner_qname, target, at)

    def emit_function_annotation_refs(
        owner_qname: str, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> None:
        emit_annotation_refs(owner_qname, node.returns, node)
        args = node.args
        for arg in [*args.posonlyargs, *args.args, *args.kwonlyargs]:
            emit_annotation_refs(owner_qname, arg.annotation, arg)
        if args.vararg is not None:
            emit_annotation_refs(owner_qname, args.vararg.annotation, args.vararg)
        if args.kwarg is not None:
            emit_annotation_refs(owner_qname, args.kwarg.annotation, args.kwarg)

    def base_edge_kind(base: ast.expr, target_raw: str) -> str:
        marker = _marker_from_base_expr(base, import_aliases=import_aliases)
        if marker and _is_interface_marker(marker):
            return "IMPLEMENTS"
        if target_raw in interface_qnames:
            return "IMPLEMENTS"
        # Same-file name that resolves to an Interface.
        if isinstance(base, ast.Name):
            resolved = resolve_name(base.id)
            if resolved in interface_qnames:
                return "IMPLEMENTS"
            leaf = base.id
            aliased = import_aliases.get(leaf)
            if aliased and _is_interface_marker(aliased):
                return "IMPLEMENTS"
        return "EXTENDS"

    def emit_imports(node: ast.Import | ast.ImportFrom) -> None:
        if isinstance(node, ast.Import):
            for alias in node.names:
                target = import_target_raw(
                    module=alias.name, level=0, from_qpath=qpath
                )
                add_edge("IMPORTS", qpath, target, node)
                if alias.asname:
                    # ALIASES is FQN-shaped: prefer the dotted module over the file path.
                    real = (
                        module_name(target)
                        if target.endswith(".py") or target.endswith("/__init__.py")
                        else target
                    )
                    add_edge("ALIASES", dotted(mod, alias.asname), real, node)
            return
        # ImportFrom
        level = node.level or 0
        module = node.module
        # One IMPORTS edge per statement to the module (or the first named relative leaf).
        if level > 0 and module is None and node.names:
            # `from . import x, y` — one IMPORTS per name (each may be its own module).
            for alias in node.names:
                if alias.name == "*":
                    continue
                target = import_target_raw(
                    module=None, level=level, from_qpath=qpath, name=alias.name
                )
                add_edge("IMPORTS", qpath, target, node)
                if alias.asname:
                    add_edge("ALIASES", dotted(mod, alias.asname), target, node)
            return
        target = import_target_raw(module=module, level=level, from_qpath=qpath)
        add_edge("IMPORTS", qpath, target, node)
        for alias in node.names:
            if alias.name == "*" or not alias.asname:
                continue
            # `from a import b as y` — alias points at the imported name under the module.
            resolved_mod = resolve_import(module=module, level=level, from_qpath=qpath)
            if resolved_mod:
                # Prefer symbol qname under the defining module when we know the file.
                real = dotted(module_name(resolved_mod), alias.name)
            elif module:
                real = dotted(module, alias.name)
            else:
                real = alias.name
            add_edge("ALIASES", dotted(mod, alias.asname), real, node)

    def emit_call(node: ast.Call, scope: str, enclosing_class: str | None) -> None:
        func = node.func
        if isinstance(func, ast.Name):
            # ``super()`` alone is not a call edge; ``super().m()`` is handled via Attribute.
            if func.id == "super":
                return
            add_edge("CALLS", scope, resolve_name(func.id), node, call=node)
            return
        if isinstance(func, ast.Attribute):
            method = func.attr
            recv = func.value
            # self.m() / cls.m() with a known enclosing class → same-file Method when present.
            if (
                isinstance(recv, ast.Name)
                and recv.id in ("self", "cls")
                and enclosing_class is not None
            ):
                target = member(enclosing_class, method)
                if target in method_qnames:
                    add_edge("CALLS", scope, target, node, call=node)
                else:
                    add_edge("CALLS", scope, method, node, "HEURISTIC", call=node)
                return
            # super().m() — prefer a same-file base Method; else HEURISTIC bare name.
            if (
                isinstance(recv, ast.Call)
                and isinstance(recv.func, ast.Name)
                and recv.func.id == "super"
                and enclosing_class is not None
            ):
                for base in class_bases.get(enclosing_class, []):
                    target = member(base, method)
                    if target in method_qnames:
                        add_edge("CALLS", scope, target, node, call=node)
                        return
                add_edge("CALLS", scope, method, node, "HEURISTIC", call=node)
                return
            # obj.m() — method name known, receiver not: HEURISTIC ceiling (emit-do-not-gate).
            add_edge("CALLS", scope, method, node, "HEURISTIC", call=node)
            return
        add_edge("CALLS", scope, "(dynamic)", node, "DYNAMIC", call=node)

    def walk_body(
        body: list[ast.stmt],
        container: str,
        scope: str,
        enclosing_class: str | None,
    ) -> None:
        for stmt in body:
            walk_stmt(stmt, container, scope, enclosing_class)

    def walk_stmt(
        stmt: ast.stmt,
        container: str,
        scope: str,
        enclosing_class: str | None,
    ) -> None:
        if isinstance(stmt, (ast.Import, ast.ImportFrom)):
            emit_imports(stmt)
            return

        if isinstance(stmt, ast.ClassDef):
            if enclosing_class is None and container in (qpath, mod):
                qn = dotted(mod, stmt.name)
            elif enclosing_class is not None:
                qn = member(enclosing_class, stmt.name)
            else:
                qn = dotted(mod, stmt.name)
            kind = class_kind.get(qn, "Class")
            add_node(kind, stmt.name, qn, stmt)
            add_edge("CONTAINS", container, qn, stmt)
            emit_decorator_refs(qn, stmt)
            for base in stmt.bases:
                node = _unwrap_base(base)
                if isinstance(node, ast.Name):
                    base_target = resolve_name(node.id)
                    add_edge(base_edge_kind(base, base_target), qn, base_target, base)
                elif isinstance(node, ast.Attribute):
                    base_target = _attr_dotted(node)
                    add_edge(base_edge_kind(base, base_target), qn, base_target, base)
            walk_body(stmt.body, qn, qn, qn)
            return

        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if enclosing_class is not None:
                kind = "Method"
                qn = member(enclosing_class, stmt.name)
                mods = _method_modifiers(stmt)
            elif container in (qpath, mod):
                kind = "Function"
                qn = dotted(mod, stmt.name)
                mods = _function_modifiers(stmt)
            else:
                # Nested function — Function CONTAINS inside parent.
                kind = "Function"
                qn = member(container, stmt.name)
                mods = _function_modifiers(stmt)
            params = _callable_params(stmt, skip_receiver=kind == "Method")
            ret = _annotation_text(stmt.returns)
            extra = {"type": ret} if ret is not None else None
            add_node(
                kind,
                stmt.name,
                qn,
                stmt,
                modifiers=mods or None,
                params=params,
                extra=extra,
            )
            add_edge("CONTAINS", container, qn, stmt)
            emit_decorator_refs(qn, stmt)
            emit_function_annotation_refs(qn, stmt)
            if not declarations_only:
                walk_body(stmt.body, qn, qn, enclosing_class)
            return

        if isinstance(stmt, (ast.Assign, ast.AnnAssign)):
            targets: list[ast.expr] = []
            if isinstance(stmt, ast.Assign):
                targets = list(stmt.targets)
            elif stmt.target is not None:
                targets = [stmt.target]
            owner_for_ann: str | None = None
            for target in targets:
                if not isinstance(target, ast.Name):
                    continue
                if enclosing_class is not None:
                    qn = member(enclosing_class, target.id)
                    ann = stmt.annotation if isinstance(stmt, ast.AnnAssign) else None
                    typ = _annotation_text(ann)
                    extra = {"type": typ} if typ is not None else None
                    add_node("Property", target.id, qn, stmt, extra=extra)
                    add_edge("CONTAINS", enclosing_class, qn, stmt)
                    owner_for_ann = qn
                elif container in (qpath, mod) and _is_upper_const(target.id):
                    qn = dotted(mod, target.id)
                    ann = stmt.annotation if isinstance(stmt, ast.AnnAssign) else None
                    typ = _annotation_text(ann)
                    extra = {"type": typ} if typ is not None else None
                    add_node("Const", target.id, qn, stmt, extra=extra)
                    add_edge("CONTAINS", container, qn, stmt)
                    owner_for_ann = qn
            if isinstance(stmt, ast.AnnAssign):
                # Class-body / annotated assign → REFERENCES from the Property/Const (or scope).
                src = owner_for_ann or scope
                emit_annotation_refs(src, stmt.annotation, stmt)
            if not declarations_only and isinstance(stmt, ast.Assign) and stmt.value:
                _walk_expr(stmt.value, scope, enclosing_class)
            elif not declarations_only and isinstance(stmt, ast.AnnAssign) and stmt.value:
                _walk_expr(stmt.value, scope, enclosing_class)
            return

        if not declarations_only:
            for child in ast.iter_child_nodes(stmt):
                if isinstance(child, ast.stmt):
                    walk_stmt(child, container, scope, enclosing_class)
                else:
                    _walk_expr(child, scope, enclosing_class)

    def _walk_expr(expr: ast.AST, scope: str, enclosing_class: str | None) -> None:
        if isinstance(expr, ast.Call):
            emit_call(expr, scope, enclosing_class)
        for child in ast.iter_child_nodes(expr):
            _walk_expr(child, scope, enclosing_class)

    for stmt in tree.body:
        walk_stmt(stmt, root_container, root_container, None)

    return {"path": qpath, "ok": True, "nodes": nodes, "edges": edges}
