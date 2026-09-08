"""Local type facts, file-at-a-time (task 227; mirrors TS ``types.js`` / PHP TypeTable).

Every binding comes from the language putting the type in the file — a parameter/attribute
annotation, or ``x = Foo()`` — never a checker and never a framework (R2). A member call
``obj.method()`` then resolves to ``<Class>::method`` instead of a bare HEURISTIC name.
"""

from __future__ import annotations

import ast


def type_ref_name(ann: ast.expr | None) -> str | None:
    """Simple class name a type annotation names: ``Foo`` / ``Foo[T]`` → ``\"Foo\"``."""
    if ann is None:
        return None
    node: ast.expr = ann
    if isinstance(node, ast.Subscript):
        node = node.value
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def new_expr_class(expr: ast.expr | None, *, known_classes: set[str] | None = None) -> str | None:
    """Class a ``Foo()`` initializer names when ``Foo`` is a known class; else None.

    Python has no ``new`` keyword, so a bare call is only treated as a constructor when the
    callee's simple name is in ``known_classes`` (same-file Class/Enum/Interface). A call to an
    unknown or non-class name re-opens the binding (flow-forgetful, 137/153).
    """
    if not isinstance(expr, ast.Call):
        return None
    func = expr.func
    name: str | None = None
    if isinstance(func, ast.Name):
        name = func.id
    elif isinstance(func, ast.Attribute):
        name = func.attr
    if name is None:
        return None
    if known_classes is not None and name not in known_classes:
        return None
    return name


def bound_class(
    ann: ast.expr | None,
    initializer: ast.expr | None,
    *,
    known_classes: set[str] | None = None,
) -> str | None:
    """Annotation wins; else an inferred ``Foo()`` against known classes; else None."""
    return type_ref_name(ann) or new_expr_class(initializer, known_classes=known_classes)


def param_type_map(node: ast.FunctionDef | ast.AsyncFunctionDef) -> dict[str, str]:
    """Typed parameters → name→class; untyped parameters bind nothing. Seeds a fresh local scope."""
    out: dict[str, str] = {}
    args = node.args
    for arg in [*args.posonlyargs, *args.args, *args.kwonlyargs]:
        cls = type_ref_name(arg.annotation)
        if cls:
            out[arg.arg] = cls
    return out


def class_prop_type_map(body: list[ast.stmt]) -> dict[str, str]:
    """Typed instance attributes in a class body → name→class (``x: Foo`` / ``self.x: Foo``)."""
    out: dict[str, str] = {}
    for stmt in body:
        if not isinstance(stmt, ast.AnnAssign) or stmt.target is None:
            continue
        cls = type_ref_name(stmt.annotation)
        if not cls:
            continue
        target = stmt.target
        if isinstance(target, ast.Name):
            out[target.id] = cls
        elif (
            isinstance(target, ast.Attribute)
            and isinstance(target.value, ast.Name)
            and target.value.id in ("self", "cls")
        ):
            out[target.attr] = cls
    return out


def _self_attr(target: ast.expr) -> str | None:
    """``self.x`` / ``cls.x`` → ``"x"``; anything else → None."""
    if (
        isinstance(target, ast.Attribute)
        and isinstance(target.value, ast.Name)
        and target.value.id in ("self", "cls")
    ):
        return target.attr
    return None


def class_self_types(
    body: list[ast.stmt], *, known_classes: set[str] | None = None
) -> dict[str, str]:
    """What the CLASS says its ``self.<attr>`` are — one map, read-only, order-independent.

    Read in a single pass over the class body *and* every method in it, so a `self._x: Foo` in
    `__init__` is known to a method declared above it. Two rules keep the answer a property of
    the class rather than of the reading order:

    * An annotation outranks an inferred ``self.x = Foo()`` — the annotation is the declaration.
    * Within a rank, disagreement drops the attribute. Absence is honest; picking the
      last-visited method's opinion is not (R5.2).
    """
    annotated: dict[str, str] = {}
    inferred: dict[str, str] = {}
    conflicting: set[str] = set()
    forgotten: set[str] = set()

    def note(target: ast.expr, ann: ast.expr | None, value: ast.expr | None) -> None:
        attr = _self_attr(target)
        if attr is None:
            return
        declared = type_ref_name(ann)
        if declared:
            if annotated.get(attr, declared) != declared:
                conflicting.add(attr)
            annotated[attr] = declared
            return
        guessed = new_expr_class(value, known_classes=known_classes) if value else None
        if guessed:
            if inferred.get(attr, guessed) != guessed:
                conflicting.add(attr)
            inferred[attr] = guessed
        elif value is not None:
            # An untyped write of something unrecognised: the class does not say what this is.
            forgotten.add(attr)

    for stmt in ast.walk(ast.Module(body=body, type_ignores=[])):
        if isinstance(stmt, ast.AnnAssign) and stmt.target is not None:
            note(stmt.target, stmt.annotation, stmt.value)
        elif isinstance(stmt, ast.Assign):
            for target in stmt.targets:
                note(target, None, stmt.value)

    out = {**{k: v for k, v in inferred.items() if k not in forgotten}, **annotated}
    for attr in conflicting:
        out.pop(attr, None)
    return out


def receiver_class(
    expr: ast.expr,
    locals_: dict[str, str],
    self_props: dict[str, str],
) -> str | None:
    """Class a call receiver evaluates to from the local table, or None when untyped."""
    if isinstance(expr, ast.Name):
        return locals_.get(expr.id)
    if (
        isinstance(expr, ast.Attribute)
        and isinstance(expr.value, ast.Name)
        and expr.value.id in ("self", "cls")
    ):
        return self_props.get(expr.attr)
    return None
