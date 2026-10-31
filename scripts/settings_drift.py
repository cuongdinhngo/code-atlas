"""Repo settings drift (424): read the live settings back and compare them with the standard.

`docs/SECURITY_STANDARD.md` rows carry `set: <name> = <value>` items. Those items are the only
expected values (R6.7); `READERS` is the only list of names this script can read, and
`tests/test_security_standard.py` refuses a `set:` name that is not in it. The live values come
from `gh api` through an injectable `fetch`, so the tests run on JSON fixtures with no network.

    GH_TOKEN=<fine-grained token> python3 scripts/settings_drift.py [--repo owner/name] [--local]

Exit 0 no drift, 1 drift (each named), 2 the check could not run (no token, an unreadable setting,
a `set:` name no reader knows). A check that cannot run must not read as a pass (R6.5).
Stdlib only: the scheduled workflow runs it on the runner's own `python3`.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
STANDARD = REPO / "docs" / "SECURITY_STANDARD.md"
SECRET = "SETTINGS_READ_TOKEN"
TOKEN_NEEDED = (
    f"no token: set the repository secret {SECRET} (a fine-grained personal access token on this "
    "repository with Administration: read, plus Secret scanning alerts: read) and pass it as "
    "GH_TOKEN. The workflow's own GITHUB_TOKEN cannot read rulesets, collaborators or "
    "security_and_analysis."
)

Fetch = Callable[[str], Any]
Reader = Callable[[Fetch, str], str]
SET_ITEM = re.compile(r"^(?P<name>[a-z][a-z0-9_.]*)\s*=\s*(?P<value>\S.*?)\s*$")


class SettingsError(Exception):
    """The check cannot run; the message says why and what to do."""


def _flag(value: object) -> str:
    return "true" if value else "false"


def _status(value: object) -> str:
    return str(value) if value else "absent"


def _csv(values: list[str]) -> str:
    return ",".join(sorted(values)) or "none"


def _ruleset(fetch: Fetch, repo: str, target: str, ref: str) -> dict[str, Any] | None:
    """The one ruleset of ``target`` kind whose conditions include ``ref`` (by effect, not name)."""
    for brief in fetch(f"repos/{repo}/rulesets"):
        full = fetch(f"repos/{repo}/rulesets/{brief['id']}")
        include = full.get("conditions", {}).get("ref_name", {}).get("include", [])
        if full.get("target") == target and ref in include:
            return dict(full)
    return None


def _rule_types(ruleset: dict[str, Any] | None) -> set[str]:
    return {rule["type"] for rule in (ruleset or {}).get("rules", [])}


def _ruleset_reader(target: str, ref: str, rule: str) -> Reader:
    return lambda fetch, repo: _flag(_rule_types(_ruleset(fetch, repo, target, ref)) >= {rule})


def _required_checks(fetch: Fetch, repo: str) -> str:
    found = _ruleset(fetch, repo, "branch", "~DEFAULT_BRANCH")
    checks = [
        c["context"]
        for rule in (found or {}).get("rules", [])
        if rule["type"] == "required_status_checks"
        for c in rule["parameters"]["required_status_checks"]
    ]
    return _csv(checks)


def _bypass(target: str, ref: str) -> Reader:
    def read(fetch: Fetch, repo: str) -> str:
        found = _ruleset(fetch, repo, target, ref) or {}
        actors = [
            f"{a['actor_type']}:{a['actor_id']}:{a['bypass_mode']}"
            for a in found.get("bypass_actors", [])
        ]
        return _csv(actors)

    return read


def _security(key: str) -> Reader:
    def read(fetch: Fetch, repo: str) -> str:
        analysis = fetch(f"repos/{repo}").get("security_and_analysis") or {}
        return _status((analysis.get(key) or {}).get("status"))

    return read


def _private_reporting(fetch: Fetch, repo: str) -> str:
    enabled = fetch(f"repos/{repo}/private-vulnerability-reporting").get("enabled")
    return "enabled" if enabled else "disabled"


def _sha_pinning(fetch: Fetch, repo: str) -> str:
    return _flag(fetch(f"repos/{repo}/actions/permissions").get("sha_pinning_required"))


def _admins(fetch: Fetch, repo: str) -> str:
    people = fetch(f"repos/{repo}/collaborators?affiliation=direct&per_page=100")
    return _csv([p["login"] for p in people if p.get("role_name") == "admin"])


_MAIN = ("branch", "~DEFAULT_BRANCH")
_TAGS = ("tag", "refs/tags/v*")

# The only names a `set:` item may use. Add a reader here before a row can cite the setting.
READERS: Mapping[str, Reader] = {
    "rulesets.main.deletion": _ruleset_reader(*_MAIN, "deletion"),
    "rulesets.main.non_fast_forward": _ruleset_reader(*_MAIN, "non_fast_forward"),
    "rulesets.main.pull_request": _ruleset_reader(*_MAIN, "pull_request"),
    "rulesets.main.required_checks": _required_checks,
    "rulesets.main.bypass": _bypass(*_MAIN),
    "rulesets.tags.deletion": _ruleset_reader(*_TAGS, "deletion"),
    "rulesets.tags.update": _ruleset_reader(*_TAGS, "update"),
    "rulesets.tags.non_fast_forward": _ruleset_reader(*_TAGS, "non_fast_forward"),
    "rulesets.tags.bypass": _bypass(*_TAGS),
    "private_vulnerability_reporting": _private_reporting,
    "secret_scanning": _security("secret_scanning"),
    "secret_scanning_push_protection": _security("secret_scanning_push_protection"),
    "dependabot_security_updates": _security("dependabot_security_updates"),
    "actions.sha_pinning_required": _sha_pinning,
    "admins": _admins,
}


def parse_set_item(value: str) -> tuple[str, str] | None:
    """``name = value`` of one `set:` item, or None when it is not that shape."""
    match = SET_ITEM.match(value)
    return (match["name"], match["value"]) if match else None


def expected_settings(text: str) -> dict[str, tuple[str, str]]:
    """name -> (value, row id) from every `set:` item in the standard's rows."""
    found: dict[str, tuple[str, str]] = {}
    for line in text.splitlines():
        if not re.match(r"^\|\s*SEC-", line):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        for part in (p.strip() for p in cells[-1].split(";")):
            kind, _, rest = part.partition(":")
            if kind.strip() != "set":
                continue
            item = parse_set_item(rest.strip())
            if item is None:
                raise SettingsError(f"{cells[0]}: `set: {rest.strip()}` is not `<name> = <value>`")
            name, value = item
            if name in found and found[name][0] != value:
                raise SettingsError(f"{name} is set to two values: {found[name][1]} and {cells[0]}")
            found[name] = (value, cells[0])
    return found


def drift(expected: Mapping[str, tuple[str, str]], fetch: Fetch, repo: str) -> list[str]:
    """One line per setting whose live value is not the standard's."""
    unknown = sorted(set(expected) - set(READERS))
    if unknown:
        raise SettingsError(f"no reader for {unknown}; add it to READERS or drop the `set:` item")
    cache: dict[str, Any] = {}

    def cached(path: str) -> Any:
        if path not in cache:
            cache[path] = fetch(path)
        return cache[path]

    lines = []
    for name, (want, row) in sorted(expected.items()):
        actual = READERS[name](cached, repo)
        if actual != want:
            lines.append(f"DRIFT {name} ({row}): the standard says {want}, the repo has {actual}")
    return lines


def gh_fetch(path: str) -> Any:
    try:
        done = subprocess.run(
            ["gh", "api", path],
            capture_output=True,
            check=True,
            text=True,
            timeout=60,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as error:
        detail = getattr(error, "stderr", "") or str(error)
        raise SettingsError(f"cannot read {path}: {detail.strip()}") from error
    return json.loads(done.stdout or "null")


def main(
    argv: list[str],
    fetch: Fetch | None = None,
    env: Mapping[str, str] | None = None,
    standard: Path = STANDARD,
) -> int:
    env = os.environ if env is None else env
    args = list(argv)
    local = "--local" in args
    repo = env.get("GITHUB_REPOSITORY", "")
    if "--repo" in args:
        repo = args[args.index("--repo") + 1]
    try:
        if fetch is None:
            if not env.get("GH_TOKEN") and not local:
                raise SettingsError(TOKEN_NEEDED)
            fetch = gh_fetch
        if not repo:
            raise SettingsError("no repository: pass --repo owner/name or set GITHUB_REPOSITORY")
        expected = expected_settings(standard.read_text(encoding="utf-8"))
        if not expected:
            raise SettingsError("the standard holds no `set:` item; the check would pass vacuously")
        lines = drift(expected, fetch, repo)
    except SettingsError as error:
        print(f"settings drift: cannot run: {error}")
        return 2
    if lines:
        print("\n".join(lines))
        print(f"settings drift: {len(lines)} of {len(expected)} setting(s) differ")
        return 1
    print(f"settings drift: none ({len(expected)} setting(s) match the standard)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
