"""scripts/lint.py — one test per violation class it knows about.

Each test starts from a vault that lints clean, introduces exactly one defect,
and asserts both the exit code and the message, so a rule cannot be silently
dropped without a test noticing.
"""

from __future__ import annotations

import sys

from helpers import SCRIPTS, TempDirTestCase, add_clean_pair, make_vault, write


class LintTest(TempDirTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.vault = make_vault(self.tmp / "vault")
        add_clean_pair(self.vault)

    def lint(self) -> tuple[int, str]:
        proc = self.script("lint.py", str(self.vault))
        return proc.returncode, proc.stdout + proc.stderr

    def assert_violation(self, fragment: str) -> None:
        code, out = self.lint()
        self.assertEqual(code, 1, f"expected a violation, got exit 0:\n{out}")
        self.assertIn(fragment, out)

    # --- the clean baseline ------------------------------------------------- #

    def test_clean_vault_passes(self) -> None:
        code, out = self.lint()
        self.assertEqual(code, 0, out)
        self.assertIn("lint: clean", out)
        self.assertIn("2 note(s) checked", out)

    # --- frontmatter -------------------------------------------------------- #

    def test_missing_frontmatter(self) -> None:
        write(self.vault / "guides" / "no-frontmatter.md", "# Just a heading\n")
        self.assert_violation("missing YAML frontmatter block")

    def test_unparseable_frontmatter_line(self) -> None:
        write(
            self.vault / "guides" / "bad-line.md",
            "---\ntype: guides\n!!! not a key\ndomains: [ci-cd]\ncreated: 2026-08-01\n"
            "source: inbox\nstatus: raw\n---\n# Bad\n",
        )
        self.assert_violation("unparseable frontmatter line")

    def test_missing_required_keys(self) -> None:
        write(self.vault / "guides" / "sparse-note.md", "---\ntype: guides\n---\n# Sparse\n")
        code, out = self.lint()
        self.assertEqual(code, 1, out)
        for key in ("domains", "created", "source", "status"):
            self.assertIn(f"missing required frontmatter key: {key}", out)

    def test_type_does_not_match_folder(self) -> None:
        write(
            self.vault / "guides" / "wrong-type.md",
            "---\ntype: troubleshooting\ndomains: [ci-cd]\ncreated: 2026-08-01\n"
            "source: inbox\nstatus: raw\n---\n# Wrong\n",
        )
        self.assert_violation("does not match its folder 'guides'")

    def test_status_outside_the_enum(self) -> None:
        write(
            self.vault / "guides" / "bad-status.md",
            "---\ntype: guides\ndomains: [ci-cd]\ncreated: 2026-08-01\n"
            "source: inbox\nstatus: golden\n---\n# Bad status\n",
        )
        self.assert_violation("status 'golden' is not one of")

    def test_source_outside_the_enum(self) -> None:
        write(
            self.vault / "guides" / "bad-source.md",
            "---\ntype: guides\ndomains: [ci-cd]\ncreated: 2026-08-01\n"
            "source: telepathy\nstatus: raw\n---\n# Bad source\n",
        )
        self.assert_violation("source 'telepathy' is not one of")

    def test_created_is_not_a_date(self) -> None:
        write(
            self.vault / "guides" / "bad-date.md",
            "---\ntype: guides\ndomains: [ci-cd]\ncreated: yesterday\n"
            "source: inbox\nstatus: raw\n---\n# Bad date\n",
        )
        self.assert_violation("created 'yesterday' is not a YYYY-MM-DD date")

    # --- domains ------------------------------------------------------------ #

    def test_domain_outside_the_vocabulary(self) -> None:
        write(
            self.vault / "guides" / "unknown-domain.md",
            "---\ntype: guides\ndomains: [quantum]\ncreated: 2026-08-01\n"
            "source: inbox\nstatus: raw\n---\n# Unknown domain\n",
        )
        self.assert_violation("domain 'quantum' is not in the vocabulary")

    def test_empty_domains_on_a_curated_note(self) -> None:
        write(
            self.vault / "guides" / "no-domains.md",
            "---\ntype: guides\ndomains: []\ncreated: 2026-08-01\n"
            "source: inbox\nstatus: curated\n---\n# No domains\n\n[[alpha-note]]\n",
        )
        self.assert_violation("domains may only be empty on raw notes")

    def test_empty_domains_on_a_raw_note_is_allowed(self) -> None:
        write(
            self.vault / "guides" / "raw-no-domains.md",
            "---\ntype: guides\ndomains: []\ncreated: 2026-08-01\n"
            "source: inbox\nstatus: raw\n---\n# Raw\n",
        )
        code, out = self.lint()
        self.assertEqual(code, 0, out)

    # --- links -------------------------------------------------------------- #

    def test_curated_note_without_a_wikilink(self) -> None:
        write(
            self.vault / "guides" / "lonely-note.md",
            "---\ntype: guides\ndomains: [ci-cd]\ncreated: 2026-08-01\n"
            "source: inbox\nstatus: curated\n---\n# Lonely\n",
        )
        self.assert_violation("must link to at least one related note")

    def test_dangling_wikilink(self) -> None:
        write(
            self.vault / "guides" / "dangling-link.md",
            "---\ntype: guides\ndomains: [ci-cd]\ncreated: 2026-08-01\n"
            "source: inbox\nstatus: raw\n---\n# Dangling\n\n[[nowhere-note]]\n",
        )
        self.assert_violation("wikilink [[nowhere-note]] has no matching note")

    # --- filenames ---------------------------------------------------------- #

    def test_non_kebab_filename(self) -> None:
        write(
            self.vault / "guides" / "Not_Kebab.md",
            "---\ntype: guides\ndomains: [ci-cd]\ncreated: 2026-08-01\n"
            "source: inbox\nstatus: raw\n---\n# Not kebab\n",
        )
        self.assert_violation("filename must be kebab-case English")

    def test_undated_meeting_filename(self) -> None:
        write(
            self.vault / "meetings" / "team-sync.md",
            "---\ntype: meetings\ndomains: [ci-cd]\ncreated: 2026-08-01\n"
            "source: meeting\nstatus: raw\n---\n# Sync\n",
        )
        self.assert_violation("filename must start with the meeting date")

    def test_dated_meeting_filename_passes(self) -> None:
        write(
            self.vault / "meetings" / "2026-08-01-team-sync.md",
            "---\ntype: meetings\ndomains: [ci-cd]\ncreated: 2026-08-01\n"
            "source: meeting\nstatus: raw\n---\n# Sync\n",
        )
        code, out = self.lint()
        self.assertEqual(code, 0, out)

    def test_wikilink_inside_an_html_comment_does_not_count(self) -> None:
        # Templates legitimately ship `[[...]]` examples inside comments, and a comment
        # is invisible in Obsidian: it must neither dangle nor satisfy the curated floor.
        write(
            self.vault / "guides" / "commented-link.md",
            "---\ntype: guides\ndomains: [ci-cd]\ncreated: 2026-08-01\n"
            "source: inbox\nstatus: curated\n---\n# Commented\n\n"
            "<!-- ## Related\n- [[nowhere-note]]\n-->\n",
        )
        code, out = self.lint()
        self.assertEqual(code, 1, out)
        self.assertIn("must link to at least one related note", out)
        self.assertNotIn("nowhere-note", out)

    def test_non_utf8_file_is_one_violation_not_a_traceback(self) -> None:
        path = self.vault / "guides" / "cp950-note.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(
            b"---\ntype: guides\ndomains: [ci-cd]\ncreated: 2026-08-01\n"
            b"source: inbox\nstatus: raw\n---\n# "
            + "測試中文".encode("cp950")
            + b"\n"
        )
        code, out = self.lint()
        self.assertEqual(code, 1, out)
        self.assertIn("guides/cp950-note.md: not valid UTF-8", out)
        self.assertNotIn("Traceback", out)
        self.assertIn("1 violation(s)", out)

    def test_duplicate_basename_across_folders(self) -> None:
        write(
            self.vault / "troubleshooting" / "alpha-note.md",
            "---\ntype: troubleshooting\ndomains: [ci-cd]\ncreated: 2026-08-01\n"
            "source: inbox\nstatus: raw\n---\n# Duplicate\n",
        )
        self.assert_violation("basename 'alpha-note' is not unique")

    def test_inbox_basename_collision_is_a_warning(self) -> None:
        # "Drop anything into _inbox/" cannot mean "unless you picked a taken name".
        write(self.vault / "_inbox" / "alpha-note.md", "rough notes about alpha\n")
        code, out = self.lint()
        self.assertEqual(code, 0, out)
        self.assertIn("_inbox/alpha-note.md: warning: basename 'alpha-note'", out)
        self.assertIn("guides/alpha-note.md", out)
        self.assertIn("1 warning(s)", out)

    # --- vault-level -------------------------------------------------------- #

    def test_missing_instance_file(self) -> None:
        (self.vault / "_meta" / "instance.md").unlink()
        self.assert_violation("_meta/instance.md: missing")

    def write_vocabulary(self, *lines: str) -> None:
        write(
            self.vault / "_meta" / "instance.md",
            "# Instance Configuration\n\n## Domain tag vocabulary (closed)\n\n"
            + "".join(f"{line}\n" for line in lines),
        )

    def test_annotated_vocabulary_lines_are_parsed(self) -> None:
        self.write_vocabulary(
            "- `ci-cd` — pipelines, runners: the whole release path",
            "- `tooling` - dev environment: toolchains, IDE setup",
            "- infrastructure — cloud, networking",
        )
        write(
            self.vault / "guides" / "annotated-domains.md",
            "---\ntype: guides\ndomains: [ci-cd, tooling, infrastructure]\ncreated: 2026-08-01\n"
            "source: inbox\nstatus: raw\n---\n# Annotated\n",
        )
        code, out = self.lint()
        self.assertEqual(code, 0, out)
        self.assertNotIn("warning", out)

    def test_unreadable_vocabulary_line_warns_without_failing(self) -> None:
        self.write_vocabulary("- `ci-cd`", "- `tooling`", "- **Not A Tag** — prose that slipped in")
        code, out = self.lint()
        self.assertEqual(code, 0, out)
        self.assertIn("vocabulary line carries no kebab-case tag", out)
        self.assertIn("**Not A Tag**", out)
        self.assertIn("1 warning(s)", out)

    def test_note_in_a_non_type_folder_warns_without_failing(self) -> None:
        write(
            self.vault / "notes" / "stray.md",
            "---\ntype: notes\ndomains: [ci-cd]\ncreated: 2026-08-01\n"
            "source: inbox\nstatus: raw\n---\n# Stray\n",
        )
        code, out = self.lint()
        self.assertEqual(code, 0, out)
        self.assertIn("warning", out)
        self.assertIn("'notes' is not a type folder", out)
        self.assertIn("1 warning(s)", out)

    def test_framework_directories_are_outside_the_note_namespace(self) -> None:
        # None of these directories holds notes. The procedures live in .claude/skills/;
        # an instance may add team skills of its own in .agents/skills/, whose SKILL.md
        # basenames would otherwise collide in the index with the ones next door.
        for skills_dir in (".claude", ".agents"):
            write(self.vault / skills_dir / "skills" / "kb-search" / "SKILL.md", "# pointer\n")
        write(self.vault / "docs" / "design-decisions.md", "# ADRs\n")
        write(self.vault / "_attachments" / "kb-search.md", "# not a note\n")
        code, out = self.lint()
        self.assertEqual(code, 0, out)
        self.assertNotIn("warning", out)
        self.assertNotIn("SKILL", out)

    def test_a_note_nested_under_a_type_folder_is_still_linted(self) -> None:
        # The framework directory names are skipped at the top level only. A note in
        # `guides/scripts/` is a note: skipping it at any depth made it invisible —
        # unlinted, absent from the basename index, and dangling from every link to it.
        write(
            self.vault / "guides" / "scripts" / "nested-note.md",
            "---\ntype: guides\ndomains: [ci-cd]\ncreated: 2026-08-01\n"
            "source: inbox\nstatus: golden\n---\n# Nested\n",
        )
        self.assert_violation("guides/scripts/nested-note.md: status 'golden' is not one of")

    def test_a_nested_note_joins_the_basename_index(self) -> None:
        write(
            self.vault / "guides" / "docs" / "nested-target.md",
            "---\ntype: guides\ndomains: [ci-cd]\ncreated: 2026-08-01\n"
            "source: inbox\nstatus: raw\n---\n# Target\n",
        )
        write(
            self.vault / "guides" / "pointer-note.md",
            "---\ntype: guides\ndomains: [ci-cd]\ncreated: 2026-08-01\n"
            "source: inbox\nstatus: raw\n---\n# Pointer\n\n[[nested-target]]\n",
        )
        code, out = self.lint()
        self.assertEqual(code, 0, out)
        self.assertIn("4 note(s) checked", out)

    def test_inbox_notes_are_never_warned_about(self) -> None:
        write(self.vault / "_inbox" / "rough-idea.md", "some unclassified text\n")
        code, out = self.lint()
        self.assertEqual(code, 0, out)
        self.assertNotIn("warning", out)

    # --- import safety ------------------------------------------------------ #

    def test_lint_is_importable_and_callable(self) -> None:
        sys.path.insert(0, str(SCRIPTS))
        self.addCleanup(sys.path.remove, str(SCRIPTS))
        import lint  # noqa: PLC0415 — importing under test is the point

        problems, warnings, checked = lint.lint(self.vault)
        self.assertEqual(problems, [])
        self.assertEqual(warnings, [])
        self.assertEqual(checked, 2)


if __name__ == "__main__":
    import unittest

    unittest.main()
