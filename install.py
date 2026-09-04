#!/usr/bin/env python3
"""Install NTC Agent Router without editing host configuration. Python 3.11+."""

import argparse
import hashlib
import os
from pathlib import Path
import shutil
import stat
import tempfile
import uuid


NAME = "ntc-agent-router"


def absolute(path):
    # Do not resolve links before checking them.
    return Path(os.path.abspath(os.path.expanduser(path)))


def check_path(path):
    """Reject links, Windows reparse points, and non-directory ancestors."""
    for part in (*reversed(path.parents), path):
        try:
            info = part.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ValueError(f"Refusing symlink or junction: {part}")
        if part != path and not stat.S_ISDIR(info.st_mode):
            raise ValueError(f"Expected a directory: {part}")


def contents(path):
    """Fingerprint the complete tree, including empty directories; reject links."""
    check_path(path)
    if not path.exists():
        return None
    result = {}

    def visit(item):
        check_path(item)
        info = item.lstat()
        relative = str(item.relative_to(path))
        if stat.S_ISDIR(info.st_mode):
            result[relative] = None
            for child in sorted(item.iterdir()):
                visit(child)
        elif stat.S_ISREG(info.st_mode):
            with item.open("rb") as stream:
                result[relative] = hashlib.file_digest(stream, "sha256").digest()
        else:
            raise ValueError(f"Expected a regular file or directory: {item}")

    visit(path)
    return result


def install(repo=None, *, target="codex", home=None, dry_run=False, environ=None):
    """Return a change log; --home isolates both targets from environment settings."""
    if target not in {"codex", "claude", "all"}:
        raise ValueError(f"Unknown target: {target}")
    repo = absolute(repo or Path(__file__).parent)
    env = os.environ if environ is None else environ
    base = absolute(home if home is not None else Path.home())
    roots = {
        "codex": absolute(env.get("CODEX_HOME") or base / ".codex")
        if home is None else base / ".codex",
        "claude": absolute(env.get("CLAUDE_CONFIG_DIR") or base / ".claude")
        if home is None else base / ".claude",
    }
    source = repo / "skills" / NAME
    if contents(source) is None or not source.is_dir() or not (source / "SKILL.md").is_file():
        raise ValueError(f"Missing skill: {source / 'SKILL.md'}")
    profiles = repo / "claude-agents"
    targets = ["codex", "claude"] if target == "all" else [target]
    operations = []
    for host in targets:
        root = roots[host]
        operations.append((source, root / "skills" / NAME, root))
        if host == "claude" and contents(profiles) is not None:
            if not profiles.is_dir():
                raise ValueError(f"Expected a directory: {profiles}")
            for profile in sorted(profiles.glob("*.md")):
                if not profile.is_file():
                    raise ValueError(f"Expected an agent file: {profile}")
                operations.append((profile, root / "agents" / profile.name, root))

    # Validate every operation before creating even a temporary directory.
    run_id = uuid.uuid4().hex
    pending, messages = [], []
    for src, dest, root in operations:
        expected, current = contents(src), contents(dest)
        backup = root / "backups" / NAME / run_id / dest.parent.name / dest.name
        check_path(backup)
        if backup.exists():
            raise ValueError(f"Backup destination already exists: {backup}")
        if root.exists() and not root.is_dir():
            raise ValueError(f"Expected a directory: {root}")
        if current is not None and src.is_dir() != dest.is_dir():
            raise ValueError(f"Destination has the wrong type: {dest}")
        for other_src, other_dest, _ in operations:
            if dest == other_src or dest in other_src.parents or other_src in dest.parents:
                raise ValueError(f"Source and destination overlap: {dest}")
            if other_dest != dest and (dest in other_dest.parents or other_dest in dest.parents):
                raise ValueError(f"Install destinations overlap: {dest}")
        if current == expected:
            messages.append(f"Unchanged: {dest}")
        else:
            pending.append({"src": src, "dest": dest, "root": root,
                            "backup": backup, "expected": expected,
                            "original": current, "saved": False, "installed": False})
    destinations = [dest for _, dest, _ in operations]
    if len(set(destinations)) != len(destinations):
        raise ValueError("Targets resolve to the same destination; install each host separately")
    if dry_run:
        return messages + [f"Would install: {op['dest']}" for op in pending]
    if not pending:
        return messages

    created, staging = [], {}

    def mkdir(path):
        check_path(path)
        missing = []
        while not path.exists():
            missing.append(path)
            path = path.parent
        for directory in reversed(missing):
            directory.mkdir()
            created.append(directory)

    try:
        # Finish all copies before touching installed files.
        for index, op in enumerate(pending):
            root = op["root"]
            mkdir(root)
            if root not in staging:
                staging[root] = Path(tempfile.mkdtemp(prefix=f".{NAME}-", dir=root))
            stage = staging[root] / str(index)
            op["stage"] = stage
            check_path(op["src"])
            if op["src"].is_dir():
                shutil.copytree(op["src"], stage, symlinks=True)
            else:
                shutil.copy2(op["src"], stage, follow_symlinks=False)
            if contents(stage) != op["expected"]:
                raise ValueError(f"Source changed during installation: {op['src']}")

        for op in pending:
            dest, backup = op["dest"], op["backup"]
            if contents(dest) != op["original"]:
                raise ValueError(f"Destination changed during installation: {dest}")
            mkdir(dest.parent)
            if op["original"] is not None:
                mkdir(backup.parent)
                check_path(backup)
                os.replace(dest, backup)
                op["saved"] = True
            check_path(dest)
            os.replace(op["stage"], dest)
            op["installed"] = True
            messages.append(f"Installed: {dest}")
            if op["saved"]:
                messages.append(f"Backup: {backup}")
    except Exception as error:
        failures = []
        for op in reversed(pending):
            try:
                if op["installed"]:
                    check_path(op["dest"])
                    check_path(op["stage"])
                    os.replace(op["dest"], op["stage"])
                if op["saved"]:
                    check_path(op["backup"])
                    check_path(op["dest"])
                    os.replace(op["backup"], op["dest"])
            except (OSError, ValueError) as rollback_error:
                failures.append(f"{op['dest']}: {rollback_error}; backup: {op['backup']}")
        if failures:
            raise RuntimeError(f"{error}; rollback needs attention: {'; '.join(failures)}") from error
        raise
    finally:
        for root, stage in staging.items():
            # Only recursively remove the temporary directory created by this run.
            if stage.parent != root or not stage.name.startswith(f".{NAME}-"):
                raise ValueError(f"Unexpected staging path: {stage}")
            contents(stage)
            shutil.rmtree(stage)
        for directory in reversed(created):
            try:
                directory.rmdir()  # Empty installer-created directories only.
            except OSError:
                pass
    return messages


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", choices=("codex", "claude", "all"), default="codex")
    parser.add_argument("--home", type=Path, help="Use an isolated home; ignore host environment directories")
    parser.add_argument("--dry-run", action="store_true", help="Validate and preview without writing")
    args = parser.parse_args()
    try:
        for message in install(target=args.target, home=args.home, dry_run=args.dry_run):
            print(message)
    except (OSError, ValueError, RuntimeError) as error:
        parser.exit(1, f"Install failed: {error}\n")


if __name__ == "__main__":
    main()
