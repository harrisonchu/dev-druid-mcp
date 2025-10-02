#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/apache/druid.git"
TARGET_DIR="druid-src"
BRANCH="druid-29.0.0-rc1"

color_enabled() {
  [ -t 1 ]
}

print_intro_art() {
  if color_enabled; then
    local cyan=$'\033[38;5;45m'
    local teal=$'\033[38;5;37m'
    local green=$'\033[38;5;82m'
    local purple=$'\033[38;5;129m'
    local sand=$'\033[38;5;180m'
    local reset=$'\033[0m'
    printf '%s\n' \
      "${cyan}                 _______${reset}" \
      "${cyan}               .'${teal} _____ ${cyan}'.${reset}" \
      "${cyan}              / /${teal}     ${cyan}\\ \\${reset}" \
      "${cyan}             | |${teal}  DATA ${cyan}| |${reset}" \
      "${cyan}              \\ \\_____/ /${reset}" \
      "${cyan}               '._____.'${reset}" \
      "${teal}                  ||${reset}" \
      "${teal}              ___ ${purple}|| ${teal}___${reset}" \
      "${teal}             /   \\${purple}||${teal}/   \\${reset}" \
      "${teal}            / /|  ${purple}\\/${teal}  |\\ \\${reset}" \
      "${teal}           /_/ |${sand} (**) ${teal}| \\_\\${reset}" \
      "${green}              /  /\\  \\${reset}" \
      "${green}             /  /  \\  \\${reset}" \
      "${green}            /__/====\\__\\${reset}" \
      "${green}             /  /  \\  \\${reset}" \
      "${green}            /__/    \\__\\${reset}" \
      "${sand}            /_/        \\_\\${reset}"
  else
    cat <<'ART'
                 _______
               .' _____ '.
              / /     \ \
             | |  DATA | |
              \ \_____/ /
               '._____.'
                  ||
              ___ || ___
             /   \||/   \
            / /|  \/  |\ \
           /_/ | (**) | \_\
              /  /\  \
             /  /  \  \
            /__/====\__\
             /  /  \  \
            /__/    \__\
            /_/        \_\
ART
  fi
}

print_success_art() {
  if color_enabled; then
    local magenta=$'\033[38;5;201m'
    local orange=$'\033[38;5;208m'
    local yellow=$'\033[38;5;226m'
    local green=$'\033[38;5;82m'
    local purple=$'\033[38;5;129m'
    local sand=$'\033[38;5;180m'
    local reset=$'\033[0m'
    printf '%s\n' \
      "${magenta}                 *  |  *${reset}" \
      "${magenta}              *  ${yellow}\\ | /${magenta}  *${reset}" \
      "${yellow}                \\${orange}\\|//${yellow} /${reset}" \
      "${orange}               --${yellow}★${orange}--${reset}" \
      "${yellow}                //${orange}|\\\\${yellow} \\${reset}" \
      "${magenta}              *  ${yellow}/ | \\${magenta}  *${reset}" \
      "${magenta}                 *  |  *${reset}" \
      "${purple}              ___ || ___${reset}" \
      "${purple}             /   \\||/   \\${reset}" \
      "${purple}            / /|  \/  |\\ \\${reset}" \
      "${purple}           /_/ |${sand} (**) ${purple}| \\_\\${reset}" \
      "${green}              /  /\\  \\${reset}" \
      "${green}             /  /  \\  \\${reset}" \
      "${green}            /__/====\\__\\${reset}" \
      "${green}             /  /  \\  \\${reset}" \
      "${green}            /__/    \\__\\${reset}" \
      "${sand}            /_/        \\_\\${reset}" \
      "${yellow}        ✨ Mission conjured! ✨${reset}"
  else
    cat <<'ART'
                 *  |  *
              *   \ | /   *
                \ \|// /
               -- ★ --
                //|\\ \
              *   / | \   *
                 *  |  *
              ___ || ___
             /   \||/   \
            / /|  \/  |\ \
           /_/ | (**) | \_\
              /  /\  \
             /  /  \  \
            /__/====\__\
             /  /  \  \
            /__/    \__\
            /_/        \_\
        ✨ Mission conjured! ✨
ART
  fi
}

print_intro_art

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

print_success_art
