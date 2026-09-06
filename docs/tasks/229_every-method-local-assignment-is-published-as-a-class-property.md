---
id: 229
slug: every-method-local-assignment-is-published-as-a-class-property
title: 'A bare-name assignment anywhere inside a method body is emitted as a `Property` of the enclosing class, because the Assign branch tests `enclosing_class is not None` and never the container — 4,384 of a 1,209-file repo''s 17,516 nodes (25 %) are method locals published as class members, and the sibling `Const` arm three lines below already makes the container test this branch is missing'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [020, 217, 011]
---

## Why this exists

`walk_stmt`'s `Assign`/`AnnAssign` branch decides what an assignment declares from **who encloses
it** rather than **what contains it** (`adapters/python/src/parse.py:652-657`):

```python
if enclosing_class is not None:
    qn = member(enclosing_class, target.id)
    add_node("Property", target.id, qn, stmt)
    add_edge("CONTAINS", enclosing_class, qn, stmt)
elif container in (qpath, mod) and _is_upper_const(target.id):
    ...
```

`enclosing_class` is threaded through a method body unchanged — `walk_body(stmt.body, qn, qn,
enclosing_class)` (`parse.py:639`) — so it stays truthy for every statement at every depth inside
every method. A local variable therefore becomes a class member. **The `elif` immediately below it
does make the container test**, and the `FunctionDef` branch above it makes the same one
(`parse.py:625-628`); only the `Property` arm reads the enclosing class where it means the
container.

**Reproduced in five lines** through `adapters/python/index.py --file`:

```python
class Widget:
    kind = "w"
    def render(self):
        tmp = self.kind
        return tmp
```
```
NODE  Property m.Widget::kind line 2      <- correct
NODE  Property m.Widget::tmp  line 4      <- a local in render()
EDGE  CONTAINS m.Widget -> m.Widget::tmp
```

**Measured on a 1,209-file repo** (index built with the Python + SQL adapters; every Property node
joined back to its own file's AST and classified by whether its line is a direct class-body
statement or a statement inside a method of that class):

| Property nodes | | |
|---|---:|---:|
| real class-body attribute | 2,943 | 40.2 % |
| **method-local variable** | **4,384** | **59.8 %** |

That is **25.0 % of all 17,516 nodes in the graph**, plus 4,384 `CONTAINS` edges asserting them, and
the largest single node kind in the index (7,327) is the one that is majority wrong.

**What it costs the reader.** `search_symbol("Entity")` on that index returns `total_count: 1873`
and its first page is one real class followed by four `TestUnitEntity::entity`-shaped Property nodes
— locals in test methods. The correct answer is present and outranked by noise the adapter
invented. Every ranked surface pays this: `file_outline`, `read_symbol` on a class, the class
diagram's member lists, and every node-count denominator in `get_index_status`.

**This is Python-specific and not a contract question.** PHP declares a property with a visibility
keyword and TypeScript with a class-body field, so neither adapter can confuse the two; in Python
`self.kind` in a class body and `tmp` in a method body are the same `ast.Assign` node and only the
container distinguishes them.

## Scope

1. **Test the container, not the enclosure.** The `Property` arm fires when the assignment's
   container **is** the class — the same `container in (…)` shape the `Const` arm and the
   `FunctionDef` branch already use. Nothing else in the branch changes.
2. **Emit nothing for a method local.** A local is not a member and has no vocabulary of its own;
   the honest output is no node, not a differently-kinded one. No new node kind, no
   `CONTRACT_VERSION` bump (R3).
3. **Leave `self.x = …` alone.** It is an `ast.Attribute` target, not `ast.Name`, so the `continue`
   at `parse.py:650-651` already skips it. Instance attributes assigned in `__init__` are **out of
   scope** — they are a real gap but a different one, and adding them under cover of this fix would
   make the before/after count unreadable.
4. **Keep the annotation path correct.** `owner_for_ann` feeds `emit_annotation_refs`
   (`parse.py:662-665`); an annotated local still gets its `REFERENCES` edge, sourced from the
   enclosing scope rather than from a Property that no longer exists.

**Not in scope:** instance attributes (Scope 3); `Const` detection; any other adapter; the
`Property` kind itself, which is correct vocabulary for the 2,943 that are real.

## Acceptance criteria

- **AC1 (R6.5 — prove the guard fails first).** The five-line fixture above asserts
  `m.Widget::tmp` **exists** against today's adapter, and `m.Widget::kind` exists too. Without the
  red row a green test proves only that the file parses.
- **AC2** After the change `m.Widget::kind` is unchanged — same qname, kind, line and `CONTAINS`
  edge — and `m.Widget::tmp` and its `CONTAINS` edge are gone.
- **AC3** Nested depth is covered: a local inside an `if`, a `for`, a `with` and a nested `def`
  within a method emits no Property. The defect is depth-independent, so the fixture must be too.
- **AC4** A module-level `UPPER = 1` still emits `Const`, and a class-body annotated attribute still
  emits its `REFERENCES` edge (Scope 4) — pinned so the fix cannot be read as "stop emitting from
  Assign".
- **AC5** Every existing Python adapter fixture is byte-identical apart from removed method-local
  Property nodes and their `CONTAINS` edges, and the removals are enumerated in the PR (R4.2). **A
  drop in node count is the expected result, not a regression** — the PR states the before/after.

## Exclusions

- **E1** The 4,384 / 17,516 measurement is from a **local, private checkout**
  (`~/WORKSPACE/PROJECTS/InCloud/valance-system/valance-backend`, `develop` @ `7ba652d4`) and is not
  reproducible from this repo. The committed artifact is AC1's fixture; the re-run method is
  recorded above (join each `Property` node to its file's AST, classify by class-body vs method-body
  line). `cross_repo_samples.json` pins no Python sample — shared open item with 226/227.

## Notes

**Why the count matters more than the kind error.** A wrong node kind on a few symbols is a quality
complaint; a quarter of the graph being invented members is a **denominator** problem. Coverage
percentages, orphan counts, module fan-in and the token cost of every payload that lists members are
all computed over a node population that is 25 % fiction, and none of those numbers can be trusted
until this lands.

**Relationship to 226/227.** Independent. 226 links edges that exist, 227 adds a type table, this
one deletes nodes that should never have been emitted. Landing it first makes 226's and 227's
before/after measurements readable, because it moves the denominator they are measured against.
