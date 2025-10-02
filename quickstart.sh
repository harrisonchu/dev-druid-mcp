#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/apache/druid.git"
TARGET_DIR="druid-src"
BRANCH="druid-29.0.0-rc1"

GREEN=$'\033[32m'
RED=$'\033[31m'
RESET=$'\033[0m'

require_command() {
  local cmd="$1"
  local description="$2"
  local failure_message="$3"
  if command -v "$cmd" >/dev/null 2>&1; then
    printf '%b\n' "${GREEN}PASS${RESET}: $description"
  else
    printf '%b\n' "${RED}FAIL${RESET}: $failure_message" >&2
    exit 1
  fi
}

if [ -d "$TARGET_DIR/.git" ]; then
  echo "Repository already exists in $TARGET_DIR; skipping clone."
else
  if [ -d "$TARGET_DIR" ]; then
    echo "Error: $TARGET_DIR exists but is not a git repository. Remove or rename it before re-running." >&2
    exit 1
  fi
  git clone --branch "$BRANCH" --single-branch "$REPO_URL" "$TARGET_DIR"
fi

require_command "docker" "Docker is installed." "Docker is required but not installed. Install Docker before re-running this script."
require_command "mvn" "Apache Maven is installed." "Apache Maven is required but not installed. Install Maven before re-running this script."
require_command "python3" "Python 3 is installed." "Python 3 is required but not installed. Install Python 3 before re-running this script."
require_command "java" "Java is installed." "Java 17 is required but Java is not installed. Install Java 17 before re-running this script."

JAVA_VERSION_STRING=$(java -version 2>&1 | awk -F\" '/version/ {print $2; exit}')
if [ -z "$JAVA_VERSION_STRING" ]; then
  printf '%b\n' "${RED}FAIL${RESET}: Unable to determine the installed Java version. Ensure Java 17 is installed and active before re-running this script." >&2
  exit 1
fi

JAVA_VERSION_MAJOR=$(printf '%s\n' "$JAVA_VERSION_STRING" | cut -d. -f1)
if [ "$JAVA_VERSION_MAJOR" = "1" ]; then
  JAVA_VERSION_MAJOR=$(printf '%s\n' "$JAVA_VERSION_STRING" | cut -d. -f2)
fi

if [ "$JAVA_VERSION_MAJOR" != "17" ]; then
  printf '%b\n' "${RED}FAIL${RESET}: Java 17 is required but the current version is $JAVA_VERSION_STRING. Switch to a Java 17 runtime before re-running this script." >&2
  exit 1
fi

printf '%b\n' "${GREEN}PASS${RESET}: Java 17 detected ($JAVA_VERSION_STRING)."

mkdir -p sessions
