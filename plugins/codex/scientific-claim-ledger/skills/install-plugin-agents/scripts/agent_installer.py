from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import re
import secrets
import shutil
import stat
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

try:
    import fcntl
except ImportError:  # Windows
    fcntl = None

try:
    import msvcrt
except ImportError:  # POSIX
    msvcrt = None

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib


Status = Literal["added", "unchanged", "conflict"]
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)
DIRECTORY = getattr(os, "O_DIRECTORY", 0)
ANCHOR_SUPPORTED = all(
    function in os.supports_dir_fd
    for function in (os.open, os.stat, os.unlink)
)


@dataclass(frozen=True)
class InstallAction:
    path: Path
    status: Status
    sha256: str


@dataclass(frozen=True)
class InstallResult:
    destination: Path
    actions: tuple[InstallAction, ...]
    ledger: Path
    dry_run: bool


@dataclass(frozen=True)
class _Template:
    source: Path
    name: str
    content: bytes
    sha256: str


def _assert_no_symlink_ancestors(path: Path, *, label: str) -> None:
    absolute = path.absolute()
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current /= part
        if current.is_symlink():
            raise ValueError(f"{label} ancestor is a symlink: {current}")


def _load_plugin_metadata(source_dir: Path) -> tuple[str, str]:
    manifest_path = source_dir.parent / ".codex-plugin" / "plugin.json"
    try:
        data = json.loads(_read_regular_nofollow(manifest_path).decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid plugin manifest: {manifest_path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"invalid plugin manifest object: {manifest_path}")
    name = data.get("name")
    version = data.get("version")
    if not isinstance(name, str) or not NAME_RE.fullmatch(name):
        raise ValueError("plugin manifest has an invalid name")
    if not isinstance(version, str) or not version.strip():
        raise ValueError("plugin manifest is missing version")
    return name, version


def _load_templates(source_dir: Path) -> list[_Template]:
    if ".." in source_dir.parts:
        raise ValueError("source directory must not contain '..'")
    if not source_dir.is_dir():
        raise ValueError(f"agent source directory does not exist: {source_dir}")
    for parent in (source_dir.parent, source_dir):
        if parent.is_symlink():
            raise ValueError(f"agent source parent must not be a symlink: {parent}")
    resolved_source = source_dir.resolve()
    templates: list[_Template] = []
    for source in sorted(source_dir.glob("*.toml"), key=lambda path: path.name):
        if source.is_symlink():
            raise ValueError(f"agent template must not be a symlink: {source}")
        if not source.resolve().is_relative_to(resolved_source):
            raise ValueError(f"agent template escapes source directory: {source}")
        try:
            content = _read_regular_nofollow(source)
            data = tomllib.loads(content.decode("utf-8"))
        except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
            raise ValueError(f"invalid agent TOML {source}: {exc}") from exc
        for key in ("name", "description", "developer_instructions"):
            if not isinstance(data.get(key), str) or not data[key].strip():
                raise ValueError(
                    f"invalid agent TOML {source}: missing required key '{key}'"
                )
        templates.append(
            _Template(
                source=source,
                name=source.name,
                content=content,
                sha256=hashlib.sha256(content).hexdigest(),
            )
        )
    if not templates:
        raise ValueError(f"no agent TOML templates found in {source_dir}")
    return templates


def _destination(
    *,
    scope: Literal["project", "user"],
    project_root: Path | None,
    home: Path | None,
) -> tuple[Path, Path]:
    if scope == "project":
        if project_root is None:
            raise ValueError("project_root is required for project scope")
        base = project_root
    elif scope == "user":
        if home is None:
            raise ValueError("home is required for user scope")
        base = home
    else:
        raise ValueError("scope must be 'project' or 'user'")
    _assert_no_symlink_ancestors(base, label="destination")
    if ".." in base.parts:
        raise ValueError("destination base must not contain '..'")
    if base.is_symlink():
        raise ValueError(f"destination base must not be a symlink: {base}")
    if not base.is_dir():
        raise ValueError(f"destination base does not exist: {base}")
    destination = base / ".codex" / "agents"
    resolved_base = base.resolve()
    for parent in (base / ".codex", destination):
        if parent.exists() or parent.is_symlink():
            if parent.is_symlink():
                raise ValueError(
                    f"destination parent must not be a symlink: {parent}"
                )
            if not parent.resolve().is_relative_to(resolved_base):
                raise ValueError(
                    f"destination parent escapes {scope} root: {parent}"
                )
    return base, destination


def _entry_stat(path: Path, directory_fd: int | None = None) -> os.stat_result | None:
    try:
        if directory_fd is None:
            return path.stat(follow_symlinks=False)
        return os.stat(path.name, dir_fd=directory_fd, follow_symlinks=False)
    except FileNotFoundError:
        return None


def _entry_is_symlink(path: Path, directory_fd: int | None = None) -> bool:
    metadata = _entry_stat(path, directory_fd)
    return metadata is not None and stat.S_ISLNK(metadata.st_mode)


def _entry_exists(path: Path, directory_fd: int | None = None) -> bool:
    return _entry_stat(path, directory_fd) is not None


def _unlink(path: Path, directory_fd: int | None = None) -> None:
    if directory_fd is None:
        path.unlink()
    else:
        os.unlink(path.name, dir_fd=directory_fd)


def _read_regular_nofollow(
    path: Path,
    directory_fd: int | None = None,
) -> bytes:
    if directory_fd is None:
        descriptor = os.open(path, os.O_RDONLY | NOFOLLOW)
    else:
        descriptor = os.open(
            path.name,
            os.O_RDONLY | NOFOLLOW,
            dir_fd=directory_fd,
        )
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise ValueError(f"path must be a regular file: {path}")
        chunks: list[bytes] = []
        while chunk := os.read(descriptor, 1024 * 1024):
            chunks.append(chunk)
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def _verify_directory_nofollow(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | DIRECTORY | NOFOLLOW)
    os.close(descriptor)


def _ensure_destination(destination: Path) -> None:
    for parent in (destination.parent, destination):
        if parent.is_symlink():
            raise ValueError(f"destination parent must not be a symlink: {parent}")
        parent.mkdir(exist_ok=True)
        _verify_directory_nofollow(parent)


@contextlib.contextmanager
def _installation_lock(destination: Path):
    _verify_directory_nofollow(destination)
    lock_path = destination / ".plugin-agent-install.lock"
    directory_descriptor: int | None = None
    descriptor: int | None = None
    try:
        if ANCHOR_SUPPORTED:
            directory_descriptor = os.open(
                destination,
                os.O_RDONLY | DIRECTORY | NOFOLLOW,
            )
        if lock_path.is_symlink():
            raise ValueError(f"agent install lock must not be a symlink: {lock_path}")
        try:
            if directory_descriptor is None:
                descriptor = os.open(
                    lock_path,
                    os.O_RDWR | os.O_CREAT | NOFOLLOW,
                    0o600,
                )
            else:
                descriptor = os.open(
                    lock_path.name,
                    os.O_RDWR | os.O_CREAT | NOFOLLOW,
                    0o600,
                    dir_fd=directory_descriptor,
                )
        except OSError as exc:
            if lock_path.is_symlink():
                raise ValueError(
                    f"agent install lock must not be a symlink: {lock_path}"
                ) from exc
            raise
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise ValueError(f"agent install lock must be a regular file: {lock_path}")
        if fcntl is not None:
            fcntl.flock(descriptor, fcntl.LOCK_EX)
        elif msvcrt is not None:
            if os.fstat(descriptor).st_size == 0:
                os.write(descriptor, b"\0")
            os.lseek(descriptor, 0, os.SEEK_SET)
            msvcrt.locking(descriptor, msvcrt.LK_LOCK, 1)
        else:  # pragma: no cover - all supported platforms provide one backend
            raise RuntimeError("no supported file-locking backend")
        yield directory_descriptor
    finally:
        if descriptor is not None:
            if fcntl is not None:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
            elif msvcrt is not None:
                os.lseek(descriptor, 0, os.SEEK_SET)
                msvcrt.locking(descriptor, msvcrt.LK_UNLCK, 1)
            os.close(descriptor)
        if directory_descriptor is not None:
            os.close(directory_descriptor)


def _atomic_write(
    path: Path,
    content: bytes,
    directory_fd: int | None = None,
) -> None:
    if directory_fd is not None:
        if _entry_is_symlink(path, directory_fd):
            raise ValueError(f"destination file must not be a symlink: {path}")
        temporary_name = f".{path.name}.{secrets.token_hex(8)}.tmp"
        descriptor = os.open(
            temporary_name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | NOFOLLOW,
            0o600,
            dir_fd=directory_fd,
        )
        try:
            with os.fdopen(descriptor, "wb", closefd=False) as file:
                file.write(content)
                file.flush()
                os.fsync(file.fileno())
            os.close(descriptor)
            descriptor = -1
            os.replace(
                temporary_name,
                path.name,
                src_dir_fd=directory_fd,
                dst_dir_fd=directory_fd,
            )
            os.fsync(directory_fd)
        finally:
            if descriptor >= 0:
                os.close(descriptor)
            try:
                os.unlink(temporary_name, dir_fd=directory_fd)
            except FileNotFoundError:
                pass
        return
    _verify_directory_nofollow(path.parent)
    if path.is_symlink():
        raise ValueError(f"destination file must not be a symlink: {path}")
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as file:
            file.write(content)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, path)
        directory_descriptor = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    finally:
        if temporary.exists():
            temporary.unlink()


def _hash_file_nofollow(
    path: Path,
    directory_fd: int | None = None,
) -> str:
    return hashlib.sha256(_read_regular_nofollow(path, directory_fd)).hexdigest()


def _remove_matching_target(
    path: Path,
    expected_hash: str,
    directory_fd: int | None = None,
) -> None:
    if _entry_is_symlink(path, directory_fd):
        raise ValueError(f"recovery target must not be a symlink: {path}")
    if not _entry_exists(path, directory_fd):
        return
    if _hash_file_nofollow(path, directory_fd) != expected_hash:
        raise ValueError(f"recovery target changed since interrupted install: {path}")
    _unlink(path, directory_fd)


def _recover_pending_install(
    destination: Path,
    *,
    plugin_name: str,
    journal: Path,
    ledger: Path,
    directory_fd: int | None = None,
) -> None:
    if not _entry_exists(journal, directory_fd):
        return
    if _entry_is_symlink(journal, directory_fd):
        raise ValueError(f"recovery journal must not be a symlink: {journal}")
    try:
        data = json.loads(
            _read_regular_nofollow(journal, directory_fd).decode("utf-8")
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid recovery journal: {journal}: {exc}") from exc
    if not isinstance(data, dict) or data.get("plugin") != plugin_name:
        raise ValueError(f"invalid recovery journal identity: {journal}")
    files = data.get("files")
    stage_name = data.get("stage")
    if (
        not isinstance(files, list)
        or not isinstance(stage_name, str)
        or Path(stage_name).name != stage_name
        or not stage_name.startswith(f".{plugin_name}.stage-")
    ):
        raise ValueError(f"invalid recovery journal contents: {journal}")
    for item in files:
        if not isinstance(item, dict):
            raise ValueError(f"invalid recovery journal file entry: {journal}")
        name = item.get("file")
        digest = item.get("sha256")
        if (
            not isinstance(name, str)
            or Path(name).name != name
            or not isinstance(digest, str)
        ):
            raise ValueError(f"invalid recovery journal file entry: {journal}")
        _remove_matching_target(destination / name, digest, directory_fd)
    stage = destination / stage_name
    if _entry_is_symlink(stage, directory_fd):
        raise ValueError(f"recovery stage must not be a symlink: {stage}")
    if _entry_exists(stage, directory_fd):
        _remove_stage(stage, directory_fd=directory_fd)
    previous_ledger = data.get("previousLedger")
    if previous_ledger is None:
        if _entry_is_symlink(ledger, directory_fd):
            raise ValueError(f"recovery ledger must not be a symlink: {ledger}")
        if _entry_exists(ledger, directory_fd):
            _unlink(ledger, directory_fd)
    elif isinstance(previous_ledger, dict):
        _atomic_write(
            ledger,
            (json.dumps(previous_ledger, indent=2) + "\n").encode("utf-8"),
            directory_fd,
        )
    else:
        raise ValueError(f"invalid recovery journal ledger: {journal}")
    _unlink(journal, directory_fd)


def _create_stage(
    destination: Path,
    plugin_name: str,
    directory_fd: int | None,
) -> tuple[Path, int | None]:
    if directory_fd is None:
        stage = Path(
            tempfile.mkdtemp(
                prefix=f".{plugin_name}.stage-",
                dir=destination,
            )
        )
        _verify_directory_nofollow(stage)
        return stage, None
    while True:
        stage_name = f".{plugin_name}.stage-{secrets.token_hex(8)}"
        try:
            os.mkdir(stage_name, 0o700, dir_fd=directory_fd)
            break
        except FileExistsError:
            continue
    stage = destination / stage_name
    stage_descriptor = os.open(
        stage_name,
        os.O_RDONLY | DIRECTORY | NOFOLLOW,
        dir_fd=directory_fd,
    )
    return stage, stage_descriptor


def _remove_stage(
    stage: Path,
    *,
    stage_fd: int | None = None,
    directory_fd: int | None = None,
) -> None:
    if directory_fd is None:
        if stage.exists():
            shutil.rmtree(stage)
        return
    opened_here = stage_fd is None
    if stage_fd is None:
        stage_fd = os.open(
            stage.name,
            os.O_RDONLY | DIRECTORY | NOFOLLOW,
            dir_fd=directory_fd,
        )
    try:
        for name in os.listdir(stage_fd):
            metadata = os.stat(name, dir_fd=stage_fd, follow_symlinks=False)
            if not stat.S_ISREG(metadata.st_mode):
                raise ValueError(f"agent stage contains unsafe entry: {stage / name}")
            os.unlink(name, dir_fd=stage_fd)
    finally:
        if opened_here:
            os.close(stage_fd)
    os.rmdir(stage.name, dir_fd=directory_fd)


def _stage_template(
    stage: Path,
    template: _Template,
    directory_fd: int | None = None,
) -> None:
    path = stage / template.name
    if directory_fd is None:
        descriptor = os.open(
            path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | NOFOLLOW,
            0o600,
        )
    else:
        descriptor = os.open(
            template.name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | NOFOLLOW,
            0o600,
            dir_fd=directory_fd,
        )
    try:
        view = memoryview(template.content)
        while view:
            written = os.write(descriptor, view)
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _perform_install(
    *,
    plugin_name: str,
    plugin_version: str,
    templates: list[_Template],
    destination: Path,
    dry_run: bool,
    directory_fd: int | None = None,
) -> InstallResult:
    ledger = destination / f".plugin-agent-install.{plugin_name}.json"
    journal = destination / f".plugin-agent-install.{plugin_name}.journal.json"
    if not dry_run and destination.exists():
        _verify_directory_nofollow(destination)
        _recover_pending_install(
            destination,
            plugin_name=plugin_name,
            journal=journal,
            ledger=ledger,
            directory_fd=directory_fd,
        )
    elif dry_run and (journal.exists() or journal.is_symlink()):
        raise ValueError("pending agent installation requires recovery")
    actions: list[InstallAction] = []
    for template in templates:
        target = destination / template.name
        if _entry_is_symlink(target, directory_fd):
            raise ValueError(f"agent destination must not be a symlink: {target}")
        if not _entry_exists(target, directory_fd):
            status: Status = "added"
        elif _hash_file_nofollow(target, directory_fd) == template.sha256:
            status = "unchanged"
        else:
            status = "conflict"
        actions.append(
            InstallAction(
                path=target,
                status=status,
                sha256=template.sha256,
            )
        )

    result = InstallResult(
        destination=destination,
        actions=tuple(actions),
        ledger=ledger,
        dry_run=dry_run,
    )
    if dry_run or any(action.status == "conflict" for action in actions):
        return result

    if _entry_is_symlink(ledger, directory_fd) or _entry_is_symlink(
        journal,
        directory_fd,
    ):
        raise ValueError("agent install metadata must not be a symlink")
    previous_ledger = (
        _read_regular_nofollow(ledger, directory_fd)
        if _entry_exists(ledger, directory_fd)
        else None
    )
    previous_ledger_data = (
        json.loads(previous_ledger.decode("utf-8"))
        if previous_ledger is not None
        else None
    )
    additions = [
        template
        for template, action in zip(templates, actions, strict=True)
        if action.status == "added"
    ]
    stage, stage_fd = _create_stage(destination, plugin_name, directory_fd)
    journal_data = {
        "plugin": plugin_name,
        "version": plugin_version,
        "stage": stage.name,
        "previousLedger": previous_ledger_data,
        "files": [
            {"file": template.name, "sha256": template.sha256}
            for template in additions
        ],
    }
    committed: list[_Template] = []
    try:
        _atomic_write(
            journal,
            (json.dumps(journal_data, indent=2) + "\n").encode("utf-8"),
            directory_fd,
        )
        for template in additions:
            _stage_template(stage, template, stage_fd)
        for template in additions:
            if directory_fd is None or stage_fd is None:
                os.replace(stage / template.name, destination / template.name)
            else:
                os.replace(
                    template.name,
                    template.name,
                    src_dir_fd=stage_fd,
                    dst_dir_fd=directory_fd,
                )
            committed.append(template)
        ledger_data = {
            "plugin": plugin_name,
            "version": plugin_version,
            "files": [
                {"file": template.name, "sha256": template.sha256}
                for template in templates
            ],
        }
        _atomic_write(
            ledger,
            (json.dumps(ledger_data, indent=2) + "\n").encode("utf-8"),
            directory_fd,
        )
    except BaseException:
        for template in committed:
            _remove_matching_target(
                destination / template.name,
                template.sha256,
                directory_fd,
            )
        if _entry_exists(stage, directory_fd):
            _remove_stage(
                stage,
                stage_fd=stage_fd,
                directory_fd=directory_fd,
            )
        if previous_ledger is None:
            if _entry_exists(ledger, directory_fd) and not _entry_is_symlink(
                ledger,
                directory_fd,
            ):
                _unlink(ledger, directory_fd)
        else:
            _atomic_write(ledger, previous_ledger, directory_fd)
        if _entry_exists(journal, directory_fd) and not _entry_is_symlink(
            journal,
            directory_fd,
        ):
            _unlink(journal, directory_fd)
        if stage_fd is not None:
            os.close(stage_fd)
        raise
    _remove_stage(
        stage,
        stage_fd=stage_fd,
        directory_fd=directory_fd,
    )
    if stage_fd is not None:
        os.close(stage_fd)
    _unlink(journal, directory_fd)
    return result


def install_agent_templates(
    source_dir: Path,
    *,
    scope: Literal["project", "user"],
    project_root: Path | None = None,
    home: Path | None = None,
    dry_run: bool = False,
) -> InstallResult:
    source_dir = Path(source_dir)
    _assert_no_symlink_ancestors(source_dir, label="source")
    plugin_name, plugin_version = _load_plugin_metadata(source_dir)
    templates = _load_templates(source_dir)
    _, destination = _destination(
        scope=scope,
        project_root=project_root,
        home=home,
    )
    if dry_run:
        return _perform_install(
            plugin_name=plugin_name,
            plugin_version=plugin_version,
            templates=templates,
            destination=destination,
            dry_run=True,
        )
    if not dry_run:
        _ensure_destination(destination)
    with _installation_lock(destination) as directory_fd:
        return _perform_install(
            plugin_name=plugin_name,
            plugin_version=plugin_version,
            templates=templates,
            destination=destination,
            dry_run=dry_run,
            directory_fd=directory_fd,
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Safely install bundled Codex agent templates."
    )
    parser.add_argument("source_dir", type=Path, nargs="?")
    parser.add_argument("--scope", choices=("project", "user"), required=True)
    parser.add_argument("--project-root", type=Path)
    parser.add_argument("--home", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    source_dir = args.source_dir
    if source_dir is None:
        source_dir = Path(__file__).resolve().parents[3] / "agents"
    result = install_agent_templates(
        source_dir,
        scope=args.scope,
        project_root=args.project_root,
        home=args.home,
        dry_run=args.dry_run,
    )
    for action in result.actions:
        print(f"{action.status}: {action.path}")
    if any(action.status == "conflict" for action in result.actions):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
