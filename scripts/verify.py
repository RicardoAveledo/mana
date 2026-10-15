#!/usr/bin/env python3
"""Run checks for staged paths, explicit paths, or the full repository.

Path selection uses the index by default, not unrelated unstaged work.
Commands validate working-tree contents; stage the intended changes first.
CI continues to run the full native suites independently.
"""

from __future__ import annotations

import argparse
import shlex
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STEPS = {
    "tooling": ["python3", "-m", "unittest", "discover", "-s", "scripts/tests", "-v"],
    "website": ["python3", "scripts/verify-website.py"],
    "localization": ["python3", "scripts/verify-localizations.py"],
    "core": ["swift", "test", "--package-path", "Packages/ManaCore"],
    "macos": ["xcodebuild", "-project", "Mana.xcodeproj", "-scheme", "Mana",
              "-configuration", "Debug", "-destination", "platform=macOS,arch=arm64", "test"],
    "ios-unit": ["zsh", "scripts/verify-ios.sh", "--unit"],
    "ios-ui": ["zsh", "scripts/verify-ios.sh", "--ui"],
    "ios-full": ["zsh", "scripts/verify-ios.sh"],
}
FULL = {"tooling", "website", "localization", "core", "macos", "ios-full"}


def staged_paths(root: Path = ROOT) -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--no-renames", "-z"],
        cwd=root, check=True, capture_output=True,
    )
    return result.stdout.decode().rstrip("\0").split("\0") if result.stdout else []


def plan(paths: list[str], *, full: bool = False, ui: bool = False) -> list[str]:
    selected = set(FULL) if full else set()
    for path in paths:
        if path.startswith("docs/") or path == "scripts/social-card.py":
            selected.add("website")
        elif path in {"scripts/verify.py", "scripts/verify-website.py"} or path.startswith("scripts/tests/"):
            selected.add("tooling")
            if path == "scripts/verify-website.py":
                selected.add("website")
        elif path == "scripts/verify-ios.sh":
            selected.update({"tooling", "ios-unit"})
        elif path == ".github/workflows/ci.yml":
            selected.update({"tooling", "website", "localization"})
        elif path.endswith(".md") or path.startswith(("app-store-release-prep/", ".agents/")):
            continue
        elif path.startswith(("Mana/", "ManaTests/", "Mana.xcodeproj/")):
            selected.update({"localization", "macos"})
        elif path.startswith("Packages/ManaCore/"):
            selected.update({"localization", "core", "macos", "ios-unit"})
            if ".lproj/" in path:
                selected.add("ios-ui")
        elif path.startswith("ios/") or path == "scripts/generate-ios-project.py":
            selected.update({"localization", "ios-unit"})
            if (path.startswith(("ios/Mana/", "ios/ManaWidgets/", "ios/ManaUITests/", "ios/ManaIOS.xcodeproj/"))
                    or Path(path).name.endswith("View.swift")
                    or ".lproj/" in path or path == "scripts/generate-ios-project.py"):
                selected.add("ios-ui")
        else:
            # Unknown build/configuration changes must not silently bypass tests.
            selected.update(FULL)
    if ui and "ios-unit" in selected:
        selected.add("ios-ui")
    if "ios-full" in selected:
        selected.difference_update({"ios-unit", "ios-ui"})
    return [name for name in STEPS if name in selected]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", help="Repository-relative paths; defaults to staged paths")
    parser.add_argument("--staged", action="store_true", help="Use staged paths (the default)")
    parser.add_argument("--full", action="store_true", help="Run every check, including screenshot UI tests")
    parser.add_argument("--ui", action="store_true", help="Include behavioral UI tests for iOS runtime changes")
    parser.add_argument("--dry-run", action="store_true", help="Print commands without running them")
    args = parser.parse_args()
    if args.paths and args.staged:
        parser.error("Choose explicit paths or --staged, not both")
    paths = args.paths or ([] if args.full else staged_paths())
    if any(Path(path).is_absolute() or ".." in Path(path).parts for path in paths):
        parser.error("Paths must be repository-relative without '..'")
    paths = [Path(path).as_posix() for path in paths]
    steps = plan(paths, full=args.full, ui=args.ui)
    if not steps:
        print("No executable checks selected. Stage changes or supply paths; use --full for all checks.")
        return
    print("Verification: " + ", ".join(steps), flush=True)
    for step in steps:
        command = STEPS[step]
        print("+ " + shlex.join(command), flush=True)
        if not args.dry_run:
            subprocess.run(command, cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
