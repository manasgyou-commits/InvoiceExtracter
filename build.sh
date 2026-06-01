#!/usr/bin/env bash
# build.sh — Build Invoice Extractor Pro APK with Buildozer
set -euo pipefail

echo "=== Invoice Extractor Pro — APK Build ==="

if ! command -v buildozer &>/dev/null; then
    echo "buildozer not found. Installing..."
    pip install buildozer cython
fi

# Clean previous artefacts
rm -rf bin/ .buildozer/

echo "Building debug APK..."
buildozer android debug

mkdir -p output
mv bin/*.apk output/ 2>/dev/null || true

echo ""
echo "Build complete. APK is in output/"
ls -lh output/*.apk 2>/dev/null || echo "(no APK found — check build log)"
