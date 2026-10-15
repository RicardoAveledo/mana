"""Regression tests for change-scoped local verification. No Xcode required."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import verify


class VerificationPlanTests(unittest.TestCase):
    def test_website_never_starts_native_tests(self):
        self.assertEqual(verify.plan(["docs/index.html", "docs/assets/app-store-badge.svg",
                                      "scripts/social-card.py"]), ["website"])

    def test_mac_changes_do_not_start_simulator(self):
        self.assertEqual(verify.plan(["Mana/Usage/UsageStore.swift"]), ["localization", "macos"])

    def test_ios_runtime_uses_unit_tests_not_ui_tests(self):
        self.assertEqual(verify.plan(["ios/Shared/MobileStore.swift"]),
                         ["localization", "ios-unit"])

    def test_ios_views_include_behavioral_ui_checks(self):
        self.assertEqual(verify.plan(["ios/Mana/ProviderQuotaCard.swift"]),
                         ["localization", "ios-unit", "ios-ui"])

    def test_translations_include_rendered_ui_checks(self):
        self.assertIn("ios-ui", verify.plan(["ios/Shared/fr.lproj/Localizable.strings"]))

    def test_core_checks_both_consumers_without_ui_capture(self):
        self.assertEqual(verify.plan(["Packages/ManaCore/Sources/ManaCore/CodexUsageClient.swift"]),
                         ["localization", "core", "macos", "ios-unit"])

    def test_explicit_ui_option_adds_ui_checks(self):
        self.assertIn("ios-ui", verify.plan(["ios/Shared/MobileStore.swift"], ui=True))

    def test_unknown_paths_fall_back_to_full_verification(self):
        self.assertIn("ios-full", verify.plan(["new-build-config.json"]))

    def test_full_mode_keeps_all_suites(self):
        self.assertEqual(verify.plan([], full=True),
                         ["tooling", "website", "localization", "core", "macos", "ios-full"])

    def test_workflow_edits_have_a_fast_regression_loop(self):
        self.assertEqual(verify.plan(["scripts/verify.py", "scripts/tests/test_verify.py", "AGENTS.md"]),
                         ["tooling"])

    def test_ci_edits_use_tooling_checks_locally_and_native_suites_in_ci(self):
        self.assertEqual(verify.plan([".github/workflows/ci.yml"]),
                         ["tooling", "website", "localization"])

    def test_ios_wrapper_edits_check_scope_and_real_unit_execution(self):
        self.assertEqual(verify.plan(["scripts/verify-ios.sh"]), ["tooling", "ios-unit"])

    def test_native_documentation_does_not_launch_xcode(self):
        self.assertEqual(verify.plan(["ios/README.md", "Packages/ManaCore/README.md"]), [])

    def test_no_staged_changes_runs_nothing(self):
        self.assertEqual(verify.plan([]), [])

    def test_staged_paths_exclude_unrelated_work(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q", directory], check=True)
            (root / "docs").mkdir()
            (root / "ios").mkdir()
            (root / "docs/index.html").write_text("<html></html>")
            (root / "ios/Unrelated.swift").write_text("// Unrelated work")
            subprocess.run(["git", "add", "docs/index.html"], cwd=root, check=True)
            self.assertEqual(verify.staged_paths(root), ["docs/index.html"])
            self.assertEqual(verify.plan(verify.staged_paths(root)), ["website"])


if __name__ == "__main__":
    unittest.main()
