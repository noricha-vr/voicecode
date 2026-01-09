#!/bin/bash
# Homebrew Formula の SHA256 を計算するヘルパースクリプト
#
# 使用方法:
#   ./scripts/generate_formula.sh [VERSION]
#
# 例:
#   ./scripts/generate_formula.sh 0.1.0
#   ./scripts/generate_formula.sh 0.2.0

set -e

VERSION=${1:-"0.1.0"}
REPO="noricha-vr/voicecode"
URL="https://github.com/${REPO}/archive/refs/tags/v${VERSION}.tar.gz"

echo "VoiceCode Homebrew Formula SHA256 Generator"
echo "============================================"
echo ""
echo "Version: v${VERSION}"
echo "URL: ${URL}"
echo ""

# Check if the tag exists
echo "Checking if tag exists..."
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -I "${URL}")

if [ "$HTTP_STATUS" = "404" ]; then
    echo ""
    echo "ERROR: Tag v${VERSION} does not exist yet."
    echo ""
    echo "To create a release:"
    echo "  1. Update version in pyproject.toml"
    echo "  2. Commit and push changes"
    echo "  3. Create a tag: git tag v${VERSION}"
    echo "  4. Push the tag: git push origin v${VERSION}"
    echo "  5. Run this script again"
    exit 1
fi

echo "Downloading and calculating SHA256..."
SHA256=$(curl -sL "${URL}" | shasum -a 256 | cut -d' ' -f1)

echo ""
echo "============================================"
echo "Results"
echo "============================================"
echo ""
echo "SHA256: ${SHA256}"
echo ""
echo "Update homebrew/voicecode.rb with:"
echo ""
echo "  url \"https://github.com/${REPO}/archive/refs/tags/v${VERSION}.tar.gz\""
echo "  sha256 \"${SHA256}\""
echo ""
