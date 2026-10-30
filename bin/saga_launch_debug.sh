#!/usr/bin/env sh
# Select this as Saga's Ruby executable to capture its launch arguments.
# Logs only; does not launch Ruby or Lich.
set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)"

{
  printf '\n--- Saga invocation: %s ---\n' "$(date '+%Y-%m-%d %H:%M:%S %z')"
  printf 'Working directory: %s\n' "$PWD"
  printf 'Argument count: %s\n' "$#"
  index=0
  for arg in "$@"; do
    index=$((index + 1))
    printf 'arg[%s]: %s\n' "$index" "$arg"
  done
  if [ "$#" -ge 2 ]; then
    printf '\n--- Contents of second argument (%s) ---\n' "$2"
    cat -- "$2"
    printf '\n--- End contents ---\n'
  fi
} >> "$SCRIPT_DIR/saga_launch_debug.log"
