"""scripts/verify_digest.py — the digest must be checkable, not merely written.

Every test builds a small real repo, commits into it the way the loop would, and
asserts what the verifier concludes.
"""

from __future__ import annotations

import unittest

from helpers import TempDirTestCase, add_clean_pair, make_vault, write

CURATED = """---
type: guides
domains: [ci-cd]
created: 2026-08-01
source: inbox
status: {status}
---
# Gamma

## Related
- [[alpha-note]]
"""


class VerifyDigestTest(TempDirTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.vault = make_vault(self.tmp / "vault")
        add_clean_pair(self.vault)
        self.git(self.vault, "init", "-b", "main")
        self.commit("chore: seed the vault")

    # --- scaffolding -------------------------------------------------------- #

    def commit(self, message: str) -> str:
        self.git(self.vault, "add", "-A")
        self.git(self.vault, "commit", "-m", message)
        return self.git(self.vault, "rev-parse", "HEAD")

    def short(self, sha: str) -> str:
        return self.git(self.vault, "rev-parse", "--short", sha)

    def set_digest(self, body: str) -> None:
        write(self.vault / "_meta" / "digest.md", f"# Run digest\n\n{body}\n")

    def verify(self):
        proc = self.script("verify_digest.py", str(self.vault))
        proc.output = proc.stdout + proc.stderr  # type: ignore[attr-defined]
        return proc

    def assert_clean(self) -> None:
        proc = self.verify()
        self.assertEqual(proc.returncode, 0, proc.output)
        self.assertIn("verify-digest: clean", proc.output)

    def assert_missing(self, sha: str, because: str = "") -> None:
        proc = self.verify()
        self.assertEqual(proc.returncode, 1, proc.output)
        self.assertIn(f"missing from digest: {self.short(sha)}", proc.output)
        if because:
            self.assertIn(because, proc.output)

    # --- the quiet cases ---------------------------------------------------- #

    def test_additive_agent_commit_is_not_risky(self) -> None:
        write(self.vault / "guides" / "gamma-note.md", CURATED.format(status="raw"))
        self.commit("[kb-loop] triage: file gamma-note")
        self.assert_clean()

    def test_human_deletion_is_not_the_agents_to_report(self) -> None:
        (self.vault / "guides" / "beta-note.md").unlink()
        self.commit("cleanup: drop beta-note")
        self.assert_clean()

    def test_digest_only_commit_is_not_a_meta_change(self) -> None:
        self.set_digest("Risky actions: none")
        self.commit("[kb-loop] run report: 2026-08-01")
        self.assert_clean()

    def test_promotion_is_not_a_demotion(self) -> None:
        write(self.vault / "guides" / "gamma-note.md", CURATED.format(status="raw"))
        self.commit("[kb-loop] triage: file gamma-note")
        write(self.vault / "guides" / "gamma-note.md", CURATED.format(status="curated"))
        self.commit("[kb-loop] refine: promote gamma-note")
        self.assert_clean()

    # --- each risky class --------------------------------------------------- #

    def test_deletion_must_be_in_the_digest(self) -> None:
        (self.vault / "guides" / "beta-note.md").unlink()
        write(self.vault / "guides" / "alpha-note.md", CURATED.format(status="curated"))
        sha = self.commit("[kb-loop] refine: merge beta-note into alpha-note")
        self.assert_missing(sha, because="deleted guides/beta-note.md")

    def test_rename_must_be_in_the_digest(self) -> None:
        self.git(self.vault, "mv", "guides/beta-note.md", "guides/renamed-note.md")
        write(self.vault / "guides" / "alpha-note.md", CURATED.format(status="curated"))
        sha = self.commit("[kb-loop] refine: rename beta-note")
        self.assert_missing(sha, because="renamed guides/beta-note.md -> guides/renamed-note.md")

    def test_meta_change_must_be_in_the_digest(self) -> None:
        write(self.vault / "_meta" / "taxonomy.md", "# Taxonomy\n\nFramework rules.\n\nNew rule.\n")
        sha = self.commit("[kb-loop] taxonomy change: add a rule")
        self.assert_missing(sha, because="_meta/ rule change: _meta/taxonomy.md")

    def test_demotion_must_be_in_the_digest(self) -> None:
        write(self.vault / "guides" / "alpha-note.md", CURATED.format(status="raw"))
        sha = self.commit("[kb-loop] refine: demote alpha-note — commands no longer accurate")
        self.assert_missing(sha, because="demoted guides/alpha-note.md: curated -> raw")

    # --- the digest satisfies the check ------------------------------------- #

    def test_itemizing_the_short_sha_satisfies_the_check(self) -> None:
        (self.vault / "guides" / "beta-note.md").unlink()
        write(self.vault / "guides" / "alpha-note.md", CURATED.format(status="curated"))
        sha = self.commit("[kb-loop] refine: merge beta-note into alpha-note")

        self.set_digest(f"## Risky actions\n\n- merged beta-note into alpha-note ({self.short(sha)})")
        self.assert_clean()

    def test_a_full_sha_also_satisfies_the_check(self) -> None:
        (self.vault / "guides" / "beta-note.md").unlink()
        sha = self.commit("[kb-loop] refine: delete beta-note")
        self.set_digest(f"- deleted beta-note ({sha})")
        self.assert_clean()

    # --- the window --------------------------------------------------------- #

    def test_first_run_scans_the_whole_history(self) -> None:
        (self.vault / "guides" / "beta-note.md").unlink()
        sha = self.commit("[kb-loop] refine: delete beta-note")
        for index in range(3):
            write(self.vault / "guides" / f"filler-{index}.md", CURATED.format(status="raw"))
            self.commit(f"[kb-loop] triage: file filler-{index}")

        proc = self.verify()
        self.assertEqual(proc.returncode, 1, proc.output)
        self.assertIn(f"missing from digest: {self.short(sha)}", proc.output)

    def test_a_previous_run_report_closes_the_window(self) -> None:
        (self.vault / "guides" / "beta-note.md").unlink()
        old = self.commit("[kb-loop] refine: delete beta-note")

        self.set_digest("Risky actions: none")
        self.commit("[kb-loop] run report: 2026-08-01")

        write(self.vault / "guides" / "gamma-note.md", CURATED.format(status="raw"))
        self.commit("[kb-loop] triage: file gamma-note")

        proc = self.verify()
        self.assertEqual(proc.returncode, 0, proc.output)
        self.assertNotIn(self.short(old), proc.output)
        self.assertIn("since the previous run report", proc.output)

    def test_head_being_the_report_commit_still_covers_that_run(self) -> None:
        """Running the verifier after the report commit must not vacuously pass."""
        (self.vault / "guides" / "beta-note.md").unlink()
        sha = self.commit("[kb-loop] refine: delete beta-note")
        self.set_digest("Risky actions: none")
        self.commit("[kb-loop] run report: 2026-08-01")
        self.assert_missing(sha)

    def test_missing_digest_file_fails_when_something_is_risky(self) -> None:
        (self.vault / "_meta" / "digest.md").unlink()
        (self.vault / "guides" / "beta-note.md").unlink()
        sha = self.commit("[kb-loop] refine: delete beta-note and the digest")
        self.assert_missing(sha)


if __name__ == "__main__":
    unittest.main()
