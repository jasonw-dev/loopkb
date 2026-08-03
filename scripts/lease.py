#!/usr/bin/env python3
"""loopkb concurrency lease — one loop run at a time, across machines.

Usage:
    python3 scripts/lease.py acquire [--holder NAME] [--ttl-hours 2]
    python3 scripts/lease.py release [--holder NAME] [--ttl-hours 2] [--force]
    python3 scripts/lease.py status  [--ttl-hours 2]

Mechanism: an orphan branch `kb-loop-lock` holding a single empty commit whose
message records the holder, the session, and an ISO-8601 acquisition timestamp.
The branch is pushed to `origin`, so every clone sees the same lock. `acquire`
fails when the lock exists and is younger than the TTL (default 2 hours); an
older lock is considered stale and is replaced. `release` deletes the branch
locally and on the remote.

`release` only releases a lock this run holds. A lock recording another holder,
or another session of the same holder, is refused (exit 1) while it is younger
than the TTL — otherwise the documented "release on every exit path" would turn a
*failed* acquire into a lock theft: the run that lost the race would delete the
lock of the run that won it, and two loop runs would proceed at once. `--force`
is the escape hatch for a run that is genuinely dead before its TTL. An expired
lock needs no force: it is already stale and replaceable.

A release that cannot reach `origin` says so and exits 1. It drops the local ref
but the remote lock stands until the TTL, so reporting success there would tell
one clone the lease is free while every other clone still sees it held.

Compare-and-swap, not check-then-write. Reading the lock and then publishing one
is two steps, so the publish itself has to be the atomic test:

  * taking a free lock pushes WITHOUT `--force`. Git rejects a non-fast-forward
    update, and the lock commit is an orphan, so a push that lands proves the ref
    did not exist a moment ago. A rejection means someone else won the race — the
    rejection IS the compare-and-swap, and this process backs off.
  * replacing a stale lock, or refreshing one we already hold, pushes with
    `--force-with-lease=<ref>:<sha we read>`, so a concurrent takeover loses
    cleanly instead of being silently overwritten.
  * with no remote, `git update-ref <ref> <new> <expected>` gives the same
    semantics against the local ref (an empty `<expected>` means "must not exist").

Sessions: the lock also records a session id (`KB_LOOP_SESSION`, else the parent
process id). Only the same holder in the same session may refresh a live lock —
otherwise two terminals on one machine, sharing a holder name, would each
"refresh" their way into a concurrent run. A dead run's lock is cleared by
`release` or by the TTL, not by a second terminal inheriting it. Locks written by
older versions carry no session and stay refreshable by their holder.

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

# Substrings git uses when it refuses an update because the ref moved under us.
# Anything else is an infrastructure failure, not a lost race.
REJECT_MARKERS = (
    "rejected",
    "stale info",
    "non-fast-forward",
    "fetch first",
    "cannot lock ref",
    "reference already exists",
)


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


def default_session() -> str:
    """Distinguishes two runs that share a holder name — e.g. two terminals."""
    return os.environ.get("KB_LOOP_SESSION") or str(os.getppid())


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
            if key in ("holder", "acquired", "session"):
                info[key] = value.strip()
    info.setdefault("holder", "unknown")
    info.setdefault("session", "")  # locks written before sessions existed
    info.setdefault("acquired", git("log", "-1", "--format=%cI", sha))
    return info


def age(info: dict[str, str]) -> timedelta | None:
    acquired = parse_iso(info["acquired"])
    if acquired is None:
        return None
    return datetime.now(timezone.utc) - acquired


def create_lock_commit(holder: str, session: str = "") -> str:
    """Build the lock commit object. It is not referenced anywhere until published."""
    tree = subprocess.run(
        ["git", "hash-object", "-w", "-t", "tree", "--stdin"],
        input="",
        capture_output=True,
        text=True,
    )
    if tree.returncode != 0:
        raise SystemExit(f"could not create the empty tree: {tree.stderr.strip()}")
    empty_tree = tree.stdout.strip()
    message = f"kb-loop lock\n\nholder: {holder}\nsession: {session}\nacquired: {now_iso()}\n"
    proc = subprocess.run(
        ["git", "commit-tree", empty_tree, "-m", message],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise SystemExit(f"could not create lock commit: {proc.stderr.strip()}")
    return proc.stdout.strip()


def classify_failure(stderr: str) -> str:
    lowered = stderr.lower()
    return "rejected" if any(marker in lowered for marker in REJECT_MARKERS) else "error"


def publish_lock(sha: str, expected: str | None) -> tuple[str, str]:
    """Compare-and-swap the lock ref to `sha`.

    `expected` is the sha the lock must currently have; None means it must not
    exist at all. Returns ("ok" | "rejected" | "error", detail). "rejected" means
    another process won the race — never an infrastructure problem.
    """
    if has_remote():
        if expected is None:
            args = ["push", "origin", f"{sha}:{LOCK_REF}"]
        else:
            args = ["push", f"--force-with-lease={LOCK_REF}:{expected}", "origin", f"{sha}:{LOCK_REF}"]
        proc = subprocess.run(["git", *args], capture_output=True, text=True)
        if proc.returncode != 0:
            return classify_failure(proc.stderr), proc.stderr.strip()
        git("update-ref", LOCK_REF, sha)
        return "ok", ""

    proc = subprocess.run(
        ["git", "update-ref", LOCK_REF, sha, expected or ""],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return classify_failure(proc.stderr), proc.stderr.strip()
    return "ok", ""


def report_failure(status: str, detail: str) -> int:
    if status == "rejected":
        print(
            "lease: lost the race — another run took the lock while this one was reading it. "
            "Stop here; run `python3 scripts/lease.py status` to see who holds it.",
            file=sys.stderr,
        )
    else:
        print(f"lease: could not publish the lock: {detail}", file=sys.stderr)
    return 1


def cmd_acquire(args: argparse.Namespace) -> int:
    holder = args.holder or default_holder()
    session = default_session()
    sha = fetch_lock()

    if sha:
        info = lock_info(sha)
        held_for = age(info)
        # A missing session means a lock from an older version: holder alone decides.
        ours = info["holder"] == holder and info["session"] in ("", session)
        if ours:
            status, detail = publish_lock(create_lock_commit(holder, session), expected=sha)
            if status != "ok":
                return report_failure(status, detail)
            print(f"lease: refreshed by {holder}")
            return 0
        if held_for is not None and held_for < timedelta(hours=args.ttl_hours):
            minutes = int(held_for.total_seconds() // 60)
            same_identity = info["holder"] == holder
            where = " in another session" if same_identity else ""
            print(
                f"lease: held by {info['holder']}{where} since {info['acquired']} ({minutes}m ago) — "
                f"not stale until {args.ttl_hours}h. Another loop run is in progress; stop here."
                + (
                    " If that run is dead, clear it with "
                    "`python3 scripts/lease.py release --force`."
                    if same_identity
                    else ""
                ),
                file=sys.stderr,
            )
            return 1
        print(f"lease: replacing stale lock held by {info['holder']} since {info['acquired']}")

    status, detail = publish_lock(create_lock_commit(holder, session), expected=sha)
    if status != "ok":
        return report_failure(status, detail)
    scope = "origin" if has_remote() else "local only (no origin remote)"
    print(f"lease: acquired by {holder} — {scope}")
    return 0


def cmd_release(args: argparse.Namespace) -> int:
    holder = args.holder or default_holder()
    session = default_session()
    sha = fetch_lock()
    if not sha:
        print("lease: was not held — nothing to release")
        return 0

    info = lock_info(sha)
    held_for = age(info)
    # A missing session means a lock from an older version: holder alone decides.
    ours = info["holder"] == holder and info["session"] in ("", session)
    live = held_for is not None and held_for < timedelta(hours=args.ttl_hours)
    if not ours and live and not args.force:
        where = " in another session" if info["holder"] == holder else ""
        print(
            f"lease: refusing to release — the lock is held by {info['holder']}{where} since "
            f"{info['acquired']}, not by this run ({holder}). Deleting it would let a second "
            f"loop run start while that one is still working. It goes stale on its own after "
            f"{args.ttl_hours}h; pass --force only if you know that run is dead.",
            file=sys.stderr,
        )
        return 1

    remote_error = ""
    if has_remote():
        proc = subprocess.run(
            ["git", "push", "origin", "--delete", LOCK_NAME],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            remote_error = (proc.stderr.strip() or proc.stdout.strip() or "unknown error")
    drop_local_lock()

    if remote_error:
        print(
            f"lease: the local lock ref is gone, but deleting it on origin failed: "
            f"{remote_error}. The lease is NOT released — every other clone still sees it "
            f"held by {info['holder']} until it goes stale ({args.ttl_hours}h after "
            f"{info['acquired']}). Rerun `release` once origin is reachable.",
            file=sys.stderr,
        )
        return 1

    print("lease: released")
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

    release = subparsers.add_parser("release", help="drop the lease this run holds")
    release.add_argument("--holder", help="identity to match against the lock (default: as acquire)")
    release.add_argument("--ttl-hours", type=float, default=2.0, help="age after which a lock is stale")
    release.add_argument(
        "--force",
        action="store_true",
        help="release a live lock held by someone else — only for a run known to be dead",
    )
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
