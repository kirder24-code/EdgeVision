#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p build
OS="$(uname -s)"
case "$OS" in
  Darwin)
    COMPILER="${CXX:-clang++}"
    OUTPUT="build/libedgevision_tracker.dylib"
    "$COMPILER" -std=c++17 -O2 -Wall -Wextra -Werror -fPIC -dynamiclib cpp/tracker.cpp -o "$OUTPUT"
    ;;
  Linux)
    COMPILER="${CXX:-g++}"
    OUTPUT="build/libedgevision_tracker.so"
    "$COMPILER" -std=c++17 -O2 -Wall -Wextra -Werror -fPIC -shared cpp/tracker.cpp -o "$OUTPUT"
    ;;
  *) echo "Unsupported OS: $OS" >&2; exit 2 ;;
esac
printf 'C++ shared library compiled: %s\n' "$OUTPUT"
