---
name: xpost
description: "X/Twitter CLI for posting, reading, searching, and engagement via OAuth 1.0a API v2. Use for tweeting, replying, searching tweets, reading mentions/timelines, liking, retweeting, following, and managing tweets. Replaces bird (cookie auth) with proper OAuth."
---

# xpost 🐦‍⬛

X/Twitter CLI using API v2 with OAuth 1.0a authentication.

## Install

```bash
bash <skill-dir>/install.sh
```

Copies `xpost.py` into workspace `scripts/` and installs Python dependencies.

Requires env vars: `X_CONSUMER_KEY`, `X_CONSUMER_SECRET`, `X_ACCESS_TOKEN`, `X_ACCESS_TOKEN_SECRET`

## Commands

All commands: `python3 <skill-dir>/scripts/xpost.py <command> [args]`

### Post & Reply

```bash
python3 scripts/xpost.py tweet "Hello world"        # 280 char limit
python3 scripts/xpost.py reply <tweet_id> "Reply"
python3 scripts/xpost.py delete <tweet_id>
```

### Read

```bash
python3 scripts/xpost.py get <tweet_id>              # Single tweet
python3 scripts/xpost.py thread <tweet_id>            # Conversation replies
python3 scripts/xpost.py thread-chain <tweet_id>      # Author's full thread (chronological)
python3 scripts/xpost.py quotes <tweet_id>            # Quote tweets of a tweet
python3 scripts/xpost.py search "query" -n 20         # Recent tweets (default 10)
python3 scripts/xpost.py mentions -n 10               # Your mentions
python3 scripts/xpost.py timeline -n 10               # Home timeline
```

### Research

```bash
python3 scripts/xpost.py user <username>              # Profile lookup (bio, metrics)
python3 scripts/xpost.py user-timeline <user> -n 10   # Someone's recent tweets
python3 scripts/xpost.py user-timeline <user> --include-rts  # Include retweets
```

### Engage

```bash
python3 scripts/xpost.py like <tweet_id>
python3 scripts/xpost.py unlike <tweet_id>
python3 scripts/xpost.py retweet <tweet_id>
python3 scripts/xpost.py unretweet <tweet_id>
python3 scripts/xpost.py follow <username>
```

### Account

```bash
python3 scripts/xpost.py verify                       # Test auth
python3 scripts/xpost.py me                           # Your profile
python3 scripts/xpost.py profile "New bio"            # Update bio
```

## Output

JSON objects with `id`, `text`, `edit_history_tweet_ids`. Search/mentions return arrays.

## Notes

- **280 char limit** — always check length before posting
- Replaces `bird` (cookie auth, unreliable) — use xpost for all X operations
