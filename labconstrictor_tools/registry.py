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
from collections.abc import Sequence
from pathlib import Path

from .structures import AppSchema, RegistryEntry

SUPPORTED_PROTOCOLS = (1,)


# ---------------------------------------------------------------- locations
def home() -> Path:
    return Path(os.environ.get("LC_HOME") or (Path.home() / ".labconstrictor"))


def apps_dir() -> Path:
    """The per-user directory that `register` writes to."""
    return home() / "apps"


def system_dir() -> Path:
    if os.name == "nt":
        return Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData")) / "LabConstrictor" / "apps"
    if sys.platform == "darwin":
        return Path("/Library/Application Support/LabConstrictor/apps")
    return Path("/etc/labconstrictor/apps")


def search_dirs() -> list[Path]:
    """Directories searched for entries, highest priority first."""
    extra = [Path(p) for p in os.environ.get("LC_APPS_PATH", "").split(os.pathsep) if p]
    seen, ordered = set(), []
    for directory in [apps_dir(), *extra, system_dir()]:
        if str(directory) not in seen:
            seen.add(str(directory))
            ordered.append(directory)
    return ordered


# ---------------------------------------------------------------- writing
def python_for(prefix: str | Path) -> Path:
    p = Path(prefix)
    for c in (p / "python.exe", p / "Scripts" / "python.exe", p / "bin" / "python"):
        if c.exists():
            return c
    return p / ("python.exe" if os.name == "nt" else "bin/python")


def runtime_path() -> str:
    """Directory that contains the `labconstrictor_tools` package (put on the worker's PYTHONPATH)."""
    return str(Path(__file__).resolve().parent.parent)


def _check_name(name):
    """An app name becomes a file name in the registry: refuse anything that could point outside of it."""
    if not name or name in (".", "..") or any(c in name for c in "/\\\0") or name != name.strip():
        raise ValueError("invalid app name %r: it must be a plain name without path separators" % (name,))
    return name


def _runtime_needed(interpreter):
    """False if the app's own interpreter already has labconstrictor_tools. Then nothing may be added to its PYTHONPATH:
    runtime_path() is the *registering* interpreter's site-packages, whose numpy/pandas/... would shadow the app's own.
    """
    try:
        done = subprocess.run(
            [str(interpreter), "-I", "-c", "import labconstrictor_tools"], capture_output=True, timeout=60
        )
        return done.returncode != 0
    except (OSError, subprocess.SubprocessError):
        return True


def register(
    name: str,
    prefix: str | Path,
    module: str,
    version: str = "",
    pythonpath: Sequence[str | Path] = (),
    display_name: str | None = None,
    directory: str | Path | None = None,
) -> RegistryEntry:
    """Register an installed app: generate its schema with the app's own interpreter, cache it, write the entry."""
    _check_name(name)
    interpreter = python_for(prefix)
    runtime = runtime_path() if _runtime_needed(interpreter) else ""
    env = {
        **os.environ,
        "PYTHONPATH": os.pathsep.join(x for x in (runtime, *map(str, pythonpath)) if x),
        "PYTHONNOUSERSITE": "1",
        "PYTHONSAFEPATH": "1",
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
    entry: RegistryEntry = {
        "schema": 1,
        "name": name,
        "display_name": display_name or name,
        "version": version,
        "prefix": str(prefix),
        "python": str(interpreter),
        "module": module,
        "pythonpath": [str(x) for x in pythonpath],
        "runtime_path": runtime,
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
    if os.name == "posix":
        os.chmod(
            temporary, 0o644
        )  # not the umask's choice: with 0002 (Ubuntu's default) readers would reject our own entry as group-writable
    os.replace(temporary, path)


def unregister(name: str, directory: str | Path | None = None, prefix: str | Path | None = None) -> bool:
    """Remove an app. With `prefix`, only if the entry still belongs to that install: a second install of the same app
    (another prefix, e.g. an upgrade in a new folder) registered later must survive the first one's uninstall.
    """
    _check_name(name)
    removed = False
    target = Path(directory) if directory else apps_dir()
    if prefix is not None:
        try:
            owner = json.loads((target / (name + ".json")).read_text(encoding="utf-8")).get("prefix")
        except (OSError, ValueError):
            owner = None
        if owner is not None and os.path.normcase(os.path.abspath(owner)) != os.path.normcase(
            os.path.abspath(prefix)
        ):
            return False
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
    if Path(prefix).parent == Path(prefix):  # "/" or "C:\\": containment would prove nothing
        return "the install prefix %s is a filesystem root" % prefix
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


def load_entries() -> tuple[dict[str, RegistryEntry], list[tuple[str, str]]]:
    """-> ({name: entry} for every usable app, [(name, reason)] for every app that had to be skipped)."""
    entries: dict[str, RegistryEntry] = {}
    problems: list[tuple[str, str]] = []
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
            except FileNotFoundError:
                continue  # unregistered while we were scanning: the app is simply gone
            except (OSError, ValueError, KeyError) as error:
                problems.append((name, "unreadable entry (%s)" % error))
    _log_problems(problems)
    return entries, problems


_LOGGED_PROBLEMS: set[tuple[str, str]] = set()


def _log_problems(problems):
    """Each skipped app is logged once per session with the reason (not on every rescan)."""
    from . import log

    for name, reason in problems:
        if (name, reason) not in _LOGGED_PROBLEMS:
            _LOGGED_PROBLEMS.add((name, reason))
            log.warning("app %r skipped: %s", name, reason)


def load_all() -> dict[str, RegistryEntry]:
    """Usable entries only (see `load_entries` for the reasons others are skipped)."""
    return load_entries()[0]


def schema(app: str, entries: dict[str, RegistryEntry] | None = None) -> AppSchema:
    """The cached schema of one app. Raises ValueError with a readable reason if it cannot be used.
    `entries` (from load_entries) avoids re-scanning the registry for every app."""
    entry = (entries if entries is not None else load_all())[app]
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


def load_schemas() -> tuple[dict[str, AppSchema], list[tuple[str, str]]]:
    """-> ({app: schema} for every usable app, [(app, reason)] for every app that had to be skipped, for any reason)."""
    entries, problems = load_entries()
    schemas = {}
    for name in entries:
        try:
            schemas[name] = schema(name, entries)
        except ValueError as error:
            problems.append((name, str(error)))
    return schemas, problems
