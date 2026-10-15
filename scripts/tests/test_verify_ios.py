"""Exercise the actual iOS wrapper without launching Xcode or a simulator."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "verify-ios.sh"


class IOSVerificationScopeTests(unittest.TestCase):
    def command(self, *options):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            capture = root / "arguments.json"
            xcodebuild = root / "xcodebuild"
            xcodebuild.write_text(
                f"#!{sys.executable}\nimport json, os, sys\n"
                "with open(os.environ['CAPTURE'], 'w') as output: json.dump(sys.argv[1:], output)\n"
            )
            xcodebuild.chmod(0o755)
            env = dict(os.environ, PATH=f"{root}:{os.environ['PATH']}", CAPTURE=str(capture),
                       MANA_IOS_DESTINATION="platform=iOS Simulator,id=test-device")
            result = subprocess.run(["zsh", str(SCRIPT), *options], env=env, capture_output=True)
            return result.returncode, json.loads(capture.read_text()) if capture.exists() else []

    def test_default_keeps_full_ci_suite(self):
        code, arguments = self.command()
        self.assertEqual(code, 0)
        self.assertFalse(any("testing:" in argument for argument in arguments))
        self.assertIn("test", arguments)
        self.assertIn("CODE_SIGNING_ALLOWED=YES", arguments)

    def test_unit_scope_does_not_launch_ui_tests(self):
        code, arguments = self.command("--unit")
        self.assertEqual(code, 0)
        self.assertIn("-only-testing:ManaIOSTests", arguments)

    def test_ui_scope_excludes_asset_capture(self):
        code, arguments = self.command("--ui")
        self.assertEqual(code, 0)
        self.assertIn("-only-testing:ManaIOSUITests", arguments)
        self.assertIn("-skip-testing:ManaIOSUITests/ManaAppStoreScreenshotTests", arguments)

    def test_invalid_options_fail_before_starting_xcode(self):
        for options in [("--typo",), ("--unit", "--ui")]:
            with self.subTest(options=options):
                code, arguments = self.command(*options)
                self.assertEqual(code, 2)
                self.assertEqual(arguments, [])


if __name__ == "__main__":
    unittest.main()
