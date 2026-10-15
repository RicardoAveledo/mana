#!/bin/zsh
set -euo pipefail

ROOT="${0:A:h:h}"
cd "$ROOT"
# Default remains the complete CI suite. Local verification selects a scope.
TEST_FILTERS=()
case "${1:-}" in
  "") ;;
  --unit) TEST_FILTERS=(-only-testing:ManaIOSTests) ;;
  --ui) TEST_FILTERS=(-only-testing:ManaIOSUITests -skip-testing:ManaIOSUITests/ManaAppStoreScreenshotTests) ;;
  *) print -u2 "Usage: zsh scripts/verify-ios.sh [--unit|--ui]"; exit 2 ;;
esac
if (( $# > 1 )); then
  print -u2 "Usage: zsh scripts/verify-ios.sh [--unit|--ui]"
  exit 2
fi
DESTINATION="${MANA_IOS_DESTINATION:-}"
if [[ -z "$DESTINATION" ]]; then
  DEVICE_ID="$(xcrun simctl list devices available --json | python3 -c '
import json, sys
devices = json.load(sys.stdin)["devices"]
for runtime in sorted(devices, reverse=True):
    if "iOS" not in runtime:
        continue
    for device in devices[runtime]:
        if device.get("isAvailable") and device["name"].startswith("iPhone"):
            print(device["udid"])
            sys.exit(0)
sys.exit("No available iPhone simulator. Install an iOS runtime in Xcode.")
')"
  DESTINATION="platform=iOS Simulator,id=$DEVICE_ID"
fi
mkdir -p build
xcodebuild -project ios/ManaIOS.xcodeproj -scheme ManaIOS -configuration Debug \
  -destination "$DESTINATION" -derivedDataPath build/ios -parallel-testing-enabled NO \
  "${TEST_FILTERS[@]}" test CODE_SIGNING_ALLOWED=YES CODE_SIGN_IDENTITY=-
