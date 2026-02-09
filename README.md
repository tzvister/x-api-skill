<p align="center">
  <img src="assets/banner.png" alt="xpost — X/Twitter CLI for AI agents" width="600">
</p>

<p align="center">
  Post, read, search, and engage on X using the official v2 API with OAuth 1.0a, Bearer Token, and OAuth 2.0 PKCE.
</p>

Extended fork of [syn-ack-ai/xpost](https://github.com/syn-ack-ai/xpost) — adds Bearer Token auth, OAuth 2.0 PKCE, 23 new commands, and full X API v2 coverage.

Built as an [AgentSkills](https://agentskills.io) skill — works with [OpenClaw](https://openclaw.ai), [Claude Code](https://docs.anthropic.com/en/docs/agents-and-tools/claude-code/overview), [Codex](https://openai.com/index/introducing-codex/), [Copilot](https://github.com/features/copilot), or any skills-compatible agent.

## Why xpost?

- **Proper OAuth 1.0a** — no cookie scraping, no browser sessions
- **Full X API v2** — tweet, reply, search, threads, likes, retweets, follows, DMs
- **Social graph** — followers, following, liked tweets, liking users, retweeters
- **Mute, block, bookmarks, lists** — full moderation, bookmark folders, and list management
- **Streaming & full-archive** — filtered stream, volume stream, and historical search (Pro)
- **Trends & Spaces** — location-based trends and Spaces search/lookup
- **Single script** — one Python file, minimal dependencies
- **Agent-native** — JSON output, skill metadata, install script

Replaces [`bird`](https://github.com/steipete/bird) for agents that need reliable, authenticated X access.

## Quick Install

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/tzvister/xpost/master/install.sh)
```

The installer asks which platform you use (OpenClaw, Claude Code, Codex, Copilot, or a custom path), downloads the skill files, installs Python dependencies, and walks you through API key setup.

### Non-interactive install (for agents / CI)

```bash
export X_CONSUMER_KEY="..." X_CONSUMER_SECRET="..." X_ACCESS_TOKEN="..." X_ACCESS_TOKEN_SECRET="..."
XPOST_SKILL_DIR=~/.claude/skills/xpost bash install.sh --non-interactive
```

Skips all prompts. Reads API keys from environment variables and writes them to `.env`.

## Manual Install

```bash
# Replace <skill-dir> with your platform's skills path, e.g.:
#   OpenClaw:    ~/.openclaw/skills/xpost
#   Claude Code: ~/.claude/skills/xpost
#   Codex:       ~/.codex/skills/xpost
#   Copilot:     ~/.copilot/skills/xpost
mkdir -p <skill-dir>/scripts
curl -fsSL https://raw.githubusercontent.com/tzvister/xpost/master/SKILL.md -o <skill-dir>/SKILL.md
curl -fsSL https://raw.githubusercontent.com/tzvister/xpost/master/scripts/xpost.py -o <skill-dir>/scripts/xpost.py
pip install requests requests-oauthlib python-dotenv
```

## Requirements

- Python 3.10+
- `requests`, `requests-oauthlib`, `python-dotenv`
- X API credentials ([developer.x.com](https://developer.x.com/en/portal/dashboard))

## Authentication

xpost supports three authentication methods, each covering different API features:

### OAuth 1.0a (required — core functionality)

Set these environment variables (or add to OpenClaw `env.vars`):

```bash
export X_CONSUMER_KEY="..."
export X_CONSUMER_SECRET="..."
export X_ACCESS_TOKEN="..."
export X_ACCESS_TOKEN_SECRET="..."
```

Covers: tweet, reply, delete, like, unlike, retweet, follow/unfollow, mute, block, search, timelines, user lookup, followers, following, liked tweets, DMs, lists, hide replies.

### Bearer Token (optional — streams & full-archive search)

```bash
export X_BEARER_TOKEN="..."
```

Required for:
- Filtered stream (`stream-filter`)
- Volume stream (`stream-sample`)
- Full-archive search (`search-all`)

> **Note:** These endpoints require **Pro access** ($5,000/month). They will return a 403 error on Free/Basic tiers.

### OAuth 2.0 PKCE (optional — bookmarks)

```bash
export X_CLIENT_ID="..."
export X_CLIENT_SECRET="..."   # optional, for confidential clients
```

Then run the one-time authorization flow:

```bash
python3 scripts/xpost.py auth
```

This opens your browser for authorization and stores tokens in `~/.xpost/tokens.json`. Tokens auto-refresh when expired.

Required for: `bookmarks`, `bookmark`, `unbookmark`, `bookmark-folders`, `bookmarks-folder`.

## Commands

```bash
# Use your platform's install path (shown at the end of install.sh)
xpost=<skill-dir>/scripts/xpost.py

# Post & reply
python3 $xpost tweet "Hello world"
python3 $xpost reply <tweet_id> "Your reply"
python3 $xpost delete <tweet_id>

# Read
python3 $xpost get <tweet_id>
python3 $xpost thread <tweet_id>
python3 $xpost thread-chain <tweet_id>
python3 $xpost quotes <tweet_id>
python3 $xpost search "query" -n 20
python3 $xpost mentions -n 10
python3 $xpost timeline -n 10

# Research
python3 $xpost user <username>
python3 $xpost user-timeline <username> -n 10
python3 $xpost user-timeline <username> --include-rts
python3 $xpost followers <username> -n 100
python3 $xpost following <username> -n 100
python3 $xpost liked <username> -n 20
python3 $xpost liking-users <tweet_id>
python3 $xpost retweeters <tweet_id>

# Engage
python3 $xpost like <tweet_id>
python3 $xpost unlike <tweet_id>
python3 $xpost retweet <tweet_id>
python3 $xpost unretweet <tweet_id>
python3 $xpost follow <username>
python3 $xpost unfollow <username>

# Hide / Unhide replies
python3 $xpost hide <tweet_id>
python3 $xpost unhide <tweet_id>

# Moderate
python3 $xpost mute <username>
python3 $xpost unmute <username>
python3 $xpost block <username>
python3 $xpost unblock <username>

# Direct Messages
python3 $xpost dm <username> "Hello!"
python3 $xpost dm-list -n 20
python3 $xpost dm-conversation <conversation_id> -n 20

# Bookmarks (run 'auth' first)
python3 $xpost auth
python3 $xpost bookmarks -n 20
python3 $xpost bookmark <tweet_id>
python3 $xpost unbookmark <tweet_id>
python3 $xpost bookmark-folders
python3 $xpost bookmarks-folder <folder_id> -n 20

# Lists
python3 $xpost my-lists
python3 $xpost list <list_id>
python3 $xpost list-create "My List" --description "desc" --private
python3 $xpost list-delete <list_id>
python3 $xpost list-tweets <list_id> -n 20
python3 $xpost list-members <list_id>
python3 $xpost list-add-member <list_id> <username>
python3 $xpost list-remove-member <list_id> <username>

# Trends
python3 $xpost trends --woeid 1

# Spaces
python3 $xpost spaces "music"
python3 $xpost space <space_id>

# Streams (Pro access)
python3 $xpost stream-rules-add "keyword" --tag "label"
python3 $xpost stream-rules-list
python3 $xpost stream-rules-delete <rule_id>
python3 $xpost stream-filter -n 10
python3 $xpost stream-sample -n 10

# Full-archive search (Pro access)
python3 $xpost search-all "query" -n 10

# Account
python3 $xpost verify
python3 $xpost me
python3 $xpost profile "New bio"
```

## Output

All commands return JSON. Tweet objects include `id`, `text`, and `edit_history_tweet_ids`.

```json
{
  "data": {
    "id": "1234567890",
    "text": "Hello world"
  }
}
```

## Notes

- **280 character limit** on tweets — the script enforces this
- Profile update uses the v1.1 API (only endpoint not yet on v2)
- Access tokens inherit permission scope at generation time — regenerate after changing app permissions
- Streams and full-archive search require **Pro access** — will return 403 on lower tiers
- Bookmarks require a one-time `auth` setup (OAuth 2.0 PKCE flow)
- Bearer Token must be set explicitly via `X_BEARER_TOKEN` — get it from https://developer.x.com/en/portal/dashboard

## License

MIT

---

*Inspired by and forked from [syn-ack-ai/xpost](https://github.com/syn-ack-ai/xpost) by [SynACK](https://syn-ack.ai). Extended with Bearer Token, OAuth 2.0 PKCE, and full API v2 coverage by [tzvister](https://github.com/tzvister).*
