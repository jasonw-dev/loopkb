#!/usr/bin/env python3
"""loopkb concurrency lease — one loop run at a time, across machines.

Usage:
    python3 scripts/lease.py acquire [--holder NAME] [--ttl-hours 2]
    python3 scripts/lease.py release
    python3 scripts/lease.py status  [--ttl-hours 2]

Mechanism: an orphan branch `kb-loop-lock` holding a single empty commit whose
message records the holder and an ISO-8601 acquisition timestamp. The branch is
pushed to `origin`, so every clone sees the same lock. `acquire` fails when the
lock exists and is younger than the TTL (default 2 hours); an older lock is
considered stale and is replaced. `release` deletes the branch locally and on
the remote.

Degradation: with no `origin` remote (a solo vault that never pushes), the lock
is a purely local ref and the same rules apply.

Python 3 standard library only; all git access goes through subprocess.
"""

from __future__ import annotations

import argparse
import os
import socket
import subprocess
import sys
from datetime import datetime, timedelta, timezone

LOCK_REF = "refs/heads/kb-loop-lock"
LOCK_NAME = "kb-loop-lock"
MIRROR_REF = "refs/kb-loop-lock/remote"


def git(*args: str, check: bool = True) -> str:
    proc = subprocess.run(["git", *args], capture_output=True, text=True)
    if check and proc.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout.strip()


def git_ok(*args: str) -> bool:
    return subprocess.run(["git", *args], capture_output=True, text=True).returncode == 0


def has_remote() -> bool:
    return git_ok("remote", "get-url", "origin")


def default_holder() -> str:
    env = os.environ.get("KB_LOOP_HOLDER")
    if env:
        return env
    user = git("config", "--get", "user.name", check=False) or os.environ.get("USER", "unknown")
    return f"{user}@{socket.gethostname()}"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def parse_iso(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def local_lock() -> str | None:
    return git("rev-parse", "--verify", "--quiet", LOCK_REF, check=False) or None


def drop_local_lock() -> None:
    for ref in (LOCK_REF, MIRROR_REF):
        if git("rev-parse", "--verify", "--quiet", ref, check=False):
            git("update-ref", "-d", ref, check=False)


def remote_lock() -> tuple[bool, str | None]:
    """(origin reachable, lock sha). ls-remote is the authority — a fetch alone
    cannot tell 'still held' from 'deleted upstream, mirror ref left behind'."""
    proc = subprocess.run(["git", "ls-remote", "origin", LOCK_REF], capture_output=True, text=True)
    if proc.returncode != 0:
        return False, None
    out = proc.stdout.strip()
    return True, (out.split()[0] if out else None)


def fetch_lock() -> str | None:
    """Return the commit sha of the current lock, refreshing from origin first."""
    if not has_remote():
        return local_lock()

    reachable, sha = remote_lock()
    if not reachable:
        print("lease: origin unreachable — using the local ref only", file=sys.stderr)
        return local_lock()
    if sha is None:
        drop_local_lock()  # released upstream
        return None

    subprocess.run(
        ["git", "fetch", "--force", "origin", f"+{LOCK_REF}:{MIRROR_REF}"],
        capture_output=True,
        text=True,
    )
    git("update-ref", LOCK_REF, sha)  # keep the local ref in step with remote truth
    return sha


def lock_info(sha: str) -> dict[str, str]:
    message = git("log", "-1", "--format=%B", sha)
    info: dict[str, str] = {}
    for line in message.splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip().lower()
            if key in ("holder", "acquired"):
                info[key] = value.strip()
    info.setdefault("holder", "unknown")
    info.setdefault("acquired", git("log", "-1", "--format=%cI", sha))
    return info


def age(info: dict[str, str]) -> timedelta | None:
    acquired = parse_iso(info["acquired"])
    if acquired is None:
        return None
    return datetime.now(timezone.utc) - acquired


def write_lock(holder: str) -> str:
    empty_tree = git("hash-object", "-t", "tree", "/dev/null")
    message = f"kb-loop lock\n\nholder: {holder}\nacquired: {now_iso()}\n"
    proc = subprocess.run(
        ["git", "commit-tree", empty_tree, "-m", message],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise SystemExit(f"could not create lock commit: {proc.stderr.strip()}")
    sha = proc.stdout.strip()
    git("update-ref", LOCK_REF, sha)
    if has_remote():
        push = subprocess.run(
            ["git", "push", "--force", "origin", f"{LOCK_REF}:{LOCK_REF}"],
            capture_output=True,
            text=True,
        )
        if push.returncode != 0:
            git("update-ref", "-d", LOCK_REF, check=False)
            raise SystemExit(f"could not publish the lock to origin: {push.stderr.strip()}")
    return sha


def cmd_acquire(args: argparse.Namespace) -> int:
    holder = args.holder or default_holder()
    sha = fetch_lock()
    if sha:
        info = lock_info(sha)
        held_for = age(info)
        if info["holder"] == holder:
            write_lock(holder)
            print(f"lease: refreshed by {holder}")
            return 0
        if held_for is not None and held_for < timedelta(hours=args.ttl_hours):
            minutes = int(held_for.total_seconds() // 60)
            print(
                f"lease: held by {info['holder']} since {info['acquired']} ({minutes}m ago) — "
                f"not stale until {args.ttl_hours}h. Another loop run is in progress; stop here.",
                file=sys.stderr,
            )
            return 1
        print(f"lease: replacing stale lock held by {info['holder']} since {info['acquired']}")
    write_lock(holder)
    scope = "origin" if has_remote() else "local only (no origin remote)"
    print(f"lease: acquired by {holder} — {scope}")
    return 0


def cmd_release(args: argparse.Namespace) -> int:
    sha = fetch_lock()
    if has_remote():
        subprocess.run(
            ["git", "push", "origin", "--delete", LOCK_NAME],
            capture_output=True,
            text=True,
        )
    drop_local_lock()
    print("lease: released" if sha else "lease: was not held — nothing to release")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    sha = fetch_lock()
    if not sha:
        print("lease: free")
        return 0
    info = lock_info(sha)
    held_for = age(info)
    minutes = "unknown" if held_for is None else f"{int(held_for.total_seconds() // 60)}m"
    stale = held_for is not None and held_for >= timedelta(hours=args.ttl_hours)
    print(f"lease: held by {info['holder']}")
    print(f"acquired: {info['acquired']} ({minutes} ago)")
    print(f"stale: {'yes' if stale else 'no'} (ttl {args.ttl_hours}h)")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="loopkb concurrency lease")
    subparsers = parser.add_subparsers(dest="command", required=True)

    acquire = subparsers.add_parser("acquire", help="take the lease, failing if it is held and fresh")
    acquire.add_argument("--holder", help="identity recorded in the lock (default: git user @ hostname)")
    acquire.add_argument("--ttl-hours", type=float, default=2.0, help="age after which a lock is stale")
    acquire.set_defaults(func=cmd_acquire)

    release = subparsers.add_parser("release", help="drop the lease")
    release.set_defaults(func=cmd_release)

    status = subparsers.add_parser("status", help="report who holds the lease")
    status.add_argument("--ttl-hours", type=float, default=2.0)
    status.set_defaults(func=cmd_status)

    args = parser.parse_args(argv[1:])
    if not git_ok("rev-parse", "--git-dir"):
        print("lease: not inside a git repository", file=sys.stderr)
        return 1
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
