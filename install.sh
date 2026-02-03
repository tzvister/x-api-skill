#!/usr/bin/env bash
# xpost skill installer for OpenClaw
# Installs SKILL.md + xpost.py into ~/.openclaw/skills/xpost/

set -euo pipefail

SKILL_NAME="xpost"
SKILL_DIR="$HOME/.openclaw/skills/$SKILL_NAME"
BASE_URL="https://syn-ack.ai/skills/$SKILL_NAME"

echo "🐦‍⬛ Installing xpost skill..."

# 1. Create skill directory
mkdir -p "$SKILL_DIR/scripts"

# 2. Download skill files
curl -fsSL "$BASE_URL/SKILL.md" -o "$SKILL_DIR/SKILL.md"
echo "  ✓ SKILL.md"

curl -fsSL "$BASE_URL/scripts/xpost.py" -o "$SKILL_DIR/scripts/xpost.py"
chmod +x "$SKILL_DIR/scripts/xpost.py"
echo "  ✓ scripts/xpost.py"

# 3. Install Python dependencies (if not already present)
if python3 -c "import requests_oauthlib" 2>/dev/null; then
  echo "  ✓ requests-oauthlib already installed"
else
  echo "  → Installing requests-oauthlib..."
  pip3 install --quiet requests requests-oauthlib
  echo "  ✓ requests-oauthlib installed"
fi

echo ""
echo "⚙️  Ensure these env vars are set (in OpenClaw config env.vars or shell):"
echo "   X_CONSUMER_KEY, X_CONSUMER_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET"
echo ""
echo "✅ Installed to $SKILL_DIR"
echo "   Usage: python3 $SKILL_DIR/scripts/xpost.py --help"
