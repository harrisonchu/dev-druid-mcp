#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/apache/druid.git"
TARGET_DIR="druid-src"
BRANCH="druid-29.0.0-rc1"

if [ -d "$TARGET_DIR/.git" ]; then
  echo "Repository already exists in $TARGET_DIR; skipping clone."
else
  if [ -d "$TARGET_DIR" ]; then
    echo "Error: $TARGET_DIR exists but is not a git repository. Remove or rename it before re-running." >&2
    exit 1
  fi
  git clone --branch "$BRANCH" --single-branch "$REPO_URL" "$TARGET_DIR"
fi

mkdir -p sessions
