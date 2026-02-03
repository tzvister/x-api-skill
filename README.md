# xpost 🐦‍⬛

X/Twitter CLI for AI agents. Post, read, search, and engage on X using the official v2 API with OAuth 1.0a.

Built as an [OpenClaw](https://openclaw.ai) / [AgentSkills](https://agentskills.io) skill — install it and your agent learns X/Twitter automatically.

## Why xpost?

- **Proper OAuth 1.0a** — no cookie scraping, no browser sessions
- **Full X API v2** — tweet, reply, search, threads, likes, retweets, follows
- **Single script** — one Python file, minimal dependencies
- **Agent-native** — JSON output, skill metadata, install script

Replaces [`bird`](https://github.com/steipete/bird) for agents that need reliable, authenticated X access.

## Quick Install

```bash
curl -fsSL https://syn-ack.ai/skills/xpost/install.sh | bash
```

This installs to `~/.openclaw/skills/xpost/` and ensures Python dependencies are available.

## Manual Install

```bash
mkdir -p ~/.openclaw/skills/xpost/scripts
curl -fsSL https://syn-ack.ai/skills/xpost/SKILL.md -o ~/.openclaw/skills/xpost/SKILL.md
curl -fsSL https://syn-ack.ai/skills/xpost/scripts/xpost.py -o ~/.openclaw/skills/xpost/scripts/xpost.py
pip install requests requests-oauthlib
```

## Requirements

- Python 3.10+
- `requests` + `requests-oauthlib`
- X API credentials ([developer.x.com](https://developer.x.com/en/portal/dashboard))

Set these environment variables (or add to OpenClaw `env.vars`):

```bash
export X_CONSUMER_KEY="..."
export X_CONSUMER_SECRET="..."
export X_ACCESS_TOKEN="..."
export X_ACCESS_TOKEN_SECRET="..."
```

## Commands

```bash
xpost=~/.openclaw/skills/xpost/scripts/xpost.py

# Post & reply
python3 $xpost tweet "Hello world"
python3 $xpost reply <tweet_id> "Your reply"
python3 $xpost delete <tweet_id>

# Read
python3 $xpost get <tweet_id>
python3 $xpost thread <tweet_id>
python3 $xpost search "query" -n 20
python3 $xpost mentions -n 10
python3 $xpost timeline -n 10

# Engage
python3 $xpost like <tweet_id>
python3 $xpost unlike <tweet_id>
python3 $xpost retweet <tweet_id>
python3 $xpost unretweet <tweet_id>
python3 $xpost follow <username>

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

## License

MIT

---

*Built by [SynACK](https://syn-ack.ai) 👻*
