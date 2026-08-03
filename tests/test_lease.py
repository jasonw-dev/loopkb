"""scripts/lease.py — the lock has to be a compare-and-swap, not a promise.

Every test runs against a real `git init --bare` remote with two clones, because
the property under test (a losing acquire must not steal the lock) only exists at
the git protocol level.
"""

from __future__ import annotations

import subprocess
import sys
import unittest

from helpers import SCRIPTS, TempDirTestCase, write

# Exercises the CAS primitive directly: publish a fresh lock commit with a stated
# expectation about the remote's current value, and print only the outcome.
CAS_PROBE = (
    "import sys, lease;"
    "expected = sys.argv[1] or None;"
    "sha = lease.create_lock_commit('probe', 'probe');"
    "print(lease.publish_lock(sha, expected)[0])"
)


class LeaseTest(TempDirTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.remote = self.tmp / "remote.git"
        subprocess.run(
            ["git", "init", "--bare", "-b", "main", str(self.remote)],
            capture_output=True,
            text=True,
            env=self.env,
            check=True,
        )
        self.alpha = self.clone("alpha", seed=True)
        self.beta = self.clone("beta")

    # --- scaffolding -------------------------------------------------------- #

    def clone(self, name: str, seed: bool = False):
        dest = self.tmp / name
        subprocess.run(
            ["git", "clone", str(self.remote), str(dest)],
            capture_output=True,
            text=True,
            env=self.env,
            check=True,
        )
        if seed:
            write(dest / "README.md", "# vault\n")
            self.git(dest, "add", "-A")
            self.git(dest, "commit", "-m", "chore: seed")
            self.git(dest, "push", "-u", "origin", "main")
        return dest

    def lease(self, repo, *args: str, holder: str = "holder-a", session: str = "session-1"):
        env = dict(self.env)
        env["KB_LOOP_HOLDER"] = holder
        env["KB_LOOP_SESSION"] = session
        proc = self.script("lease.py", *args, cwd=repo, env=env)
        proc.output = proc.stdout + proc.stderr  # type: ignore[attr-defined]
        return proc

    def remote_lock(self) -> str:
        out = self.git(self.remote, "rev-parse", "--verify", "--quiet", "refs/heads/kb-loop-lock", check=False)
        return out.strip()

    def cas_probe(self, repo, expected: str) -> str:
        env = dict(self.env)
        env["PYTHONPATH"] = str(SCRIPTS)
        proc = subprocess.run(
            [sys.executable, "-c", CAS_PROBE, expected],
            capture_output=True,
            text=True,
            cwd=str(repo),
            env=env,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return proc.stdout.strip()

    # --- acquire / block ---------------------------------------------------- #

    def test_acquire_publishes_the_lock(self) -> None:
        proc = self.lease(self.alpha, "acquire")
        self.assertEqual(proc.returncode, 0, proc.output)
        self.assertIn("acquired by holder-a", proc.output)
        self.assertTrue(self.remote_lock(), "the lock branch should exist on origin")

    def test_second_acquire_is_blocked_and_does_not_steal(self) -> None:
        self.lease(self.alpha, "acquire")
        held = self.remote_lock()

        proc = self.lease(self.beta, "acquire", holder="holder-b", session="session-2")
        self.assertEqual(proc.returncode, 1, proc.output)
        self.assertIn("held by holder-a", proc.output)
        self.assertEqual(self.remote_lock(), held, "a blocked acquire must not move the lock")

    def test_stale_lock_is_taken_over(self) -> None:
        self.lease(self.alpha, "acquire")
        held = self.remote_lock()

        proc = self.lease(self.beta, "acquire", "--ttl-hours", "0", holder="holder-b", session="session-2")
        self.assertEqual(proc.returncode, 0, proc.output)
        self.assertIn("replacing stale lock held by holder-a", proc.output)
        self.assertNotEqual(self.remote_lock(), held)

    def test_same_holder_same_session_refreshes(self) -> None:
        """Re-running acquire in the same session renews the lock instead of failing.

        (Within the same second the lock commit is byte-identical, so the ref may
        legitimately not move — what matters is that the run is not blocked.)
        """
        self.lease(self.alpha, "acquire")

        proc = self.lease(self.alpha, "acquire")
        self.assertEqual(proc.returncode, 0, proc.output)
        self.assertIn("refreshed by holder-a", proc.output)
        self.assertTrue(self.remote_lock(), "the lock must still be held after a refresh")

        status = self.lease(self.beta, "status", holder="holder-b", session="session-2")
        self.assertIn("held by holder-a", status.output)

    def test_same_holder_other_session_is_blocked(self) -> None:
        """Two terminals on one machine share a holder name — they are still two runs."""
        self.lease(self.alpha, "acquire", session="session-1")
        held = self.remote_lock()

        proc = self.lease(self.beta, "acquire", session="session-2")
        self.assertEqual(proc.returncode, 1, proc.output)
        self.assertIn("in another session", proc.output)
        self.assertIn("lease.py release", proc.output)
        self.assertEqual(self.remote_lock(), held)

    # --- the compare-and-swap itself ---------------------------------------- #

    def test_taking_a_held_lock_as_if_free_is_rejected(self) -> None:
        """The non-force push IS the CAS: 'the ref must not exist' is enforced by git."""
        self.lease(self.alpha, "acquire")
        held = self.remote_lock()
        self.assertEqual(self.cas_probe(self.beta, ""), "rejected")
        self.assertEqual(self.remote_lock(), held)

    def test_takeover_with_a_stale_expectation_is_rejected(self) -> None:
        """--force-with-lease: a takeover racing another takeover must lose cleanly."""
        self.lease(self.alpha, "acquire")
        stale_expectation = self.remote_lock()
        # Someone else takes the stale lock while this process still holds the old sha.
        self.lease(self.beta, "acquire", "--ttl-hours", "0", holder="holder-b", session="session-2")
        current = self.remote_lock()
        self.assertNotEqual(current, stale_expectation)

        self.assertEqual(self.cas_probe(self.alpha, stale_expectation), "rejected")
        self.assertEqual(self.remote_lock(), current)

    def test_takeover_with_the_right_expectation_succeeds(self) -> None:
        self.lease(self.alpha, "acquire")
        current = self.remote_lock()
        self.assertEqual(self.cas_probe(self.beta, current), "ok")
        self.assertNotEqual(self.remote_lock(), current)

    # --- release ------------------------------------------------------------ #

    def test_release_removes_the_lock_everywhere(self) -> None:
        self.lease(self.alpha, "acquire")
        proc = self.lease(self.alpha, "release")
        self.assertEqual(proc.returncode, 0, proc.output)
        self.assertIn("released", proc.output)
        self.assertEqual(self.remote_lock(), "")

        free = self.lease(self.beta, "status", holder="holder-b", session="session-2")
        self.assertIn("lease: free", free.output)

    def test_double_release_is_harmless(self) -> None:
        self.lease(self.alpha, "acquire")
        self.lease(self.alpha, "release")
        proc = self.lease(self.alpha, "release")
        self.assertEqual(proc.returncode, 0, proc.output)
        self.assertIn("was not held", proc.output)

    def test_release_refuses_a_lock_held_by_someone_else(self) -> None:
        """The abort path of a losing acquire must not delete the winner's lock."""
        self.lease(self.alpha, "acquire")
        held = self.remote_lock()

        blocked = self.lease(self.beta, "acquire", holder="holder-b", session="session-2")
        self.assertEqual(blocked.returncode, 1, blocked.output)

        proc = self.lease(self.beta, "release", holder="holder-b", session="session-2")
        self.assertEqual(proc.returncode, 1, proc.output)
        self.assertIn("refusing to release", proc.output)
        self.assertIn("held by holder-a", proc.output)
        self.assertEqual(self.remote_lock(), held, "a refused release must not move the lock")

        still = self.lease(self.beta, "status", holder="holder-b", session="session-2")
        self.assertIn("held by holder-a", still.output)

    def test_release_refuses_another_session_of_the_same_holder(self) -> None:
        """Two terminals on one machine share a holder name — still two runs."""
        self.lease(self.alpha, "acquire", session="session-1")
        held = self.remote_lock()

        proc = self.lease(self.beta, "release", session="session-2")
        self.assertEqual(proc.returncode, 1, proc.output)
        self.assertIn("in another session", proc.output)
        self.assertEqual(self.remote_lock(), held)

    def test_an_explicit_session_ties_acquire_and_release_together(self) -> None:
        """`--session` beats the environment: it is how a run states its own identity."""
        self.lease(self.alpha, "acquire", "--session", "run-42", session="shell-one")
        proc = self.lease(self.alpha, "release", "--session", "run-42", session="shell-two")
        self.assertEqual(proc.returncode, 0, proc.output)
        self.assertEqual(self.remote_lock(), "")

    def test_the_default_session_does_not_survive_a_new_shell(self) -> None:
        """The trap `--session` exists for, pinned.

        Every lease command of a real run is a separate process — an agent issues
        `acquire` and `release` as two commands. The parent-process fallback gives
        them different ids, so a release that does not name the run refuses the lock
        that run is holding. Naming it releases it.
        """
        env = dict(self.env)
        env["KB_LOOP_HOLDER"] = "holder-a"
        env.pop("KB_LOOP_SESSION", None)

        def in_its_own_shell(*args: str) -> str:
            # The trailing `:` stops sh from exec'ing python in its own process, so
            # python really does get a fresh parent — as it does under any agent.
            command = " ".join([sys.executable, str(SCRIPTS / "lease.py"), *args]) + "; :"
            proc = subprocess.run(
                ["sh", "-c", command], capture_output=True, text=True, cwd=str(self.alpha), env=env
            )
            return proc.stdout + proc.stderr

        acquired = in_its_own_shell("acquire")
        self.assertIn("acquired by holder-a", acquired)
        self.assertIn("--session", acquired, "acquire must name the id it had to invent")

        blind = in_its_own_shell("release")
        self.assertIn("refusing to release", blind)
        self.assertTrue(self.remote_lock(), "the run's own lock must survive its blind release")

        message = self.git(self.alpha, "log", "-1", "--format=%B", "refs/heads/kb-loop-lock")
        session = next(
            line.partition(":")[2].strip() for line in message.splitlines() if line.startswith("session:")
        )
        released = in_its_own_shell("release", "--session", session)
        self.assertIn("released", released)
        self.assertEqual(self.remote_lock(), "")

    def test_forced_release_clears_someone_elses_lock(self) -> None:
        """The escape hatch for a run that is dead before its TTL."""
        self.lease(self.alpha, "acquire")
        self.assertTrue(self.remote_lock())

        proc = self.lease(self.beta, "release", "--force", holder="holder-b", session="session-2")
        self.assertEqual(proc.returncode, 0, proc.output)
        self.assertIn("released", proc.output)
        self.assertEqual(self.remote_lock(), "")

    def test_release_of_a_stale_lock_needs_no_force(self) -> None:
        self.lease(self.alpha, "acquire")
        proc = self.lease(
            self.beta, "release", "--ttl-hours", "0", holder="holder-b", session="session-2"
        )
        self.assertEqual(proc.returncode, 0, proc.output)
        self.assertEqual(self.remote_lock(), "")

    def test_release_says_so_when_origin_is_unreachable(self) -> None:
        """The remote lock outlives an offline release; saying "released" would lie."""
        self.lease(self.alpha, "acquire")
        held = self.remote_lock()
        self.git(self.alpha, "remote", "set-url", "origin", str(self.tmp / "gone.git"))

        proc = self.lease(self.alpha, "release")
        self.assertEqual(proc.returncode, 1, proc.output)
        self.assertIn("local lock ref is gone", proc.output)
        self.assertIn("NOT released", proc.output)
        self.assertEqual(self.remote_lock(), held, "the remote lock must survive")
        self.assertEqual(
            self.git(
                self.alpha, "rev-parse", "--verify", "--quiet", "refs/heads/kb-loop-lock", check=False
            ).strip(),
            "",
            "the local ref is dropped — which is exactly what makes the report necessary",
        )

    def test_release_frees_the_lock_for_another_holder(self) -> None:
        self.lease(self.alpha, "acquire")
        self.lease(self.alpha, "release")
        proc = self.lease(self.beta, "acquire", holder="holder-b", session="session-2")
        self.assertEqual(proc.returncode, 0, proc.output)

    # --- status ------------------------------------------------------------- #

    def test_status_reports_the_holder(self) -> None:
        self.lease(self.alpha, "acquire")
        proc = self.lease(self.beta, "status", holder="holder-b", session="session-2")
        self.assertEqual(proc.returncode, 0, proc.output)
        self.assertIn("held by holder-a", proc.output)
        self.assertIn("stale: no", proc.output)


class LeaseWithoutRemoteTest(TempDirTestCase):
    """A solo vault that never pushes still gets a real lock — a local ref CAS."""

    def setUp(self) -> None:
        super().setUp()
        self.solo = self.tmp / "solo"
        self.solo.mkdir()
        self.git(self.solo, "init", "-b", "main")
        write(self.solo / "README.md", "# vault\n")
        self.git(self.solo, "add", "-A")
        self.git(self.solo, "commit", "-m", "chore: seed")

    def lease(self, *args: str, holder: str = "solo", session: str = "session-1"):
        env = dict(self.env)
        env["KB_LOOP_HOLDER"] = holder
        env["KB_LOOP_SESSION"] = session
        proc = self.script("lease.py", *args, cwd=self.solo, env=env)
        proc.output = proc.stdout + proc.stderr  # type: ignore[attr-defined]
        return proc

    def local_lock(self) -> str:
        return self.git(
            self.solo, "rev-parse", "--verify", "--quiet", "refs/heads/kb-loop-lock", check=False
        ).strip()

    def test_acquire_status_release_cycle(self) -> None:
        acquire = self.lease("acquire")
        self.assertEqual(acquire.returncode, 0, acquire.output)
        self.assertIn("local only (no origin remote)", acquire.output)
        self.assertTrue(self.local_lock())

        status = self.lease("status")
        self.assertIn("held by solo", status.output)

        release = self.lease("release")
        self.assertEqual(release.returncode, 0, release.output)
        self.assertEqual(self.local_lock(), "")

    def test_other_holder_is_blocked_locally_too(self) -> None:
        self.lease("acquire")
        held = self.local_lock()
        proc = self.lease("acquire", holder="someone-else", session="session-2")
        self.assertEqual(proc.returncode, 1, proc.output)
        self.assertEqual(self.local_lock(), held)

    def test_local_cas_rejects_creating_over_an_existing_lock(self) -> None:
        self.lease("acquire")
        held = self.local_lock()
        env = dict(self.env)
        env["PYTHONPATH"] = str(SCRIPTS)
        proc = subprocess.run(
            [sys.executable, "-c", CAS_PROBE, ""],
            capture_output=True,
            text=True,
            cwd=str(self.solo),
            env=env,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.strip(), "rejected")
        self.assertEqual(self.local_lock(), held)


if __name__ == "__main__":
    unittest.main()
