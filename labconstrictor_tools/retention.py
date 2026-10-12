"""Retention under LC_HOME: which result and run folders may be removed, and the one place that removes them.

The policy is written in docs/SPEC_WRONG_SCIENCE.md, section 3. In short:

* Hosts (Napari, Fiji, QuPath, notebooks) never delete anything under `<LC_HOME>/results` or `<LC_HOME>/runs`. They create a
  folder, write `.lc-owner.json` first and `.lc-done.json` last (`write_owner`, `write_done` are the reference writers), then
  start `labconstrictor-tools prune` in a subprocess.
* `prune` removes a folder only when ALL of this holds: it is a direct child of the root with a name of `A-Za-z0-9_.-`, a real
  directory (not a symlink, junction or other reparse point) whose real parent is the real root; it carries a valid owner
  marker whose `name` is the folder's own name; it carries a done marker; and this process holds the retention lock.
  Foreign folders, legacy folders without a marker, folders without a done marker (active or crashed), links and files are
  never touched and never use up the quota.
* Eligible folders are ordered by the marker's `created` then by name; the newest `RESULTS_KEPT` / `RUN_RECORDS_KEPT` stay.
* A removal is a rename to `.lc-deleting-<token>` inside the root, then a removal that never follows a link. A leftover of an
  interrupted removal is finished by the next prune.
* `--dry-run` reports exactly what would be removed and changes nothing (it does not even take the lock).

Standard library only.
"""

import json
import os
import re
import stat
import sys
import uuid
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import log, registry

if sys.platform == "win32":
    import msvcrt
else:
    import fcntl

RESULTS_KEPT = 20  # owned, finished result folders kept (SPEC_WRONG_SCIENCE 3.3)
RUN_RECORDS_KEPT = 50  # owned, finished run records kept
OWNER_FILE = ".lc-owner.json"
DONE_FILE = ".lc-done.json"
LOCK_FILE = ".retention.lock"  # in LC_HOME, never inside a root
DELETING_PREFIX = ".lc-deleting-"
MARKER_VERSION = 1
MAX_MARKER_BYTES = 64 * 1024  # a marker is a few hundred bytes; anything bigger is not one
STATUSES = ("ok", "failed", "cancelled")
LISTED_SKIPS = 20  # how many skipped folders the text report names (JSON has all of them)

# the two roots and their policy: root folder name -> (marker kind, folder quota)
ROOTS: dict[str, tuple[str, int]] = {
    "results": ("result", RESULTS_KEPT),
    "runs": ("run", RUN_RECORDS_KEPT),
}

_NAME = re.compile(r"^[A-Za-z0-9_.-]+$")
_TOKEN = re.compile(
    r"^[A-Za-z0-9_-]{8,64}$"
)  # a uuid4, with or without dashes; it becomes part of a folder name
_CREATED = re.compile(r"^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.(\d{1,9}))?Z$")
_REPARSE_POINT = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)


# ------------------------------------------------------------------ markers (written by the CLI here, by hosts themselves)
def now_utc() -> str:
    """`2026-10-12T09:30:00.123Z`: the format of `created` and `finished`."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def write_owner(folder: Path, kind: str, host: str) -> None:
    """Write `.lc-owner.json` into a folder that was just created (SPEC_WRONG_SCIENCE 3.2). First thing in the folder."""
    marker = {
        "lc_marker": MARKER_VERSION,
        "kind": kind,
        "name": folder.name,
        "host": host,
        "pid": os.getpid(),
        "created": now_utc(),
        "token": str(uuid.uuid4()),
    }
    (folder / OWNER_FILE).write_text(json.dumps(marker), encoding="utf-8")


def write_done(folder: Path, status: str) -> None:
    """Write `.lc-done.json` atomically (temporary file, then rename), last thing in the folder."""
    if status not in STATUSES:
        raise ValueError("status must be one of %s, got %r" % (", ".join(STATUSES), status))
    temporary = folder / (DONE_FILE + ".tmp-%d" % os.getpid())
    temporary.write_text(json.dumps({"finished": now_utc(), "status": status}), encoding="utf-8")
    registry._replace(temporary, folder / DONE_FILE)


def discard_unused(folder: Path) -> bool:
    """Remove a folder that holds nothing but its own owner marker (a run that produced nothing). True if it was removed."""
    try:
        if [p.name for p in folder.iterdir()] != [OWNER_FILE]:
            return False
        (folder / OWNER_FILE).unlink()
        folder.rmdir()
        return True
    except OSError as error:  # leave it: it has no done marker, so prune never touches it either
        log.warning("could not remove the unused folder %s (%s: %s)", folder, type(error).__name__, error)
        return False


# ------------------------------------------------------------------ the report
@dataclass
class RootReport:
    root: Path
    kind: str
    keep: int
    exists: bool = True
    kept: list[str] = field(default_factory=list)  # eligible and inside the quota
    deleted: list[str] = field(default_factory=list)  # removed now (dry run: would be removed)
    skipped: list[tuple[str, str]] = field(default_factory=list)  # (name, why it is never touched)
    failed: list[tuple[str, str]] = field(default_factory=list)  # (name, why a removal did not work)


@dataclass
class PruneReport:
    home: Path
    dry_run: bool
    locked_out: bool = False  # another prune holds the lock (or the share has none): nothing was done
    roots: list[RootReport] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not any(r.failed for r in self.roots)

    def as_dict(self) -> dict[str, Any]:
        return {
            "home": str(self.home),
            "dry_run": self.dry_run,
            "locked_out": self.locked_out,
            "roots": [
                {
                    "root": str(r.root),
                    "kind": r.kind,
                    "keep": r.keep,
                    "exists": r.exists,
                    "kept": r.kept,
                    "deleted": r.deleted,
                    "skipped": [{"name": n, "reason": why} for n, why in r.skipped],
                    "failed": [{"name": n, "reason": why} for n, why in r.failed],
                }
                for r in self.roots
            ],
        }

    def text(self) -> str:
        """The report a person reads."""
        if self.locked_out:
            return "prune: another prune is running (or this folder cannot be locked); nothing was removed."
        verb = "would remove" if self.dry_run else "removed"
        lines = ["prune (dry run: nothing is changed)" if self.dry_run else "prune"]
        for r in self.roots:
            if not r.exists:
                lines.append("%s: %s does not exist, nothing to do" % (r.root.name, r.root))
                continue
            lines.append(
                "%s: %s - keep the newest %d of the finished folders made by LabConstrictor"
                % (r.root.name, r.root, r.keep)
            )
            lines.append("  kept %d, %s %d" % (len(r.kept), verb, len(r.deleted)))
            lines.extend("    %s %s" % (verb, name) for name in r.deleted)
            lines.extend("    FAILED %s: %s" % (name, why) for name, why in r.failed)
            if r.skipped:
                lines.append(
                    "  left alone (not made by LabConstrictor, or not finished): %d" % len(r.skipped)
                )
                lines.extend("    %s: %s" % (name, why) for name, why in r.skipped[:LISTED_SKIPS])
                if len(r.skipped) > LISTED_SKIPS:
                    lines.append("    ... and %d more" % (len(r.skipped) - LISTED_SKIPS))
        return "\n".join(lines)


# ------------------------------------------------------------------ eligibility
@dataclass(frozen=True)
class _Entry:
    path: Path
    name: str
    created: tuple[int, ...]  # sortable form of the marker's `created`
    token: str
    leftover: bool  # a `.lc-deleting-<token>` folder of an interrupted removal


class _Refused(Exception):
    """A folder that must not be removed; the message is the reason shown in the report."""


def _is_link_or_reparse_point(mode: int, attributes: int) -> bool:
    return stat.S_ISLNK(mode) or bool(attributes & _REPARSE_POINT)


def _real_directory(path: Path) -> bool:
    """A real directory by lstat: not a symlink, not a Windows junction or other reparse point."""
    try:
        info = os.lstat(path)
    except OSError:
        return False
    return stat.S_ISDIR(info.st_mode) and not _is_link_or_reparse_point(
        info.st_mode, getattr(info, "st_file_attributes", 0)
    )


def _same_place(real_path: str, other: Path) -> bool:
    return os.path.normcase(real_path) == os.path.normcase(os.path.realpath(other))


def _read_marker(path: Path, label: str) -> dict[str, Any]:
    """A marker is a small regular file (never a link) holding a JSON object."""
    try:
        info = os.lstat(path)
    except FileNotFoundError:
        raise _Refused("no %s" % label) from None
    except OSError as error:
        raise _Refused("%s cannot be read (%s)" % (label, type(error).__name__)) from None
    if not stat.S_ISREG(info.st_mode) or _is_link_or_reparse_point(
        info.st_mode, getattr(info, "st_file_attributes", 0)
    ):
        raise _Refused("%s is not a plain file" % label)
    if info.st_size > MAX_MARKER_BYTES:
        raise _Refused("%s is too big to be a marker" % label)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):  # UnicodeDecodeError and JSONDecodeError are ValueErrors
        raise _Refused("%s is not valid JSON" % label) from None
    if not isinstance(data, dict):
        raise _Refused("%s is not a JSON object" % label)
    return data


def _created_key(text: object) -> tuple[int, ...] | None:
    """`2026-10-12T09:30:00.123Z` -> a tuple that sorts in time order; None when it is not that format."""
    match = _CREATED.match(text) if isinstance(text, str) else None
    if not match:
        return None
    *parts, fraction = match.groups()
    return (*map(int, parts), int((fraction or "0").ljust(9, "0")))


def _inspect(path: Path, root: Path, kind: str) -> _Entry:
    """The eligibility rules of SPEC_WRONG_SCIENCE 3.3 for one entry of a root; raises _Refused with the reason."""
    name = path.name
    leftover = name.startswith(DELETING_PREFIX)
    if not _NAME.match(name) or not name.strip("."):
        raise _Refused("the name has characters outside A-Za-z0-9_.-")
    try:
        info = os.lstat(path)
    except OSError as error:
        raise _Refused("cannot be examined (%s)" % type(error).__name__) from None
    if _is_link_or_reparse_point(info.st_mode, getattr(info, "st_file_attributes", 0)):
        raise _Refused("is a link (symlink or junction)")
    if not stat.S_ISDIR(info.st_mode):
        raise _Refused("is a file, not a folder")
    if not _same_place(os.path.dirname(os.path.realpath(path)), root):
        raise _Refused("does not resolve to a direct child of %s" % root.name)
    owner = _read_marker(path / OWNER_FILE, OWNER_FILE)
    if type(owner.get("lc_marker")) is not int or owner["lc_marker"] != MARKER_VERSION:
        raise _Refused("%s is not a version %d marker" % (OWNER_FILE, MARKER_VERSION))
    if owner.get("kind") != kind:
        raise _Refused(
            "%s is for another kind of folder (%r, this root holds %r)"
            % (OWNER_FILE, owner.get("kind"), kind)
        )
    token = owner.get("token")
    if not isinstance(token, str) or not _TOKEN.match(token):
        raise _Refused("%s has no usable token" % OWNER_FILE)
    if leftover:  # renamed by an interrupted removal: the marker still names the original folder
        if name != DELETING_PREFIX + token or not isinstance(owner.get("name"), str):
            raise _Refused("a .lc-deleting folder whose name is not made from its marker's token")
    elif owner.get("name") != name:
        raise _Refused("%s names another folder (%r): copied or renamed" % (OWNER_FILE, owner.get("name")))
    created = _created_key(owner.get("created"))
    if created is None:
        raise _Refused("%s has no usable 'created' time" % OWNER_FILE)
    done = _read_marker(path / DONE_FILE, DONE_FILE)
    if done.get("status") not in STATUSES:
        raise _Refused("%s has no valid status" % DONE_FILE)
    return _Entry(path, name, created, token, leftover)


def _entries(root: Path, kind: str) -> tuple[list[_Entry], list[tuple[str, str]]]:
    eligible: list[_Entry] = []
    skipped: list[tuple[str, str]] = []
    for child in sorted(root.iterdir(), key=lambda p: p.name):
        try:
            eligible.append(_inspect(child, root, kind))
        except _Refused as why:
            skipped.append((child.name, str(why)))
    return eligible, skipped


# ------------------------------------------------------------------ removal
def _remove_tree(path: Path) -> None:
    """Remove a folder without ever following a link: a link inside it is removed as a link, never its target.
    Read-only files (Windows) are made writable once. Raises OSError for the first thing that cannot be removed.
    """
    with os.scandir(path) as scan:
        children = list(scan)
    for child in children:
        info = child.stat(follow_symlinks=False)
        attributes = getattr(info, "st_file_attributes", 0)
        if stat.S_ISDIR(info.st_mode) and not _is_link_or_reparse_point(info.st_mode, attributes):
            _remove_tree(Path(child.path))
        elif stat.S_ISDIR(info.st_mode) or (attributes & _REPARSE_POINT and sys.platform == "win32"):
            os.rmdir(child.path)  # a junction or directory link on Windows: the link, not what it points to
        else:
            _unlink(child.path)
    os.rmdir(path)


def _unlink(path: str) -> None:
    try:
        os.unlink(path)
    except PermissionError:
        if sys.platform != "win32":
            raise
        os.chmod(path, stat.S_IWRITE)  # a read-only file; any other refusal raises again here
        os.unlink(path)


def _delete(entry: _Entry, root: Path, kind: str) -> None:
    """Rename into `.lc-deleting-<token>`, then remove. Looks again right before, so a folder swapped for a link meanwhile is not followed."""
    current = _inspect(entry.path, root, kind)  # raises _Refused when anything changed since the plan
    target = entry.path if current.leftover else root / (DELETING_PREFIX + current.token)
    if not current.leftover:
        if os.path.lexists(target):
            raise _Refused("%s already exists" % target.name)
        os.rename(entry.path, target)
    if not _real_directory(target):
        raise _Refused("is no longer a real folder after the rename")
    _remove_tree(target)


# ------------------------------------------------------------------ the lock
@contextmanager
def _retention_lock(home: Path) -> Iterator[bool]:
    """One exclusive, non-blocking lock on `<LC_HOME>/.retention.lock`. Yields False when it cannot be taken: another prune holds
    it, or the file system does not support locks (a network share). Never raises for either."""
    flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    try:
        descriptor = os.open(home / LOCK_FILE, flags, 0o600)
    except OSError as error:
        log.warning(
            "prune: cannot open the lock file %s (%s: %s)", home / LOCK_FILE, type(error).__name__, error
        )
        yield False
        return
    try:
        held = _try_lock(descriptor)
        try:
            yield held
        finally:
            if held:
                _unlock(descriptor)
    finally:
        os.close(descriptor)


def _try_lock(descriptor: int) -> bool:
    try:
        if sys.platform == "win32":
            os.lseek(descriptor, 0, os.SEEK_SET)
            msvcrt.locking(descriptor, msvcrt.LK_NBLCK, 1)
        else:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except OSError:  # held by someone else (EWOULDBLOCK, EACCES) or not supported here (ENOLCK, ENOTSUP)
        return False


def _unlock(descriptor: int) -> None:
    try:
        if sys.platform == "win32":
            os.lseek(descriptor, 0, os.SEEK_SET)
            msvcrt.locking(descriptor, msvcrt.LK_UNLCK, 1)
        else:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
    except OSError as error:  # closing the descriptor releases it anyway
        log.logger().debug("prune: could not release the lock: %s: %s", type(error).__name__, error)


# ------------------------------------------------------------------ prune
def prune(
    which: str = "all",
    *,
    dry_run: bool = False,
    home: Path | None = None,
    keep: Mapping[str, int] | None = None,
) -> PruneReport:
    """Apply the retention policy to `results`, `runs` or both (`which`). Never raises for a folder it cannot handle: the report
    says what was removed, kept, left alone and what failed. `keep` overrides the quota per root name (tests only; the policy
    numbers are `RESULTS_KEPT` and `RUN_RECORDS_KEPT`)."""
    if which != "all" and which not in ROOTS:
        raise ValueError("which must be 'results', 'runs' or 'all', got %r" % (which,))
    base = home if home is not None else registry.home()
    names = list(ROOTS) if which == "all" else [which]
    report = PruneReport(base, dry_run)
    if dry_run:  # looking changes nothing, so it needs no lock
        _prune_roots(report, base, names, keep or {})
        return report
    if not any((base / name).is_dir() for name in names):
        _prune_roots(
            report, base, names, keep or {}
        )  # reports that the roots do not exist; creates nothing, not even the lock
        return report
    with _retention_lock(base) as held:
        if not held:
            report.locked_out = True
            return report
        _prune_roots(report, base, names, keep or {})
    return report


def _prune_roots(report: PruneReport, base: Path, names: list[str], keep: Mapping[str, int]) -> None:
    for name in names:
        kind, quota = ROOTS[name]
        root_report = RootReport(base / name, kind, keep.get(name, quota))
        report.roots.append(root_report)
        if (
            not root_report.root.is_dir()
        ):  # a root that is itself a link is the person's own layout: entries are still checked
            root_report.exists = False
            continue
        _prune_one(root_report, report.dry_run)


def _prune_one(report: RootReport, dry_run: bool) -> None:
    try:
        entries, report.skipped = _entries(report.root, report.kind)
    except OSError as error:
        report.failed.append(
            (report.root.name, "cannot list the folder: %s: %s" % (type(error).__name__, error))
        )
        return
    leftovers = [e for e in entries if e.leftover]
    live = sorted((e for e in entries if not e.leftover), key=lambda e: (e.created, e.name))
    cut = max(0, len(live) - report.keep)
    report.kept = [e.name for e in live[cut:]]
    for entry in leftovers + live[:cut]:
        if dry_run:
            report.deleted.append(entry.name)
            continue
        try:
            _delete(entry, report.root, report.kind)
            report.deleted.append(entry.name)
        except (_Refused, OSError) as error:
            why = str(error) if isinstance(error, _Refused) else "%s: %s" % (type(error).__name__, error)
            report.failed.append((entry.name, why))
            log.warning("prune: could not remove %s (%s); it stays", entry.path, why)
