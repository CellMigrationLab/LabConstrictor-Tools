"""The per-app host expectations of the release sandbox (expected_hosts.json), for the workflow and the host drivers.

    python expected_hosts.py env --app-name NAME [--repo OWNER/NAME] [--override notebook,napari]
        prints KEY=VALUE lines for $GITHUB_ENV: EXPECT_HOSTS, EXPECT_NAPARI, EXPECT_FIJI, EXPECT_QUPATH (listed | not_listed),
        TOOLS_MODULE (required | optional)
    python expected_hosts.py validate

An app with no row (and no --override) is refused, never defaulted to "listed everywhere". Standard library only: it runs
on the runner's own Python before the app is installed.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PATH = Path(__file__).resolve().parent / "expected_hosts.json"
HOSTS = ("notebook", "napari", "fiji", "qupath")
GUI_HOSTS = ("napari", "fiji", "qupath")
TOOLS_MODULE = ("required", "optional")


def load(path: Path = PATH) -> dict[str, Any]:
    """The expectations, validated (ValueError listing the problems)."""
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    problems = validate(data)
    if problems:
        raise ValueError("%s is malformed:\n  %s" % (path.name, "\n  ".join(problems)))
    return data


def validate(data: Any) -> list[str]:
    """Problems with the file (an empty list means valid). Never raises."""
    if (
        not isinstance(data, dict)
        or data.get("expected_hosts") != 1
        or not isinstance(data.get("apps"), dict)
    ):
        return ["the file must be an object with expected_hosts 1 and an 'apps' object"]
    problems: list[str] = []
    for name, row in data["apps"].items():
        hosts = row.get("hosts") if isinstance(row, dict) else None
        if (
            not isinstance(hosts, list)
            or not hosts
            or not all(h in HOSTS for h in hosts)
            or len(set(hosts)) != len(hosts)
        ):
            problems.append(
                "%s: hosts must be a non-empty list of unique names from %s" % (name, list(HOSTS))
            )
        if not isinstance(row, dict) or row.get("tools_module") not in TOOLS_MODULE:
            problems.append("%s: tools_module must be one of %s" % (name, list(TOOLS_MODULE)))
        if not isinstance(row, dict) or not isinstance(row.get("repo"), str) or "/" not in row["repo"]:
            problems.append("%s: repo must be owner/name" % name)
    return problems


def parse_hosts(text: str) -> list[str]:
    """`--override notebook,napari` -> the list; ValueError for an unknown or repeated name."""
    hosts = [part.strip() for part in text.split(",")]
    if not all(h in HOSTS for h in hosts) or len(set(hosts)) != len(hosts):
        raise ValueError("--override must be unique names from %s, got %r" % (list(HOSTS), text))
    return hosts


def expectation(data: dict[str, Any], app_name: str, repo: str = "", override: str = "") -> dict[str, Any]:
    """{hosts, napari, fiji, qupath, tools_module} for one app: the row of the file, or the override for a new app.
    Raises ValueError when the app has no row and no override, or when the repository is not the one of the row.
    """
    row = data["apps"].get(app_name)
    if row is None:
        if not override:
            raise ValueError(
                "%r has no row in expected_hosts.json and no override was given: add the row (hosts from its "
                "labconstrictor-app.yaml) or pass the expected_hosts input; the sandbox never assumes 'listed everywhere'"
                % app_name
            )
        row = {"hosts": parse_hosts(override), "tools_module": "required", "repo": repo}
    elif override:
        row = {**row, "hosts": parse_hosts(override)}
    elif repo and repo.lower() != row["repo"].lower():
        raise ValueError(
            "%r is the app of %s in expected_hosts.json, not of %s" % (app_name, row["repo"], repo)
        )
    return {
        "hosts": list(row["hosts"]),
        **{host: "listed" if host in row["hosts"] else "not_listed" for host in GUI_HOSTS},
        "tools_module": row["tools_module"],
    }


def env_lines(found: dict[str, Any]) -> list[str]:
    return [
        "EXPECT_HOSTS=%s" % ",".join(found["hosts"]),
        *("EXPECT_%s=%s" % (host.upper(), found[host]) for host in GUI_HOSTS),
        "TOOLS_MODULE=%s" % found["tools_module"],
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=["env", "validate"])
    parser.add_argument("--app-name", default="")
    parser.add_argument("--repo", default="")
    parser.add_argument("--override", default="")
    args = parser.parse_args(argv)
    try:
        data = load()
        if args.command == "env":
            print("\n".join(env_lines(expectation(data, args.app_name, args.repo, args.override))))
    except ValueError as problem:
        print("expected_hosts: %s" % problem, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
