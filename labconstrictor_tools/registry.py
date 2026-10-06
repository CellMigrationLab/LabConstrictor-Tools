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
import tempfile
from collections.abc import Sequence
from pathlib import Path

from .structures import AppSchema, RegistryEntry

SUPPORTED_PROTOCOLS = (1,)
PROBE_TIMEOUT_S = 60  # asking an interpreter whether it already has labconstrictor_tools
REGISTER_TIMEOUT_S = 120  # generating the schema = importing the app's tool module


# ---------------------------------------------------------------- locations
def home() -> Path:
    # absolute: a relative LC_HOME would silently move the registry whenever the process changes its working directory
    return Path(os.environ.get("LC_HOME") or (Path.home() / ".labconstrictor")).expanduser().absolute()


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
    extra = [
        Path(p).expanduser().absolute() for p in os.environ.get("LC_APPS_PATH", "").split(os.pathsep) if p
    ]
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


def _runtime_needed(interpreter: str | Path) -> bool:
    """False if the app's own interpreter already has labconstrictor_tools. Then nothing may be added to its PYTHONPATH:
    runtime_path() is the *registering* interpreter's site-packages, whose numpy/pandas/... would shadow the app's own.
    If the probe itself fails (cannot start, times out) we cannot tell: assume the runtime is needed, and say so in the log.
    """
    try:
        done = subprocess.run(
            [str(interpreter), "-I", "-c", "import labconstrictor_tools"],
            capture_output=True,
            timeout=PROBE_TIMEOUT_S,
        )
        return done.returncode != 0
    except (OSError, subprocess.SubprocessError) as error:
        from . import log

        log.warning(
            "could not probe %s for labconstrictor_tools (%s: %s); assuming it is needed",
            interpreter,
            type(error).__name__,
            error,
        )
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
    from . import log

    try:
        result = subprocess.run(
            command, capture_output=True, text=True, env=env, encoding="utf-8", timeout=REGISTER_TIMEOUT_S
        )
    except subprocess.TimeoutExpired as error:
        log.error("register %s timed out after %s s command=%s", name, REGISTER_TIMEOUT_S, command)
        raise RuntimeError(
            "schema generation for %s timed out after %s s (interpreter %s, module %s): importing the tool module is "
            "slow or hangs; check it with `labconstrictor-tools check --module %s`"
            % (name, REGISTER_TIMEOUT_S, interpreter, module, module)
        ) from error
    if result.returncode:

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


def _write_atomic(path: Path, text: str) -> None:
    """Readers (hosts) may look at the folder at any moment: never expose a half-written file. The temporary file has a
    unique name and is created exclusively: a pre-planted file or symlink with a predictable name cannot redirect the write.
    """
    descriptor, name = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".", suffix=".tmp")
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
        if os.name == "posix":
            os.chmod(
                temporary, 0o644
            )  # not the umask's choice: with 0002 (Ubuntu's default) readers would reject our own entry as group-writable
        os.replace(temporary, path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


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
        except (OSError, ValueError) as error:
            owner = None
            from . import log

            log.warning(
                "unregister %s --prefix %s: the entry cannot be read (%s: %s), so its owner is unknown; removing the unusable entry",
                name,
                prefix,
                type(error).__name__,
                error,
            )
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
def _file_reason(path: Path, user_dir: bool, what: str) -> str | None:
    """POSIX ownership and permission policy for a file hosts read to decide what to start."""
    if os.name != "posix":
        return None
    info = path.stat()
    # per-user entries must be ours; entries in shared folders (LC_APPS_PATH, /etc) may also belong to root (the administrator)
    owners = {os.getuid()} if user_dir else {os.getuid(), 0}
    if info.st_uid not in owners:
        return "%s is not owned by the current user" % what + ("" if user_dir else " or root")
    if info.st_mode & 0o022:
        return "%s is writable by other users" % what
    return None


def _world_writable(path: str, directory: bool) -> bool:
    """Writable by everybody (a directory with the sticky bit, like /tmp, only lets owners replace their own files)."""
    mode = os.stat(path).st_mode
    return bool(mode & 0o002) and not (directory and mode & 0o1000)


def _untrusted_reason(entry_file: Path, entry: RegistryEntry) -> str | None:
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
        user_dir = entry_file.parent == apps_dir()
        reason = _file_reason(entry_file, user_dir, "entry file")
        if reason:
            return reason
        schema_file = Path(entry["schema_path"])
        if os.path.normcase(os.path.abspath(schema_file.parent)) != os.path.normcase(
            os.path.abspath(entry_file.parent)
        ):
            return "schema file %s is not in the same folder as the entry" % schema_file
        if schema_file.exists():  # a missing schema is reported later, with its own message
            reason = _file_reason(schema_file, user_dir, "schema file")
            if reason:
                return reason
        # anybody who can replace the interpreter (or its folders) can run code as the user the next time a host starts the app
        for path, directory, label in (
            (python, False, "interpreter"),
            (os.path.dirname(python), True, "interpreter folder"),
            (prefix, True, "install prefix"),
        ):
            if os.path.exists(path) and _world_writable(path, directory):
                return "%s %s is writable by everybody" % (label, path)
    return None


def _validated_entry(entry: object) -> RegistryEntry:
    """A registry file is untrusted JSON: check the shape before any field is used (raises ValueError with the reason)."""
    if not isinstance(entry, dict):
        raise ValueError("the entry is not a JSON object")
    for key in ("name", "python", "prefix", "module", "schema_path"):
        if not isinstance(entry.get(key), str) or not entry[key]:
            raise ValueError("field %r must be a non-empty string" % key)
    path_list = entry.setdefault("pythonpath", [])
    if not isinstance(path_list, list) or not all(isinstance(x, str) for x in path_list):
        raise ValueError("field 'pythonpath' must be a list of strings")
    if not isinstance(entry.setdefault("runtime_path", ""), str):
        raise ValueError("field 'runtime_path' must be a string")
    entry.setdefault("display_name", entry["name"])
    entry.setdefault("version", "")
    return entry  # type: ignore[return-value]


def _validated_schema(schema: object) -> AppSchema:
    """The cached schema is untrusted JSON too (raises ValueError with the reason)."""
    if not isinstance(schema, dict):
        raise ValueError("schema is not a JSON object")
    if schema.get("protocol") not in SUPPORTED_PROTOCOLS:
        raise ValueError(
            "schema protocol %r is not supported (this host speaks %s)"
            % (schema.get("protocol"), SUPPORTED_PROTOCOLS)
        )
    tools = schema.get("tools")
    if not isinstance(tools, list) or not all(
        isinstance(t, dict)
        and isinstance(t.get("id"), str)
        and isinstance(t.get("label"), str)
        and isinstance(t.get("inputs"), list)
        and isinstance(t.get("outputs"), list)
        for t in tools
    ):
        raise ValueError(
            "schema has an unexpected structure (tools must be a list of {id, label, inputs, outputs})"
        )
    return schema  # type: ignore[return-value]


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
                entry = _validated_entry(json.loads(entry_file.read_text(encoding="utf-8")))
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
            except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
                problems.append((name, "unreadable entry (%s: %s)" % (type(error).__name__, error)))
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
        loaded = json.loads(Path(entry["schema_path"]).read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ValueError("schema unreadable (%s)" % error) from error
    return _validated_schema(loaded)


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
