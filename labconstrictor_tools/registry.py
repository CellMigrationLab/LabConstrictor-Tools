"""Registry of installed LabConstrictor apps: one `<name>.json` entry plus a cached `<name>.schema.json` per app.

Written by an app's post-install step (which also caches the generated schema, so hosts can list tools and build GUIs
without starting Python) and removed by its uninstall step.

Where entries are looked up (first match for a name wins, so a user can override a shared install):
  1. the per-user directory      ~/.labconstrictor/apps            (override the root with LC_HOME)
  2. directories in LC_APPS_PATH (os.pathsep-separated; e.g. a folder on a network share maintained by an administrator)
  3. the system directory        %ProgramData%\\LabConstrictor\\apps | /Library/Application Support/LabConstrictor/apps | /etc/labconstrictor/apps

Readers never trust an entry blindly. An entry is *skipped and reported* (never silently, never hiding other apps) when:
its interpreter is missing on this machine, it is not owned by the current user / is writable by others (POSIX user dir),
its interpreter is not inside its own install prefix, or its schema is unreadable or has a protocol this host does not speak.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

SUPPORTED_PROTOCOLS = (1,)


# ---------------------------------------------------------------- locations
def home():
    return Path(os.environ.get("LC_HOME") or (Path.home() / ".labconstrictor"))


def apps_dir():
    """The per-user directory that `register` writes to."""
    return home() / "apps"


def system_dir():
    if os.name == "nt":
        return Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData")) / "LabConstrictor" / "apps"
    if sys.platform == "darwin":
        return Path("/Library/Application Support/LabConstrictor/apps")
    return Path("/etc/labconstrictor/apps")


def search_dirs():
    """Directories searched for entries, highest priority first."""
    extra = [Path(p) for p in os.environ.get("LC_APPS_PATH", "").split(os.pathsep) if p]
    seen, ordered = set(), []
    for directory in [apps_dir(), *extra, system_dir()]:
        if str(directory) not in seen:
            seen.add(str(directory))
            ordered.append(directory)
    return ordered


# ---------------------------------------------------------------- writing
def python_for(prefix):
    p = Path(prefix)
    for c in (p / "python.exe", p / "Scripts" / "python.exe", p / "bin" / "python"):
        if c.exists():
            return c
    return p / ("python.exe" if os.name == "nt" else "bin/python")


def runtime_path():
    """Directory that contains the `labconstrictor_tools` package (put on the worker's PYTHONPATH)."""
    return str(Path(__file__).resolve().parent.parent)


def _check_name(name):
    """An app name becomes a file name in the registry: refuse anything that could point outside of it."""
    if not name or name in (".", "..") or any(c in name for c in "/\\\0") or name != name.strip():
        raise ValueError("invalid app name %r: it must be a plain name without path separators" % (name,))
    return name


def register(name, prefix, module, version="", pythonpath=(), display_name=None, directory=None):
    """Register an installed app: generate its schema with the app's own interpreter, cache it, write the entry."""
    _check_name(name)
    interpreter = python_for(prefix)
    env = {
        **os.environ,
        "PYTHONPATH": os.pathsep.join([runtime_path(), *map(str, pythonpath)]),
        "PYTHONNOUSERSITE": "1",
    }
    command = [str(interpreter), "-m", "labconstrictor_tools", "describe", "--module", module]
    command += ["--application", display_name or name, "--version", version]
    result = subprocess.run(command, capture_output=True, text=True, env=env, encoding="utf-8")
    if result.returncode:
        from . import log

        log.error(
            "register %s failed (exit %s) command=%s\n%s", name, result.returncode, command, result.stderr
        )
        raise RuntimeError(
            "schema generation failed for %s (interpreter %s, module %s):\n%s"
            % (name, interpreter, module, result.stderr)
        )
    target = Path(directory) if directory else apps_dir()
    target.mkdir(parents=True, exist_ok=True)
    schema_path = target / (name + ".schema.json")
    _write_atomic(schema_path, result.stdout)
    entry = {
        "schema": 1,
        "name": name,
        "display_name": display_name or name,
        "version": version,
        "prefix": str(prefix),
        "python": str(interpreter),
        "module": module,
        "pythonpath": [str(x) for x in pythonpath],
        "runtime_path": runtime_path(),
        "schema_path": str(schema_path),
    }
    _write_atomic(
        target / (name + ".json"), json.dumps(entry, indent=2)
    )  # entry last: it is what makes the app visible
    return entry


def _write_atomic(path, text):
    """Readers (hosts) may look at the folder at any moment: never expose a half-written file."""
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def unregister(name, directory=None):
    _check_name(name)
    removed = False
    target = Path(directory) if directory else apps_dir()
    for filename in (name + ".json", name + ".schema.json"):
        path = target / filename
        if path.exists():
            path.unlink()
            removed = True
    return removed


# ---------------------------------------------------------------- reading
def _untrusted_reason(entry_file, entry):
    """Why an entry must not be used to start a process, or None if it looks fine."""
    # Compare normalised paths WITHOUT following symlinks: a virtualenv's python legitimately links to a base interpreter.
    prefix, python = os.path.abspath(entry["prefix"]), os.path.abspath(entry["python"])
    try:
        inside = os.path.commonpath([os.path.normcase(prefix), os.path.normcase(python)]) == os.path.normcase(
            prefix
        )
    except ValueError:  # e.g. different drives on Windows
        inside = False
    if not inside:
        return "interpreter %s is not inside the install prefix %s" % (python, prefix)
    if os.name == "posix":
        info = entry_file.stat()
        # per-user entries must be ours; entries in shared folders (LC_APPS_PATH, /etc) may also belong to root (the administrator)
        owners = {os.getuid()} if entry_file.parent == apps_dir() else {os.getuid(), 0}
        if info.st_uid not in owners:
            return "entry file is not owned by the current user" + (
                "" if entry_file.parent == apps_dir() else " or root"
            )
        if info.st_mode & 0o022:
            return "entry file is writable by other users"
    return None


def load_entries():
    """-> ({name: entry} for every usable app, [(name, reason)] for every app that had to be skipped)."""
    entries, problems = {}, []
    for directory in search_dirs():
        if not directory.is_dir():
            continue
        for entry_file in sorted(directory.glob("*.json")):
            if entry_file.name.endswith(".schema.json"):
                continue
            name = entry_file.stem
            if name in entries or any(name == p[0] for p in problems):
                continue  # an earlier (higher priority) directory already provided this app
            try:
                entry = json.loads(entry_file.read_text(encoding="utf-8"))
                name = entry["name"]
                if name in entries or any(name == p[0] for p in problems):
                    continue  # the file name differs from the app name it claims: priority still goes to the earlier directory
                if not Path(entry["python"]).exists():
                    problems.append(
                        (name, "not available on this machine (interpreter %s is missing)" % entry["python"])
                    )
                    continue
                reason = _untrusted_reason(entry_file, entry)
                if reason:
                    problems.append((name, "ignored: " + reason))
                    continue
                entries[name] = entry
            except (OSError, ValueError, KeyError) as error:
                problems.append((name, "unreadable entry (%s)" % error))
    _log_problems(problems)
    return entries, problems


_LOGGED_PROBLEMS = set()


def _log_problems(problems):
    """Each skipped app is logged once per session with the reason (not on every rescan)."""
    from . import log

    for name, reason in problems:
        if (name, reason) not in _LOGGED_PROBLEMS:
            _LOGGED_PROBLEMS.add((name, reason))
            log.warning("app %r skipped: %s", name, reason)


def load_all():
    """Usable entries only (see `load_entries` for the reasons others are skipped)."""
    return load_entries()[0]


def schema(app):
    """The cached schema of one app. Raises ValueError with a readable reason if it cannot be used."""
    entry = load_all()[app]
    try:
        schema = json.loads(Path(entry["schema_path"]).read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ValueError("schema unreadable (%s)" % error) from error
    if schema.get("protocol") not in SUPPORTED_PROTOCOLS:
        raise ValueError(
            "schema protocol %r is not supported (this host speaks %s)"
            % (schema.get("protocol"), SUPPORTED_PROTOCOLS)
        )
    return schema


def load_schemas():
    """-> ({app: schema} for every usable app, [(app, reason)] for every app that had to be skipped, for any reason)."""
    entries, problems = load_entries()
    schemas = {}
    for name in entries:
        try:
            schemas[name] = schema(name)
        except ValueError as error:
            problems.append((name, str(error)))
    return schemas, problems
