#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p build
g++ -std=c++17 -O2 -Wall -Wextra -Werror -fPIC -shared cpp/tracker.cpp -o build/libedgevision_tracker.so
printf 'C++ shared library compiled: build/libedgevision_tracker.so\n'
