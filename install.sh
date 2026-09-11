#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_NAME="chatgpt-ads"
DRY_RUN=0
UPGRADE=0
FORCE=0
UNINSTALL=0
EXPLICIT_TARGET=""

usage() {
  cat <<'EOF'
Usage: ./install.sh [--dry-run] [--target PATH] [--upgrade|--force] [--uninstall]

Installs only the reviewed runtime artifact. Existing targets are preserved as
sibling backups during upgrade. Windows is not supported by this shell installer.
EOF
}

while (($#)); do
  case "$1" in
    --dry-run) DRY_RUN=1 ;;
    --upgrade) UPGRADE=1 ;;
    --force) FORCE=1 ;;
    --uninstall) UNINSTALL=1 ;;
    --target)
      shift
      (($#)) || { echo "--target requires a path" >&2; exit 2; }
      EXPLICIT_TARGET="$1"
      ;;
    --help|-h) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

case "$(uname -s 2>/dev/null || true)" in
  MINGW*|MSYS*|CYGWIN*) echo "Windows installation is unsupported; use the source checkout capability boundary." >&2; exit 2 ;;
esac

validate_target() {
  local target="$1"
  python3 - "$SCRIPT_DIR" "$target" "$HOME" <<'PY'
import os, sys
source, target, home = map(os.path.realpath, sys.argv[1:])
if target in {os.path.sep, home}:
    raise SystemExit("Refusing root or HOME as an installation target")
try:
    overlap = os.path.commonpath([source, target]) in {source, target}
except ValueError:
    overlap = False
if overlap:
    raise SystemExit("Refusing a target that overlaps the source checkout")
PY
}

uninstall_target() {
  local target="$1"
  validate_target "$target"
  if [[ ! -e "$target" ]]; then
    echo "Not installed: $target"
    return 0
  fi
  if [[ ! -f "$target/.chatgpt-ads-install.json" && "$FORCE" -ne 1 ]]; then
    echo "Refusing to uninstall an unmarked target; use --force to preserve it as a removal backup." >&2
    return 2
  fi
  local removed="${target}.removed.$(date +%Y%m%d%H%M%S).$$"
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "DRY RUN: would move $target to $removed"
    return 0
  fi
  mv "$target" "$removed"
  echo "Uninstalled $target; preserved previous files at $removed"
}

install_target() {
  local target="$1"
  validate_target "$target"
  python3 "$SCRIPT_DIR/scripts/install_artifact.py" --source "$SCRIPT_DIR" --check >/dev/null
  if [[ -e "$target" && "$UPGRADE" -ne 1 && "$FORCE" -ne 1 ]]; then
    echo "Target exists; use --upgrade or --force: $target" >&2
    return 2
  fi
  if [[ -e "$target" && "$UPGRADE" -eq 1 && ! -f "$target/.chatgpt-ads-install.json" ]]; then
    echo "--upgrade requires an existing marked ChatGPT Ads installation; use --force for other targets" >&2
    return 2
  fi
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "DRY RUN: artifact and target checks passed; would atomically install at $target"
    return 0
  fi

  local parent base stage backup=""
  parent="$(dirname "$target")"
  base="$(basename "$target")"
  mkdir -p "$parent"
  stage="$parent/.${base}.stage.$$"
  [[ ! -e "$stage" ]] || { echo "Staging path already exists: $stage" >&2; return 2; }
  trap 'rm -rf -- "$stage"' RETURN
  python3 "$SCRIPT_DIR/scripts/install_artifact.py" --source "$SCRIPT_DIR" --out "$stage" >/dev/null
  cat >"$stage/.chatgpt-ads-install.json" <<EOF
{
  "schema_version": 1,
  "artifact": "chatgpt-ads-public-distribution",
  "source_version": "$(python3 -c 'import tomllib,sys; print(tomllib.load(open(sys.argv[1],"rb"))["project"]["version"])' "$SCRIPT_DIR/pyproject.toml")",
  "scope": "exact hash-listed public projection; excludes git metadata, planning files, private data, and unreviewed local files"
}
EOF

  (cd "$stage" && python3 -m chatgpt_ads_brain --help >/dev/null)

  if [[ -e "$target" ]]; then
    if [[ "$UPGRADE" -ne 1 && "$FORCE" -ne 1 ]]; then
      echo "Target exists; use --upgrade or --force: $target" >&2
      return 2
    fi
    backup="${target}.backup.$(date +%Y%m%d%H%M%S).$$"
    mv "$target" "$backup"
  fi

  if ! mv "$stage" "$target"; then
    [[ -z "$backup" ]] || mv "$backup" "$target"
    echo "Atomic replacement failed; previous installation restored" >&2
    return 1
  fi
  trap - RETURN

  if ! (cd "$target" && python3 -m chatgpt_ads_brain --help >/dev/null); then
    local failed="${target}.failed.$(date +%Y%m%d%H%M%S).$$"
    mv "$target" "$failed"
    [[ -z "$backup" ]] || mv "$backup" "$target"
    echo "Installed smoke test failed; previous installation restored" >&2
    return 1
  fi
  echo "Installed runtime artifact at $target"
  [[ -z "$backup" ]] || echo "Preserved previous installation at $backup"
}

TARGETS=()
if [[ -n "$EXPLICIT_TARGET" ]]; then
  TARGETS+=("$EXPLICIT_TARGET")
else
  [[ -d "$HOME/.claude" || "$(command -v claude || true)" ]] && TARGETS+=("$HOME/.claude/skills/$TARGET_NAME")
  [[ -d "$HOME/.gemini" ]] && TARGETS+=("$HOME/.gemini/config/skills/$TARGET_NAME")
  [[ -d "$HOME/.codex" ]] && TARGETS+=("$HOME/.codex/skills/$TARGET_NAME")
  TARGETS+=("$HOME/.agents/skills/$TARGET_NAME")
fi

for target in "${TARGETS[@]}"; do
  if [[ "$UNINSTALL" -eq 1 ]]; then
    uninstall_target "$target"
  else
    install_target "$target"
  fi
done
