#!/usr/bin/env bash
# xpost skill installer for OpenClaw / AgentSkills
# Installs SKILL.md, xpost.py, and test_runner.py into ~/.openclaw/skills/xpost/

set -euo pipefail

SKILL_NAME="xpost"
SKILL_DIR="$HOME/.openclaw/skills/$SKILL_NAME"
BASE_URL="https://syn-ack.ai/skills/$SKILL_NAME"

echo ""
echo "  xpost — X/Twitter CLI for AI agents"
echo "  Installing to $SKILL_DIR"
echo "  ────────────────────────────────────"
echo ""

# 1. Create skill directory
mkdir -p "$SKILL_DIR/scripts"

# 2. Download skill files
echo "  Downloading files..."

curl -fsSL "$BASE_URL/SKILL.md" -o "$SKILL_DIR/SKILL.md"
echo "    SKILL.md"

curl -fsSL "$BASE_URL/scripts/xpost.py" -o "$SKILL_DIR/scripts/xpost.py"
echo "    scripts/xpost.py"

curl -fsSL "$BASE_URL/test_runner.py" -o "$SKILL_DIR/test_runner.py"
echo "    test_runner.py"

# 3. Install Python dependencies
echo ""
echo "  Checking dependencies..."

DEPS_NEEDED=""
python3 -c "import requests" 2>/dev/null || DEPS_NEEDED="requests"
python3 -c "import requests_oauthlib" 2>/dev/null || DEPS_NEEDED="$DEPS_NEEDED requests-oauthlib"
python3 -c "import dotenv" 2>/dev/null || DEPS_NEEDED="$DEPS_NEEDED python-dotenv"

if [ -n "$DEPS_NEEDED" ]; then
  echo "    Installing:$DEPS_NEEDED"
  pip3 install $DEPS_NEEDED || pip3 install --user $DEPS_NEEDED
  echo "    Done"
else
  echo "    All dependencies already installed"
fi

# 4. Create .env template if it doesn't exist
ENV_FILE="$SKILL_DIR/.env"
if [ ! -f "$ENV_FILE" ]; then
  cat > "$ENV_FILE" << 'ENVEOF'
# === OAuth 1.0a (required — core functionality) ===
# Get these from https://developer.x.com/en/portal/dashboard
X_CONSUMER_KEY=""
X_CONSUMER_SECRET=""
X_ACCESS_TOKEN=""
X_ACCESS_TOKEN_SECRET=""

# === Bearer Token (required for streams, trends, spaces, full-archive search) ===
# Get from https://developer.x.com/en/portal/dashboard
X_BEARER_TOKEN=""

# === OAuth 2.0 PKCE (optional — bookmarks) ===
# Only needed if you want to use bookmark commands
X_CLIENT_ID=""
X_CLIENT_SECRET=""
ENVEOF
  echo ""
  echo "  Created .env template at $ENV_FILE"
  echo "  Fill in your API credentials before using xpost."
else
  echo ""
  echo "  .env already exists at $ENV_FILE (not overwritten)"
fi

# 5. Summary
echo ""
echo "  ────────────────────────────────────"
echo "  Installed successfully!"
echo ""
echo "  Setup:"
echo "    1. Edit $ENV_FILE with your API keys"
echo "    2. Run: python3 $SKILL_DIR/scripts/xpost.py verify"
echo ""
echo "  Required credentials (OAuth 1.0a):"
echo "    X_CONSUMER_KEY, X_CONSUMER_SECRET"
echo "    X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET"
echo ""
echo "  Optional credentials:"
echo "    X_BEARER_TOKEN    — for streams, trends, spaces"
echo "    X_CLIENT_ID       — for bookmarks (run 'auth' after setting)"
echo ""
echo "  Quick start:"
echo "    python3 $SKILL_DIR/scripts/xpost.py --help"
echo "    python3 $SKILL_DIR/test_runner.py"
echo ""
