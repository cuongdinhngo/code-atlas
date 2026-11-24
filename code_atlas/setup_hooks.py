"""``code-atlas-setup`` — install the hooks that keep the index fresh, or say they are absent (453).

Three parts, each idempotent: a marked block in each git hook that refreshes the index; the Claude
Code hooks in ``.claude/settings.local.json`` unless the plugin already provides them; and the
adapter commands this shell exports, added to the user file every hook reads (452). What it did is
recorded in ``.code-atlas/setup.json``, which ``get_index_status`` reads to say ``unguarded``.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import sys
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from code_atlas import gitutil
from code_atlas.build_info import package_version
from code_atlas.config import ADAPTER_CMD_ENV, ADAPTER_CMD_TABLE, user_config_path
from code_atlas.containment import make_private_dir, safe_write
from code_atlas_hooks.table import GATE, HOOKS

GIT_HOOKS = ("post-merge", "post-checkout", "post-commit", "post-rewrite")
# Git passes a branch checkout `1`; a rewrite says why — an amend is post-commit's already (355).
_CONDITION = {"post-checkout": ' && [ "$3" = "1" ]', "post-rewrite": ' && [ "$1" != "amend" ]'}
BEGIN = "# >>> code-atlas (code-atlas-setup) >>>"
END = "# <<< code-atlas <<<"
_SHELLS = frozenset({"sh", "bash", "dash", "zsh", "ksh"})
RECORD_NAME = "setup.json"
SETTINGS_FILE = Path(".claude") / "settings.local.json"
SHARED_SETTINGS = Path(".claude") / "settings.json"
PLUGIN_PREFIX = "code-atlas@"
SETUP_ROUTE = "code-atlas-setup"
OK, MISSING, FAILED = 0, 1, 2
WOULD_WRITE = "would write"  # a dry run or --check: a part setup has not installed yet


@dataclass(frozen=True)
class Part:
    """One line of the report: what, its state (`ok`, `wrote`, `skipped`, `missing`), and why."""

    name: str
    state: str
    why: str = ""

    def line(self) -> str:
        mark = {"ok": "✅", "wrote": "✅", "skipped": "⚠"}.get(self.state, "❌")
        return f"{mark} {self.name}: {self.state}" + (f" — {self.why}" if self.why else "")


def refresh_command() -> str | None:
    """The absolute path of ``code-atlas-refresh`` for this install: a hook needs no PATH (452)."""
    return script_path("code-atlas-refresh")


def script_path(name: str) -> str | None:
    """One of this install's console scripts by absolute path, or None when it is not installed."""
    found = shutil.which(name)
    if found:
        return str(Path(found).resolve())
    beside = Path(sys.executable).parent
    for candidate in (name, f"{name}.exe"):
        if (beside / candidate).is_file():
            return str((beside / candidate).resolve())
    return None


def hook_block(hook: str, refresh: str) -> str:
    """The marked block: background refresh; its skips go to ``.code-atlas/refresh.log``."""
    command = refresh.replace("'", "'\\''")
    return (
        f"{BEGIN}\n"
        f"if [ -f .code-atlas/graph.db ]{_CONDITION.get(hook, '')}; then\n"
        f"  ( '{command}' --trigger {hook} >/dev/null 2>>.code-atlas/refresh.log & )\n"
        f"fi\n{END}\n"
    )


def _is_shell(text: str) -> bool:
    first = text.splitlines()[0] if text else ""
    words = first[2:].split() if first.startswith("#!") else []
    names = [Path(word).name for word in words[:2]]
    return bool(names) and (
        names[0] in _SHELLS or (names[0] == "env" and len(names) > 1 and names[1] in _SHELLS)
    )


def _without_block(text: str) -> str:
    pattern = re.compile(rf"\n?{re.escape(BEGIN)}\n.*?{re.escape(END)}\n?", re.DOTALL)
    return pattern.sub("\n", text).rstrip("\n") + "\n"


def _with_block(text: str, block: str) -> str:
    """In place on a re-run; else right after the shebang, so an `exit` or `exec` cannot skip it."""
    if BEGIN in text and END in text:
        start, end = text.index(BEGIN), text.index(END) + len(END) + 1
        return text[:start] + block + text[end:]
    head, _, rest = text.partition("\n")
    return f"{head}\n{block}{rest}" if head.startswith("#!") else block + text


def git_parts(root: Path, refresh: str | None, *, dry_run: bool, remove: bool) -> list[Part]:
    """Write, check or remove the block in each git hook; never in a non-shell hook."""
    found = gitutil.hooks_dir(root)
    if found is None:
        return [Part("git hooks", "skipped", "not a git checkout")]
    directory, scope = found
    if scope == "global":
        why = (
            "core.hooksPath is global; add the block to those hooks by hand, it reaches every repo"
        )
        return [Part("git hooks", "skipped", why)]
    if refresh is None and not remove:
        return [Part("git hooks", "missing", "code-atlas-refresh not on PATH: install code-atlas")]
    parts: list[Part] = []
    for hook in GIT_HOOKS:
        path = directory / hook
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        if text and not _is_shell(text):
            parts.append(
                Part(f"git hook {hook}", "skipped", "not a shell script; add the block by hand")
            )
            continue
        if remove:
            wanted = _without_block(text) if BEGIN in text else text
        else:
            wanted = _with_block(text or "#!/bin/sh\n", hook_block(hook, str(refresh)))
        if wanted == text:
            parts.append(Part(f"git hook {hook}", "ok"))
            continue
        if dry_run:
            parts.append(Part(f"git hook {hook}", WOULD_WRITE, f"{path} — run {SETUP_ROUTE}"))
            continue
        make_private_dir(directory)
        safe_write(path, wanted)
        path.chmod(0o755)
        parts.append(Part(f"git hook {hook}", "wrote", str(path)))
    return parts


def plugin_enabled(root: Path, home: Path | None) -> bool:
    """The most specific settings file naming the plugin decides, as Claude Code resolves it."""
    files = [root / SHARED_SETTINGS, root / SETTINGS_FILE]
    if home is not None:
        files.insert(0, home / ".claude" / "settings.json")
    enabled = False
    for path in files:
        plugins = _json(path).get("enabledPlugins")
        if isinstance(plugins, dict):
            for key, value in plugins.items():
                if str(key).startswith(PLUGIN_PREFIX):
                    enabled = value is True
    return enabled


def _json(path: Path) -> dict[str, object]:
    return _object(path) or {}


def _object(path: Path) -> dict[str, object] | None:
    """The file's JSON object; None when absent, unreadable or not an object (`{}` is one)."""
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return loaded if isinstance(loaded, dict) else None


def _ours(entry: object) -> bool:
    hooks = entry.get("hooks") if isinstance(entry, dict) else None
    return (
        isinstance(hooks, list)
        and bool(hooks)
        and all(isinstance(h, dict) and str(h.get("command", "")).startswith(GATE) for h in hooks)
    )


def claude_part(root: Path, home: Path | None, *, dry_run: bool, remove: bool) -> Part:
    """The snippet's hooks in the personal settings file, unless the plugin or the repo has them."""
    name = "Claude Code hooks"
    if not remove and plugin_enabled(root, home):
        return Part(name, "ok", "the code-atlas plugin provides them")
    shared = _json(root / SHARED_SETTINGS).get("hooks")
    if (
        not remove
        and isinstance(shared, dict)
        and any(
            _ours(entry)
            for entries in shared.values()
            if isinstance(entries, list)
            for entry in entries
        )
    ):
        return Part(name, "ok", f"{SHARED_SETTINGS.as_posix()} carries them")
    path = root / SETTINGS_FILE
    if path.is_file() and _object(path) is None and path.read_text(encoding="utf-8").strip():
        return Part(name, "skipped", f"{SETTINGS_FILE.as_posix()} is not a JSON object")
    data = _json(path)
    before = json.dumps(data, sort_keys=True)
    raw = data.get("hooks")
    hooks: dict[str, list[object]] = dict(raw) if isinstance(raw, dict) else {}
    for event in HOOKS if not remove else list(hooks):
        kept = [e for e in hooks.get(event, []) if not _ours(e)]
        hooks[event] = kept if remove else kept + list(HOOKS[event])
        if not hooks[event]:
            del hooks[event]
    if hooks:
        data["hooks"] = hooks
    else:
        data.pop("hooks", None)
    if json.dumps(data, sort_keys=True) == before:
        return Part(name, "ok")
    if dry_run:
        return Part(name, WOULD_WRITE, f"{SETTINGS_FILE.as_posix()} — run {SETUP_ROUTE}")
    make_private_dir(path.parent)
    safe_write(path, json.dumps(data, indent=2) + "\n")
    return Part(name, "wrote", SETTINGS_FILE.as_posix())


def adapter_part(env: Mapping[str, str], *, dry_run: bool) -> Part:
    """Add each ``CA_<LANG>_CMD`` this shell exports to the user file; never a recorded one."""
    name = "adapter commands"
    path = user_config_path(env)
    if path is None:
        return Part(name, "skipped", "no HOME, XDG_CONFIG_HOME or APPDATA to find the user file")
    try:
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        table = tomllib.loads(text).get(ADAPTER_CMD_TABLE, {}) if text else {}
    except (OSError, ValueError) as error:
        return Part(name, "skipped", f"{path}: {error}")
    known = {str(key).lower() for key in table}
    new = {}
    for variable, value in sorted(env.items()):
        found = ADAPTER_CMD_ENV.fullmatch(variable)
        if found and value.strip() and found.group(1).lower() not in known:
            new[found.group(1).lower()] = value
    if not new:
        return Part(name, "ok" if known else "skipped", "" if known else f"none set; see {path}")
    lines = [
        f"{lang} = {json.dumps(shlex.split(cmd, posix=os.name != 'nt'))}"
        for lang, cmd in new.items()
    ]
    head = text.rstrip("\n") + "\n" if text else f"[{ADAPTER_CMD_TABLE}]\n"
    if dry_run:
        return Part(name, WOULD_WRITE, f"{', '.join(new)} → {path} — run {SETUP_ROUTE}")
    make_private_dir(path.parent)
    safe_write(path, head + "\n".join(lines) + "\n")
    return Part(name, "wrote", f"{', '.join(new)} → {path}")


def record_path(root: Path) -> Path:
    return root / ".code-atlas" / RECORD_NAME


def write_record(
    root: Path,
    parts: list[Part],
    *,
    declined: bool,
    guard: str | None = None,
    rebuild: str | None = None,
) -> None:
    """What setup did, beside the index; read back as untrusted data by ``guard_gaps``."""
    hooks = sorted(
        p.name.removeprefix("git hook ")
        for p in parts
        if p.name.startswith("git hook ") and p.state in ("ok", "wrote")
    )
    from code_atlas.hooks.guard import mode_of

    mode = guard or mode_of(root)  # a re-run keeps the mode already chosen (454)
    consent = rebuild or rebuild_consent(root)  # and the rebuild consent (455)
    body = {
        "version": package_version(),
        "declined": declined,
        "hooks": hooks,
        "guard": mode,
        "rebuild": consent,
    }
    make_private_dir(record_path(root).parent)
    safe_write(record_path(root), json.dumps(body, indent=2) + "\n", root=root)


def rebuild_consent(root: Path) -> str:
    """``auto`` only when setup recorded `--auto-rebuild` (455); read as data: one value counts."""
    return "auto" if _json(record_path(root)).get("rebuild") == "auto" else "ask"


def guard_gaps(root: Path) -> list[str] | None:
    """What keeps this index from staying fresh: ``None`` when guarded or declined (453).

    The record is the repo's own file, so it is read as data: only known hook names count, and
    the hooks are found again through git rather than through any path the record holds.
    """
    record = _json(record_path(root))
    if not record:
        return ["no setup"]
    if record.get("declined") is True:
        return None
    if record.get("version") != package_version():
        return ["setup from another release"]
    listed = record.get("hooks")
    hooks = [h for h in listed if h in GIT_HOOKS] if isinstance(listed, list) else []
    found = gitutil.hooks_dir(root) if hooks else None
    gaps = []
    for hook in hooks:
        path = found[0] / hook if found else None
        if path is None or not path.is_file() or BEGIN not in path.read_text(encoding="utf-8"):
            gaps.append(hook)
    return gaps or None


def run(
    root: Path,
    env: Mapping[str, str],
    *,
    dry_run: bool = False,
    remove: bool = False,
    guard: str | None = None,
    rebuild: str | None = None,
) -> list[Part]:
    """Every part, in order; records the result unless this is a dry run or a removal."""
    home = Path(env["HOME"]) if env.get("HOME") else None
    parts = git_parts(root, refresh_command(), dry_run=dry_run, remove=remove)
    parts.append(claude_part(root, home, dry_run=dry_run, remove=remove))
    if not remove:
        parts.append(adapter_part(env, dry_run=dry_run))
    if remove and not dry_run:
        record_path(root).unlink(missing_ok=True)
    elif not dry_run:
        write_record(root, parts, declined=False, guard=guard, rebuild=rebuild)
    return parts


def decline(root: Path) -> None:
    """``--no-hooks``: remember the choice so ``unguarded`` is not repeated for it."""
    write_record(root, [], declined=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="code-atlas-setup", description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="report only; exit 1 when a part is missing"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="say what would change, change nothing"
    )
    parser.add_argument(
        "--remove", action="store_true", help="take out every block and hook setup wrote"
    )
    parser.add_argument(
        "--no-hooks", action="store_true", help="record that this repo goes without"
    )
    parser.add_argument(
        "--guard",
        choices=("off", "nudge", "refuse"),
        help="what a symbol-shaped grep meets: nothing, a nudge (default), or a refusal (454)",
    )
    consent = parser.add_mutually_exclusive_group()
    consent.add_argument(
        "--auto-rebuild",
        action="store_const",
        const="auto",
        dest="rebuild",
        help="let a session start a background full rebuild when the contract moves or the index "
        "is incomplete — minutes of CPU on a large repo, the old index answering meanwhile (455)",
    )
    consent.add_argument(
        "--no-auto-rebuild", action="store_const", const="ask", dest="rebuild", help="the default"
    )
    args = parser.parse_args(argv)
    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()
    if args.no_hooks:
        decline(root)
        print("code-atlas setup: recorded --no-hooks; get_index_status will not say unguarded")
        return OK
    if args.check:
        gaps = guard_gaps(root)
        parts = run(root, os.environ, dry_run=True)
        for part in parts:
            print(part.line())
        print("code-atlas setup: " + (f"unguarded — {', '.join(gaps)}" if gaps else "guarded"))
        return MISSING if gaps or any(p.state in (WOULD_WRITE, "missing") for p in parts) else OK
    parts = run(
        root,
        os.environ,
        dry_run=args.dry_run,
        remove=args.remove,
        guard=args.guard,
        rebuild=args.rebuild,
    )
    for part in parts:
        print(part.line())
    return FAILED if any(p.state == "missing" for p in parts) else OK


if __name__ == "__main__":
    raise SystemExit(main())
