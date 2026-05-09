#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Bump version across all package manifests and create a git tag.
# Usage: ./scripts/version-bump.sh <new-version>
# Example: ./scripts/version-bump.sh 0.2.0

set -euo pipefail

if [ $# -ne 1 ]; then
    echo "Usage: $0 <new-version>"
    echo "Example: $0 0.2.0"
    exit 1
fi

NEW_VERSION="$1"

if ! echo "$NEW_VERSION" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.]+)?$'; then
    echo "Error: Version must be valid semver (e.g., 0.2.0 or 1.0.0-rc.1)"
    exit 1
fi

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "Bumping to version $NEW_VERSION..."

# 1. sdk/pyproject.toml
sed -i.bak "s/^version = \".*\"/version = \"$NEW_VERSION\"/" "$REPO_ROOT/sdk/pyproject.toml"
rm -f "$REPO_ROOT/sdk/pyproject.toml.bak"
echo "  Updated sdk/pyproject.toml"

# 2. sdk/web_control/package.json
sed -i.bak "s/\"version\": \".*\"/\"version\": \"$NEW_VERSION\"/" "$REPO_ROOT/sdk/web_control/package.json"
rm -f "$REPO_ROOT/sdk/web_control/package.json.bak"
echo "  Updated sdk/web_control/package.json"

# 3. Root package.json
sed -i.bak "s/\"version\": \".*\"/\"version\": \"$NEW_VERSION\"/" "$REPO_ROOT/package.json"
rm -f "$REPO_ROOT/package.json.bak"
echo "  Updated package.json"

# 4. ROS2 package.xml files
find "$REPO_ROOT/ros2_ws" -name "package.xml" -exec \
    sed -i.bak "s|<version>.*</version>|<version>$NEW_VERSION</version>|" {} \;
find "$REPO_ROOT/ros2_ws" -name "package.xml.bak" -delete
echo "  Updated ros2_ws/*/package.xml"

# 5. CHANGELOG header (add unreleased section if not present)
CHANGELOG="$REPO_ROOT/CHANGELOG.md"
if [ -f "$CHANGELOG" ]; then
    TODAY=$(date +%Y-%m-%d)
    if ! grep -q "## \[$NEW_VERSION\]" "$CHANGELOG"; then
        sed -i.bak "0,/^## \[/s//## [$NEW_VERSION] - $TODAY\n\n## [/" "$CHANGELOG"
        rm -f "$CHANGELOG.bak"
        echo "  Updated CHANGELOG.md"
    fi
fi

echo ""
echo "Version bumped to $NEW_VERSION"
echo ""
echo "Next steps:"
echo "  1. Review changes: git diff"
echo "  2. Commit: git commit -am \"chore: bump version to $NEW_VERSION\""
echo "  3. Tag: git tag v$NEW_VERSION"
echo "  4. Push: git push && git push --tags"
