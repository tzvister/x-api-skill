#!/usr/bin/env bash
# x-api-skill installer for OpenClaw / Claude Code / Codex / Copilot / AgentSkills
# Asks for target platform, then installs SKILL.md, x-api-skill.py, and test_runner.py.
# Walks the user through API key setup interactively.
#
# Non-interactive mode (for agents / CI):
#   X_API_SKILL_DIR=~/.claude/skills/x-api-skill bash install.sh --non-interactive
#   Pre-set X_CONSUMER_KEY, X_CONSUMER_SECRET, etc. as env vars.

set -euo pipefail

SKILL_NAME="x-api-skill"
BASE_URL="https://raw.githubusercontent.com/tzvister/x-api-skill/master"

# ── Detect interactive vs non-interactive mode ──
INTERACTIVE=true
for arg in "$@"; do
  case "$arg" in
    --non-interactive|--quiet|-q) INTERACTIVE=false ;;
  esac
done
# Also go non-interactive if stdin is not a terminal
[ -t 0 ] || INTERACTIVE=false

# ── ANSI colors (disabled when non-interactive) ──
if [ "$INTERACTIVE" = true ]; then
  BOLD="\033[1m"
  DIM="\033[2m"
  CYAN="\033[36m"
  YELLOW="\033[33m"
  GREEN="\033[32m"
  RESET="\033[0m"
else
  BOLD="" DIM="" CYAN="" YELLOW="" GREEN="" RESET=""
fi

echo ""
echo -e "  ${BOLD}${CYAN}x-api-skill — X/Twitter CLI for AI agents${RESET}"
echo -e "  ${CYAN}────────────────────────────────────${RESET}"
echo ""

# ── 0. Determine install target ──
if [ "$INTERACTIVE" = true ]; then
  # Check if X_API_SKILL_DIR was pre-set (skip menu)
  if [ -n "${X_API_SKILL_DIR:-}" ]; then
    SKILL_DIR="$X_API_SKILL_DIR"
  else
    echo -e "  ${BOLD}Where are you installing this skill?${RESET}"
    echo ""
    echo -e "    ${BOLD}1${RESET}  OpenClaw       ${DIM}~/.openclaw/skills/x-api-skill/${RESET}"
    echo -e "    ${BOLD}2${RESET}  Claude Code    ${DIM}~/.claude/skills/x-api-skill/${RESET}"
    echo -e "    ${BOLD}3${RESET}  Codex          ${DIM}~/.codex/skills/x-api-skill/${RESET}"
    echo -e "    ${BOLD}4${RESET}  Copilot        ${DIM}~/.copilot/skills/x-api-skill/${RESET}"
    echo -e "    ${BOLD}5${RESET}  Custom path"
    echo ""
    echo -ne "  ${YELLOW}Choose [1-5]${RESET} [${BOLD}1${RESET}]: "
    read -r platform_choice
    platform_choice="${platform_choice:-1}"

    case "$platform_choice" in
      1) SKILL_DIR="$HOME/.openclaw/skills/$SKILL_NAME" ;;
      2) SKILL_DIR="$HOME/.claude/skills/$SKILL_NAME" ;;
      3) SKILL_DIR="$HOME/.codex/skills/$SKILL_NAME" ;;
      4) SKILL_DIR="$HOME/.copilot/skills/$SKILL_NAME" ;;
      5)
        echo -ne "  ${BOLD}Enter full path${RESET}: "
        read -r custom_path
        if [ -z "$custom_path" ]; then
          echo -e "  ${YELLOW}No path given — defaulting to OpenClaw${RESET}"
          SKILL_DIR="$HOME/.openclaw/skills/$SKILL_NAME"
        else
          SKILL_DIR="$custom_path"
        fi
        ;;
      *) SKILL_DIR="$HOME/.openclaw/skills/$SKILL_NAME" ;;
    esac
  fi
else
  # Non-interactive: use X_API_SKILL_DIR or default to OpenClaw
  SKILL_DIR="${X_API_SKILL_DIR:-$HOME/.openclaw/skills/$SKILL_NAME}"
fi

ENV_FILE="$SKILL_DIR/.env"

echo -e "  ${DIM}Installing to ${RESET}${BOLD}$SKILL_DIR${RESET}"
echo ""

# ── 1. Create skill directory ──
mkdir -p "$SKILL_DIR/scripts"

# ── 2. Install skill files ──
# Detect local repo: if SKILL.md exists next to install.sh, copy instead of download
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -f "$SCRIPT_DIR/SKILL.md" ] && [ -f "$SCRIPT_DIR/scripts/x-api-skill.py" ]; then
  echo -e "  ${DIM}Copying files from local repo...${RESET}"

  cp "$SCRIPT_DIR/SKILL.md" "$SKILL_DIR/SKILL.md"
  echo "    SKILL.md"

  cp "$SCRIPT_DIR/scripts/x-api-skill.py" "$SKILL_DIR/scripts/x-api-skill.py"
  echo "    scripts/x-api-skill.py"

  if [ -f "$SCRIPT_DIR/test_runner.py" ]; then
    cp "$SCRIPT_DIR/test_runner.py" "$SKILL_DIR/test_runner.py"
    echo "    test_runner.py"
  fi
else
  echo -e "  ${DIM}Downloading files from GitHub...${RESET}"

  curl -fsSL "$BASE_URL/SKILL.md" -o "$SKILL_DIR/SKILL.md"
  echo "    SKILL.md"

  curl -fsSL "$BASE_URL/scripts/x-api-skill.py" -o "$SKILL_DIR/scripts/x-api-skill.py"
  echo "    scripts/x-api-skill.py"

  # test_runner.py is optional — don't fail if it's not available
  if curl -fsSL "$BASE_URL/test_runner.py" -o "$SKILL_DIR/test_runner.py" 2>/dev/null; then
    echo "    test_runner.py"
  else
    echo "    test_runner.py (not available — skipped)"
  fi
fi

# ── 3. Install Python dependencies ──
echo ""
echo -e "  ${DIM}Checking dependencies...${RESET}"

DEPS_NEEDED=""
python3 -c "import requests" 2>/dev/null || DEPS_NEEDED="requests"
python3 -c "import requests_oauthlib" 2>/dev/null || DEPS_NEEDED="$DEPS_NEEDED requests-oauthlib"
python3 -c "import dotenv" 2>/dev/null || DEPS_NEEDED="$DEPS_NEEDED python-dotenv"

if [ -n "$DEPS_NEEDED" ]; then
  echo "    Installing:$DEPS_NEEDED"
  pip3 install $DEPS_NEEDED 2>/dev/null || pip3 install --user $DEPS_NEEDED
  echo "    Done"
else
  echo "    All dependencies already installed"
fi

# ── 4. API key setup ──

# Helper: prompt for a value, show current if set, allow skip with Enter
prompt_key() {
  local var_name="$1"
  local current="$2"
  local result

  if [ -n "$current" ]; then
    echo -ne "  ${BOLD}${var_name}${RESET} ${DIM}[current: ${current:0:8}...]${RESET} (Enter to keep): " >&2
  else
    echo -ne "  ${BOLD}${var_name}${RESET}: " >&2
  fi
  read -r result
  if [ -n "$result" ]; then
    echo "$result"
  else
    echo "$current"
  fi
}

# Load existing values from .env or env vars
CUR_CONSUMER_KEY="${X_CONSUMER_KEY:-}"
CUR_CONSUMER_SECRET="${X_CONSUMER_SECRET:-}"
CUR_ACCESS_TOKEN="${X_ACCESS_TOKEN:-}"
CUR_ACCESS_SECRET="${X_ACCESS_TOKEN_SECRET:-}"
CUR_BEARER="${X_BEARER_TOKEN:-}"
CUR_CLIENT_ID="${X_CLIENT_ID:-}"
CUR_CLIENT_SECRET="${X_CLIENT_SECRET:-}"

# .env file values override empty env vars
if [ -f "$ENV_FILE" ]; then
  extract_env() { sed -n "s/^$1=\"\\(.*\\)\"/\\1/p" "$ENV_FILE" 2>/dev/null || true; }
  [ -z "$CUR_CONSUMER_KEY" ] && CUR_CONSUMER_KEY=$(extract_env X_CONSUMER_KEY)
  [ -z "$CUR_CONSUMER_SECRET" ] && CUR_CONSUMER_SECRET=$(extract_env X_CONSUMER_SECRET)
  [ -z "$CUR_ACCESS_TOKEN" ] && CUR_ACCESS_TOKEN=$(extract_env X_ACCESS_TOKEN)
  [ -z "$CUR_ACCESS_SECRET" ] && CUR_ACCESS_SECRET=$(extract_env X_ACCESS_TOKEN_SECRET)
  [ -z "$CUR_BEARER" ] && CUR_BEARER=$(extract_env X_BEARER_TOKEN)
  [ -z "$CUR_CLIENT_ID" ] && CUR_CLIENT_ID=$(extract_env X_CLIENT_ID)
  [ -z "$CUR_CLIENT_SECRET" ] && CUR_CLIENT_SECRET=$(extract_env X_CLIENT_SECRET)
fi

if [ "$INTERACTIVE" = true ]; then
  echo ""
  echo -e "  ${CYAN}────────────────────────────────────${RESET}"
  echo -e "  ${BOLD}API Key Setup${RESET}"
  echo ""
  echo -e "  ${DIM}We'll walk you through each credential.${RESET}"
  echo -e "  ${DIM}Don't have a key handy? Just press Enter to skip it.${RESET}"
  echo -e "  ${DIM}You can always add or change keys later in:${RESET}"
  echo -e "  ${BOLD}  $ENV_FILE${RESET}"
  echo ""

  # ── Step 1: OAuth 1.0a (required) ──
  echo -e "  ${BOLD}Step 1: OAuth 1.0a${RESET} ${YELLOW}(required)${RESET}"
  echo ""
  echo -e "  ${DIM}These 4 keys are needed for all core commands (tweet, search, follow, etc.).${RESET}"
  echo ""
  echo -e "  ${DIM}Where to find them:${RESET}"
  echo -e "  ${DIM}  1. Go to ${RESET}${BOLD}https://developer.x.com/en/portal/dashboard${RESET}"
  echo -e "  ${DIM}  2. Select your app (or create one)${RESET}"
  echo -e "  ${DIM}  3. Go to \"Keys and tokens\" tab${RESET}"
  echo -e "  ${DIM}  4. Under \"Consumer Keys\" — copy API Key and API Secret${RESET}"
  echo -e "  ${DIM}  5. Under \"Authentication Tokens\" — generate Access Token & Secret${RESET}"
  echo -e "  ${DIM}     Make sure app permissions are set to \"Read and Write\" BEFORE generating tokens${RESET}"
  echo -e "  ${DIM}  (Enter to skip any key — add to .env later)${RESET}"
  echo ""

  CONSUMER_KEY=$(prompt_key "X_CONSUMER_KEY" "$CUR_CONSUMER_KEY")
  CONSUMER_SECRET=$(prompt_key "X_CONSUMER_SECRET" "$CUR_CONSUMER_SECRET")
  ACCESS_TOKEN=$(prompt_key "X_ACCESS_TOKEN" "$CUR_ACCESS_TOKEN")
  ACCESS_SECRET=$(prompt_key "X_ACCESS_TOKEN_SECRET" "$CUR_ACCESS_SECRET")

  # ── Step 2: Bearer Token (optional) ──
  echo ""
  echo -e "  ${BOLD}Step 2: Bearer Token${RESET} ${DIM}(optional — for streams, trends, spaces)${RESET}"
  echo ""
  echo -e "  ${DIM}Where to find it:${RESET}"
  echo -e "  ${DIM}  Same page → \"Keys and tokens\" → \"Bearer Token\" section${RESET}"
  echo -e "  ${DIM}  Click \"Generate\" if you haven't already${RESET}"
  echo -e "  ${DIM}  (Enter to skip — add to .env later)${RESET}"
  echo ""

  BEARER_TOKEN=$(prompt_key "X_BEARER_TOKEN" "$CUR_BEARER")

  # ── Step 3: OAuth 2.0 PKCE (optional) ──
  echo ""
  echo -e "  ${BOLD}Step 3: OAuth 2.0 Client ID${RESET} ${DIM}(optional — for bookmarks)${RESET}"
  echo ""
  echo -e "  ${DIM}Where to find it:${RESET}"
  echo -e "  ${DIM}  Same app → \"Keys and tokens\" → \"OAuth 2.0 Client ID and Client Secret\"${RESET}"
  echo -e "  ${DIM}  If you don't see it, enable OAuth 2.0 in your app's \"User authentication settings\"${RESET}"
  echo -e "  ${DIM}  (Enter to skip — add to .env later)${RESET}"
  echo ""

  CLIENT_ID=$(prompt_key "X_CLIENT_ID" "$CUR_CLIENT_ID")
  CLIENT_SECRET=$(prompt_key "X_CLIENT_SECRET" "$CUR_CLIENT_SECRET")
else
  # Non-interactive: use whatever was in env vars / existing .env
  CONSUMER_KEY="$CUR_CONSUMER_KEY"
  CONSUMER_SECRET="$CUR_CONSUMER_SECRET"
  ACCESS_TOKEN="$CUR_ACCESS_TOKEN"
  ACCESS_SECRET="$CUR_ACCESS_SECRET"
  BEARER_TOKEN="$CUR_BEARER"
  CLIENT_ID="$CUR_CLIENT_ID"
  CLIENT_SECRET="$CUR_CLIENT_SECRET"
  echo "  Using API keys from environment variables / existing .env"
fi

# ── Write .env ──
cat > "$ENV_FILE" << ENVEOF
# === OAuth 1.0a (required — core functionality) ===
# Get these from https://developer.x.com/en/portal/dashboard
X_CONSUMER_KEY="${CONSUMER_KEY}"
X_CONSUMER_SECRET="${CONSUMER_SECRET}"
X_ACCESS_TOKEN="${ACCESS_TOKEN}"
X_ACCESS_TOKEN_SECRET="${ACCESS_SECRET}"

# === Bearer Token (required for streams, trends, spaces, full-archive search) ===
# Get from https://developer.x.com/en/portal/dashboard → Keys and tokens → Bearer Token
X_BEARER_TOKEN="${BEARER_TOKEN}"

# === OAuth 2.0 PKCE (optional — bookmarks) ===
# After setting these, run: python3 scripts/x-api-skill.py auth
X_CLIENT_ID="${CLIENT_ID}"
X_CLIENT_SECRET="${CLIENT_SECRET}"
ENVEOF

echo ""
echo -e "  ${GREEN}Saved credentials to $ENV_FILE${RESET}"

# ── 5. Verify (if OAuth 1.0a keys were provided) ──
if [ -n "$CONSUMER_KEY" ] && [ -n "$ACCESS_TOKEN" ]; then
  echo ""
  echo -e "  ${DIM}Verifying authentication...${RESET}"
  export X_CONSUMER_KEY="$CONSUMER_KEY"
  export X_CONSUMER_SECRET="$CONSUMER_SECRET"
  export X_ACCESS_TOKEN="$ACCESS_TOKEN"
  export X_ACCESS_TOKEN_SECRET="$ACCESS_SECRET"

  if python3 "$SKILL_DIR/scripts/x-api-skill.py" verify 2>/dev/null; then
    echo -e "  ${GREEN}Authentication verified!${RESET}"
  else
    echo -e "  ${YELLOW}Could not verify — double-check your keys in $ENV_FILE${RESET}"
  fi
fi

# ── 6. OAuth 2.0 PKCE auth flow (if Client ID was provided) ──
if [ -n "$CLIENT_ID" ] && [ "$INTERACTIVE" = true ]; then
  echo ""
  echo -e "  ${BOLD}Bookmark auth setup${RESET}"
  echo -e "  ${DIM}Bookmarks require a one-time browser authorization (OAuth 2.0 PKCE).${RESET}"
  echo -e "  ${DIM}This will open your browser — sign in and click \"Authorize app\".${RESET}"
  echo -ne "  ${YELLOW}Run auth now? (y/n)${RESET} [${BOLD}y${RESET}]: "
  read -r run_auth
  run_auth="${run_auth:-y}"
  if [ "$run_auth" = "y" ] || [ "$run_auth" = "Y" ] || [ "$run_auth" = "yes" ]; then
    export X_CLIENT_ID="$CLIENT_ID"
    export X_CLIENT_SECRET="$CLIENT_SECRET"
    echo ""
    echo -e "  ${DIM}Starting auth flow — check your browser...${RESET}"
    if python3 "$SKILL_DIR/scripts/x-api-skill.py" auth; then
      echo -e "  ${GREEN}Bookmark auth complete! Tokens saved to ~/.x-api-skill/tokens.json${RESET}"
    else
      echo -e "  ${YELLOW}Auth flow did not complete. You can retry later:${RESET}"
      echo -e "    python3 $SKILL_DIR/scripts/x-api-skill.py auth"
    fi
  else
    echo -e "  ${DIM}Skipped. Run this later to enable bookmarks:${RESET}"
    echo -e "    python3 $SKILL_DIR/scripts/x-api-skill.py auth"
  fi
elif [ -n "$CLIENT_ID" ]; then
  echo ""
  echo "  Bookmark auth requires interactive mode. Run manually:"
  echo "    python3 $SKILL_DIR/scripts/x-api-skill.py auth"
fi

# ── 7. Summary ──
echo ""
echo -e "  ${CYAN}────────────────────────────────────${RESET}"
echo -e "  ${GREEN}${BOLD}Installation complete!${RESET}"
echo ""

FILLED=0
[ -n "$CONSUMER_KEY" ] && FILLED=$((FILLED + 1))
[ -n "$BEARER_TOKEN" ] && FILLED=$((FILLED + 1))
[ -n "$CLIENT_ID" ] && FILLED=$((FILLED + 1))

if [ "$FILLED" -eq 3 ]; then
  echo -e "  ${GREEN}All credentials configured.${RESET}"
elif [ "$FILLED" -gt 0 ]; then
  echo -e "  ${DIM}Some credentials were skipped — edit $ENV_FILE to add them later.${RESET}"
else
  echo -e "  ${YELLOW}No credentials entered — edit $ENV_FILE before using x-api-skill.${RESET}"
fi

echo ""
echo -e "  ${BOLD}Quick start:${RESET}"
echo -e "    python3 $SKILL_DIR/scripts/x-api-skill.py --help"
echo -e "    python3 $SKILL_DIR/scripts/x-api-skill.py verify"
echo -e "    python3 $SKILL_DIR/test_runner.py"
echo ""
