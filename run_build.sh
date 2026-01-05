#!/bin/bash
# Simple wrapper to run build and capture output

cd "$(dirname "$0")"

echo "Starting build..." > build_progress.log
date >> build_progress.log

python3 build_windows.py >> build_progress.log 2>&1

echo "Build finished" >> build_progress.log
date >> build_progress.log

echo "✅ Build completed! Check build_progress.log for details"
