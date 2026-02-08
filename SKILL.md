---
name: xpost
description: "X/Twitter CLI for posting, reading, searching, and engagement via API v2. Supports OAuth 1.0a (tweets, likes, follows, DMs, lists, mutes, blocks), Bearer Token (streams, full-archive search, trends, spaces), and OAuth 2.0 PKCE (bookmarks, bookmark folders). Replaces bird (cookie auth) with proper OAuth."
---

# xpost

X/Twitter CLI using API v2 with OAuth 1.0a, Bearer Token, and OAuth 2.0 PKCE authentication.

## Install

```bash
bash <skill-dir>/install.sh
```

Copies `xpost.py` into workspace `scripts/` and installs Python dependencies.

### Required Env Vars (OAuth 1.0a — core functionality)

`X_CONSUMER_KEY`, `X_CONSUMER_SECRET`, `X_ACCESS_TOKEN`, `X_ACCESS_TOKEN_SECRET`

### Optional Env Vars

- `X_BEARER_TOKEN` — for streams and full-archive search (auto-generated from consumer keys if not set)
- `X_CLIENT_ID` — for bookmarks (OAuth 2.0 PKCE, run `auth` command to set up)
- `X_CLIENT_SECRET` — optional, for confidential OAuth 2.0 clients

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
python3 scripts/xpost.py followers <username> -n 100  # List a user's followers
python3 scripts/xpost.py following <username> -n 100  # List who a user follows
python3 scripts/xpost.py liked <username> -n 20       # Tweets liked by a user
python3 scripts/xpost.py liking-users <tweet_id>      # Users who liked a tweet
python3 scripts/xpost.py retweeters <tweet_id>        # Users who retweeted a tweet
```

### Engage

```bash
python3 scripts/xpost.py like <tweet_id>
python3 scripts/xpost.py unlike <tweet_id>
python3 scripts/xpost.py retweet <tweet_id>
python3 scripts/xpost.py unretweet <tweet_id>
python3 scripts/xpost.py follow <username>
python3 scripts/xpost.py unfollow <username>
```

### Hide / Unhide Replies

```bash
python3 scripts/xpost.py hide <tweet_id>              # Hide a reply to your tweet
python3 scripts/xpost.py unhide <tweet_id>            # Unhide a reply
```

### Moderate

```bash
python3 scripts/xpost.py mute <username>              # Mute a user
python3 scripts/xpost.py unmute <username>             # Unmute a user
python3 scripts/xpost.py block <username>              # Block a user
python3 scripts/xpost.py unblock <username>            # Unblock a user
```

### Direct Messages

```bash
python3 scripts/xpost.py dm <username> "Hello!"       # Send a DM
python3 scripts/xpost.py dm-list -n 20                # List recent DM events
python3 scripts/xpost.py dm-conversation <convo_id>   # DMs in a conversation
```

### Bookmarks (requires OAuth 2.0 PKCE — run `auth` first)

```bash
python3 scripts/xpost.py auth                         # One-time PKCE setup (opens browser)
python3 scripts/xpost.py bookmarks -n 20              # List your bookmarks
python3 scripts/xpost.py bookmark <tweet_id>          # Bookmark a tweet
python3 scripts/xpost.py unbookmark <tweet_id>        # Remove a bookmark
python3 scripts/xpost.py bookmark-folders             # List bookmark folders
python3 scripts/xpost.py bookmarks-folder <folder_id> # Bookmarks in a folder
```

### Lists

```bash
python3 scripts/xpost.py my-lists                     # List your owned lists
python3 scripts/xpost.py list <list_id>               # Look up a list
python3 scripts/xpost.py list-create "name" --description "desc" --private
python3 scripts/xpost.py list-delete <list_id>        # Delete a list
python3 scripts/xpost.py list-tweets <list_id> -n 20  # Tweets from a list
python3 scripts/xpost.py list-members <list_id>       # List members
python3 scripts/xpost.py list-add-member <list_id> <username>
python3 scripts/xpost.py list-remove-member <list_id> <username>
```

### Trends

```bash
python3 scripts/xpost.py trends --woeid 1             # Worldwide trends (WOEID 1)
```

### Spaces

```bash
python3 scripts/xpost.py spaces "music"               # Search for Spaces
python3 scripts/xpost.py space <space_id>             # Look up a Space
```

### Streams (requires Pro access — $5,000/month)

```bash
python3 scripts/xpost.py stream-rules-add "keyword"   # Add a filtered stream rule
python3 scripts/xpost.py stream-rules-add "from:user" --tag "tracking"
python3 scripts/xpost.py stream-rules-list            # List current rules
python3 scripts/xpost.py stream-rules-delete <rule_id> # Delete a rule
python3 scripts/xpost.py stream-filter -n 10          # Collect tweets from filtered stream
python3 scripts/xpost.py stream-sample -n 10          # Collect tweets from 1% volume stream
```

### Search (Full Archive — requires Pro access)

```bash
python3 scripts/xpost.py search-all "query" -n 10     # Search all historical tweets
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
- Streams and full-archive search require **Pro access** ($5,000/month) — will return 403 on lower tiers
- Bookmarks require a one-time `auth` setup (OAuth 2.0 PKCE flow, opens browser)
- Bearer Token is auto-generated from consumer keys if `X_BEARER_TOKEN` is not set
