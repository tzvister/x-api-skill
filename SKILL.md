---
name: xpost
description: "Complete X/Twitter CLI for AI agents — 58 commands covering the full API v2. Post, read, search, engage, moderate, DM, manage lists, bookmarks, trends, spaces, and streams. All output is JSON. Supports OAuth 1.0a, Bearer Token, and OAuth 2.0 PKCE."
---

# xpost

X/Twitter CLI with complete API v2 coverage. Every command outputs structured JSON to stdout. Errors go to stderr with a non-zero exit code.

**Script location:** `<skill-dir>/scripts/xpost.py`
**Invocation:** `python3 <skill-dir>/scripts/xpost.py <command> [args]`

## Setup

```bash
bash <skill-dir>/install.sh
```

### Required Environment Variables

| Variable | Purpose |
|----------|---------|
| `X_CONSUMER_KEY` | OAuth 1.0a consumer key |
| `X_CONSUMER_SECRET` | OAuth 1.0a consumer secret |
| `X_ACCESS_TOKEN` | OAuth 1.0a access token |
| `X_ACCESS_TOKEN_SECRET` | OAuth 1.0a access token secret |

### Optional Environment Variables

| Variable | Purpose |
|----------|---------|
| `X_BEARER_TOKEN` | Bearer token for streams, trends, spaces — get from https://developer.x.com/en/portal/dashboard |
| `X_CLIENT_ID` | OAuth 2.0 client ID for bookmarks — run `auth` first |
| `X_CLIENT_SECRET` | OAuth 2.0 client secret (only for confidential clients) |

### Auth Tiers

| Auth Method | Commands it unlocks |
|-------------|-------------------|
| **OAuth 1.0a** (required) | All core commands: tweet, read, search, engage, follow, moderate, DMs, lists, hide replies |
| **Bearer Token** (optional) | `stream-*`, `search-all`, `trends`, `spaces`, `space` |
| **OAuth 2.0 PKCE** (optional) | `bookmarks`, `bookmark`, `unbookmark`, `bookmark-folders`, `bookmarks-folder` |

---

## Command Reference (58 commands)

### 1. Post, Reply & Delete

#### `tweet` — Post a new tweet

```bash
python3 scripts/xpost.py tweet "Your tweet text here"
```

- **text** (required): Tweet content, max 280 characters. Fails if over limit.
- **Returns:** `{"data": {"id": "1234567890", "text": "Your tweet text here", ...}}`
- **Use when:** You need to publish a message to X.

#### `reply` — Reply to a tweet

```bash
python3 scripts/xpost.py reply 1234567890 "Your reply text"
```

- **tweet_id** (required): ID of the tweet to reply to.
- **text** (required): Reply text, max 280 characters.
- **Returns:** Same as `tweet` — a new tweet object with `id`.
- **Use when:** Responding to someone's tweet in a thread.

#### `delete` — Delete a tweet you posted

```bash
python3 scripts/xpost.py delete 1234567890
```

- **tweet_id** (required): ID of your tweet to delete.
- **Returns:** `{"data": {"deleted": true}}`
- **Use when:** Removing a tweet you've posted. Only works on your own tweets.

---

### 2. Read Tweets

#### `get` — Fetch a single tweet by ID

```bash
python3 scripts/xpost.py get 1234567890
```

- **tweet_id** (required): The tweet ID to fetch.
- **Returns:** Tweet object with `id`, `text`, `created_at`, `author_id`, `public_metrics`.
- **Use when:** You have a tweet ID and need its content or metadata.

#### `thread` — Get all replies in a conversation

```bash
python3 scripts/xpost.py thread 1234567890 -n 20
```

- **tweet_id** (required): Any tweet ID in the conversation.
- **-n** (optional, default 20): Max number of replies to fetch.
- **Returns:** Multiple tweet objects, one per JSON block.
- **Use when:** You want to read all replies to a tweet.

#### `thread-chain` — Walk an author's full thread (chronological)

```bash
python3 scripts/xpost.py thread-chain 1234567890 -n 20
```

- **tweet_id** (required): Any tweet ID in the thread.
- **-n** (optional, default 20): Max results.
- **Returns:** The author's own tweets in the thread, in chronological order.
- **Use when:** Someone posted a long thread and you want to read it top-to-bottom.

#### `quotes` — Get quote tweets of a tweet

```bash
python3 scripts/xpost.py quotes 1234567890 -n 10
```

- **tweet_id** (required): The original tweet ID.
- **-n** (optional, default 10): Max results.
- **Returns:** Tweet objects that quote the given tweet.
- **Use when:** You want to see how people are commenting on/sharing a tweet.

#### `search` — Search recent tweets (last 7 days)

```bash
python3 scripts/xpost.py search "AI agents" -n 10
```

- **query** (required): Search query. Supports X search operators (`from:user`, `#hashtag`, `-filter:retweets`, etc.).
- **-n** (optional, default 10): Max results (5-100).
- **Returns:** Tweet objects with author info merged in.
- **Use when:** Finding recent tweets about a topic. Only covers the last 7 days.

#### `mentions` — Get your mentions

```bash
python3 scripts/xpost.py mentions -n 10
```

- **-n** (optional, default 10): Max results.
- **Returns:** Tweets that mention the authenticated user.
- **Use when:** Checking who is talking to you.

#### `timeline` — Get your home timeline

```bash
python3 scripts/xpost.py timeline -n 10
```

- **-n** (optional, default 10): Max results.
- **Returns:** Tweets from your home timeline (people you follow).
- **Use when:** Seeing what's in your feed.

---

### 3. Research Users & Social Graph

#### `user` — Look up a user's profile

```bash
python3 scripts/xpost.py user NASA
```

- **username** (required): Username with or without `@`.
- **Returns:** `{"id", "username", "name", "description", "location", "public_metrics": {"followers_count", "following_count", "tweet_count"}, "verified", "url", "created_at"}`
- **Use when:** You need info about a specific account — bio, follower count, location, etc.

#### `user-timeline` — Get a user's recent tweets

```bash
python3 scripts/xpost.py user-timeline NASA -n 10
python3 scripts/xpost.py user-timeline NASA -n 10 --include-rts
```

- **username** (required): Username with or without `@`.
- **-n** (optional, default 10): Max results (min 5).
- **--include-rts** (optional): Include retweets (excluded by default).
- **Returns:** Tweet objects with `author.username` added.
- **Use when:** Reading what a specific user has been posting.

#### `followers` — List a user's followers

```bash
python3 scripts/xpost.py followers openai -n 100
```

- **username** (required): Username with or without `@`.
- **-n** (optional, default 100): Max results (up to 1000).
- **Returns:** User objects with `username`, `name`, `public_metrics`, `description`, `verified`.
- **Use when:** Analyzing who follows an account, finding an audience.

#### `following` — List who a user follows

```bash
python3 scripts/xpost.py following openai -n 100
```

- **username** (required): Username with or without `@`.
- **-n** (optional, default 100): Max results (up to 1000).
- **Returns:** Same user objects as `followers`.
- **Use when:** Seeing who an account follows, discovering related accounts.

#### `liked` — List tweets liked by a user

```bash
python3 scripts/xpost.py liked ycombinator -n 20
```

- **username** (required): Username with or without `@`.
- **-n** (optional, default 20): Max results (5-100).
- **Returns:** Tweet objects that the user has liked, with author info.
- **Use when:** Understanding what content a user finds interesting.

#### `liking-users` — List users who liked a specific tweet

```bash
python3 scripts/xpost.py liking-users 1234567890
```

- **tweet_id** (required): The tweet ID.
- **Returns:** User objects of people who liked the tweet.
- **Use when:** Seeing who engaged with a particular tweet.

#### `retweeters` — List users who retweeted a specific tweet

```bash
python3 scripts/xpost.py retweeters 1234567890
```

- **tweet_id** (required): The tweet ID.
- **Returns:** User objects of people who retweeted.
- **Use when:** Seeing who shared a tweet.

---

### 4. Engage (Like, Retweet, Follow)

#### `like` / `unlike` — Like or unlike a tweet

```bash
python3 scripts/xpost.py like 1234567890
python3 scripts/xpost.py unlike 1234567890
```

- **tweet_id** (required): The tweet to like/unlike.
- **Returns:** `{"data": {"liked": true/false}}`

#### `retweet` / `unretweet` — Retweet or undo a retweet

```bash
python3 scripts/xpost.py retweet 1234567890
python3 scripts/xpost.py unretweet 1234567890
```

- **tweet_id** (required): The tweet to retweet/unretweet.
- **Returns:** `{"data": {"retweeted": true/false}}`

#### `follow` / `unfollow` — Follow or unfollow a user

```bash
python3 scripts/xpost.py follow NASA
python3 scripts/xpost.py unfollow NASA
```

- **username** (required): Username with or without `@`.
- **Returns:** `{"data": {"following": true/false, "pending_follow": false}}`
- **Note:** If the account is private, the response may show `"pending_follow": true`.

---

### 5. Hide / Unhide Replies

#### `hide` / `unhide` — Hide or unhide a reply to your tweet

```bash
python3 scripts/xpost.py hide 1234567890
python3 scripts/xpost.py unhide 1234567890
```

- **tweet_id** (required): The reply tweet ID to hide/unhide. Must be a reply to one of your tweets.
- **Returns:** `{"data": {"hidden": true/false}}`
- **Use when:** Moderating replies under your tweets — hidden replies are collapsed but still accessible via "View hidden replies".

---

### 6. Moderate (Mute & Block)

#### `mute` / `unmute` — Mute or unmute a user

```bash
python3 scripts/xpost.py mute spammer123
python3 scripts/xpost.py unmute spammer123
```

- **username** (required): Username with or without `@`.
- **Returns:** `{"data": {"muting": true/false}}`
- **Use when:** You want to stop seeing someone's tweets in your timeline without unfollowing or blocking.

#### `block` / `unblock` — Block or unblock a user

```bash
python3 scripts/xpost.py block spammer123
python3 scripts/xpost.py unblock spammer123
```

- **username** (required): Username with or without `@`.
- **Returns:** `{"data": {"blocking": true/false}}`
- **Use when:** You want to prevent all interaction with a user. They cannot see your tweets or interact with you.

---

### 7. Direct Messages

#### `dm` — Send a direct message

```bash
python3 scripts/xpost.py dm johndoe "Hey, let's connect!"
```

- **username** (required): Recipient username with or without `@`.
- **text** (required): Message content.
- **Returns:** DM event object with `dm_event_id`, `dm_conversation_id`.
- **Use when:** Sending a private message to another user.

#### `dm-list` — List recent DM events

```bash
python3 scripts/xpost.py dm-list -n 20
```

- **-n** (optional, default 20): Max results (1-100).
- **Returns:** DM event objects with `id`, `text`, `event_type`, `created_at`, `sender_id`, `dm_conversation_id`.
- **Use when:** Checking your recent DMs across all conversations.

#### `dm-conversation` — List DMs in a specific conversation

```bash
python3 scripts/xpost.py dm-conversation 12345-67890 -n 20
```

- **conversation_id** (required): The DM conversation ID (from `dm-list` output).
- **-n** (optional, default 20): Max results (1-100).
- **Returns:** DM event objects for that conversation.
- **Use when:** Reading the message history of a specific DM thread.

---

### 8. Account & Auth

#### `verify` — Test that authentication works

```bash
python3 scripts/xpost.py verify
```

- **Returns:** Confirmation message with your username if auth is valid.
- **Use when:** First-time setup or troubleshooting — always verify before running other commands.

#### `me` — Get your own profile info

```bash
python3 scripts/xpost.py me
```

- **Returns:** Your user object with `id`, `username`, `name`, `description`, `public_metrics`.
- **Use when:** You need your own user ID, follower count, or profile details.

#### `profile` — Update your bio

```bash
python3 scripts/xpost.py profile "Building AI tools for everyone"
```

- **text** (required): New bio text.
- **Returns:** Confirmation message.
- **Note:** Uses the v1.1 API (only endpoint not yet available on v2).
- **Use when:** Updating the authenticated user's bio/description.

#### `auth` — One-time OAuth 2.0 PKCE authorization

```bash
python3 scripts/xpost.py auth
```

- **Requires:** `X_CLIENT_ID` env var set. Opens a browser for authorization.
- **Stores:** Tokens in `~/.xpost/tokens.json`. Auto-refreshes when expired.
- **Run once** before using any bookmark commands. Not scriptable — requires interactive browser.

---

### 9. Bookmarks (requires `auth` setup)

#### `bookmarks` — List your bookmarked tweets

```bash
python3 scripts/xpost.py bookmarks -n 20
```

- **-n** (optional, default 20): Max results.
- **Returns:** Tweet objects you've bookmarked.
- **Use when:** Retrieving saved tweets.

#### `bookmark` / `unbookmark` — Add or remove a bookmark

```bash
python3 scripts/xpost.py bookmark 1234567890
python3 scripts/xpost.py unbookmark 1234567890
```

- **tweet_id** (required): Tweet to bookmark/unbookmark.
- **Returns:** `{"data": {"bookmarked": true/false}}`

#### `bookmark-folders` — List your bookmark folders

```bash
python3 scripts/xpost.py bookmark-folders
```

- **Returns:** Folder objects with folder IDs and names.
- **Use when:** Seeing how your bookmarks are organized.

#### `bookmarks-folder` — List bookmarks in a specific folder

```bash
python3 scripts/xpost.py bookmarks-folder FOLDER_ID -n 20
```

- **folder_id** (required): Folder ID from `bookmark-folders` output.
- **-n** (optional, default 20): Max results.
- **Returns:** Tweet objects bookmarked in that folder.

---

### 10. Lists

#### `my-lists` — List your owned lists

```bash
python3 scripts/xpost.py my-lists
```

- **Returns:** List objects with `id`, `name`, `description`, `member_count`, `follower_count`, `private`, `created_at`.
- **Use when:** Seeing what lists you've created.

#### `list` — Look up a list by ID

```bash
python3 scripts/xpost.py list 1234567890
```

- **list_id** (required): The list ID.
- **Returns:** List object with metadata.

#### `list-create` — Create a new list

```bash
python3 scripts/xpost.py list-create "AI News" --description "Top AI accounts" --private
```

- **name** (required): List name.
- **--description** (optional): List description.
- **--private** (optional flag): Make the list private (default is public).
- **Returns:** `{"data": {"id": "1234567890", "name": "AI News"}}`
- **Use when:** Organizing accounts into curated feeds.

#### `list-delete` — Delete a list you own

```bash
python3 scripts/xpost.py list-delete 1234567890
```

- **list_id** (required): List ID to delete.
- **Returns:** `{"data": {"deleted": true}}`

#### `list-tweets` — Get tweets from a list's timeline

```bash
python3 scripts/xpost.py list-tweets 1234567890 -n 20
```

- **list_id** (required): The list ID.
- **-n** (optional, default 20): Max results (1-100).
- **Returns:** Tweet objects from the list's members.
- **Use when:** Reading a curated feed from a list.

#### `list-members` — List members of a list

```bash
python3 scripts/xpost.py list-members 1234567890
```

- **list_id** (required): The list ID.
- **Returns:** User objects for each member.

#### `list-add-member` / `list-remove-member` — Add or remove a list member

```bash
python3 scripts/xpost.py list-add-member 1234567890 NASA
python3 scripts/xpost.py list-remove-member 1234567890 NASA
```

- **list_id** (required): The list ID.
- **username** (required): Username to add/remove (with or without `@`).
- **Returns:** `{"data": {"is_member": true/false}}`

---

### 11. Trends

#### `trends` — Get trending topics for a location

```bash
python3 scripts/xpost.py trends --woeid 1
```

- **--woeid** (optional, default 1): Where On Earth ID. Common values:
  - `1` = Worldwide
  - `23424977` = United States
  - `23424975` = United Kingdom
  - `23424856` = Japan
- **Returns:** Trend objects with trend name/query.
- **Requires:** Bearer Token.
- **Use when:** Seeing what's trending globally or in a specific country.

---

### 12. Spaces

#### `spaces` — Search for X Spaces

```bash
python3 scripts/xpost.py spaces "AI startups"
```

- **query** (required): Search query.
- **Returns:** Space objects with `id`, `title`, `host_ids`, `state` (live/scheduled), `participant_count`, `lang`.
- **Requires:** Bearer Token.
- **Use when:** Finding live or upcoming audio conversations on a topic.

#### `space` — Look up a Space by ID

```bash
python3 scripts/xpost.py space 1AbCdEfGh
```

- **space_id** (required): The Space ID (from `spaces` output).
- **Returns:** Space object with full details.
- **Requires:** Bearer Token.

---

### 13. Streams (requires Pro access — $5,000/month)

These commands connect to real-time tweet streams. They will return 403 on Free/Basic tiers.

#### `stream-rules-add` — Add a filtered stream rule

```bash
python3 scripts/xpost.py stream-rules-add "AI OR machine learning" --tag "ai-tracking"
```

- **rule** (required): Filter rule using X stream operators.
- **--tag** (optional): Label for the rule.
- **Returns:** Rule object with `id` and `value`.

#### `stream-rules-list` — List current stream rules

```bash
python3 scripts/xpost.py stream-rules-list
```

- **Returns:** Array of rule objects.

#### `stream-rules-delete` — Delete a stream rule

```bash
python3 scripts/xpost.py stream-rules-delete RULE_ID
```

- **rule_id** (required): Rule ID from `stream-rules-list`.
- **Returns:** Deletion confirmation.

#### `stream-filter` — Connect to filtered stream

```bash
python3 scripts/xpost.py stream-filter -n 10
```

- **-n** (optional, default 10): Number of tweets to collect before disconnecting.
- **Returns:** Tweet objects as they arrive in real-time. Blocks until enough tweets are collected or timeout.
- **Use when:** Monitoring specific keywords/accounts in real-time.

#### `stream-sample` — Connect to 1% volume stream

```bash
python3 scripts/xpost.py stream-sample -n 10
```

- **-n** (optional, default 10): Number of tweets to collect.
- **Returns:** A random 1% sample of all tweets globally.
- **Use when:** Sampling the global conversation for analysis.

---

### 14. Full-Archive Search (requires Pro access)

#### `search-all` — Search all historical tweets

```bash
python3 scripts/xpost.py search-all "from:NASA moon landing" -n 10
```

- **query** (required): Same syntax as `search`, but covers ALL historical tweets.
- **-n** (optional, default 10): Max results.
- **Returns:** Tweet objects with author info.
- **Use when:** You need tweets older than 7 days. `search` only covers the last 7 days; `search-all` covers the entire archive.

---

## Common Workflows

### Monitor a topic and engage

```bash
# 1. Search for recent discussion
python3 scripts/xpost.py search "your topic" -n 20

# 2. Find interesting users from results
python3 scripts/xpost.py user interesting_user

# 3. Follow them
python3 scripts/xpost.py follow interesting_user

# 4. Like a good tweet
python3 scripts/xpost.py like TWEET_ID

# 5. Reply to start a conversation
python3 scripts/xpost.py reply TWEET_ID "Great insight!"
```

### Post a thread (multi-tweet)

```bash
# 1. Post the first tweet
python3 scripts/xpost.py tweet "1/3 Here's my take on..."
# Returns: {"data": {"id": "111..."}}

# 2. Reply to it to continue the thread
python3 scripts/xpost.py reply 111 "2/3 Furthermore..."
# Returns: {"data": {"id": "222..."}}

# 3. Continue replying to each new tweet
python3 scripts/xpost.py reply 222 "3/3 In conclusion..."
```

### Curate a list

```bash
# 1. Create a list
python3 scripts/xpost.py list-create "AI Researchers" --description "Top AI accounts"

# 2. Add members (use the list ID from step 1)
python3 scripts/xpost.py list-add-member LIST_ID ylecun
python3 scripts/xpost.py list-add-member LIST_ID kaboreka

# 3. Read the list's feed
python3 scripts/xpost.py list-tweets LIST_ID -n 20
```

### Analyze engagement on a tweet

```bash
# 1. Get the tweet
python3 scripts/xpost.py get TWEET_ID

# 2. See who liked it
python3 scripts/xpost.py liking-users TWEET_ID

# 3. See who retweeted it
python3 scripts/xpost.py retweeters TWEET_ID

# 4. See quote tweets
python3 scripts/xpost.py quotes TWEET_ID
```

### Research a user

```bash
# 1. Profile info
python3 scripts/xpost.py user elonmusk

# 2. Recent tweets
python3 scripts/xpost.py user-timeline elonmusk -n 10

# 3. Who follows them
python3 scripts/xpost.py followers elonmusk -n 100

# 4. Who they follow
python3 scripts/xpost.py following elonmusk -n 100

# 5. What they like
python3 scripts/xpost.py liked elonmusk -n 20
```

---

## Output Format

All commands output JSON to stdout. Errors go to stderr with a non-zero exit code.

**Single object commands** (tweet, get, user, like, follow, etc.):
```json
{"data": {"id": "1234567890", "text": "Hello world"}}
```

**Multi-object commands** (search, timeline, followers, etc.) print one JSON object per item:
```json
{"id": "111", "text": "First tweet", ...}
{"id": "222", "text": "Second tweet", ...}
```

Parse stdout as one or more JSON objects. Use a streaming JSON parser or split on top-level `{...}` blocks.

## Error Handling

- **Non-zero exit code** + stderr message = command failed
- **403 Forbidden** = tier limitation (e.g., Pro-only endpoint on Free tier) or permission issue
- **404 Not Found** = invalid ID or the resource doesn't exist
- **409 Conflict** = duplicate action (e.g., already following, already liked)
- **429 Too Many Requests** = rate limited — wait and retry

## Important Notes

- **280 character limit** — always check length before calling `tweet` or `reply`
- **Usernames** — all commands accept usernames with or without the `@` prefix
- **Rate limits** — X API enforces rate limits per endpoint. Space out bulk operations.
- **Profile update** uses the v1.1 API (the only endpoint not yet on v2)
- **Access tokens** inherit permission scope at generation time — if you change app permissions in the X Developer Portal, regenerate your access tokens
- **Streams and full-archive search** require Pro access ($5,000/month) — will return 403 on Free/Basic tiers
- **Bookmarks** require a one-time interactive `auth` setup (OAuth 2.0 PKCE flow, opens browser)
- **Bearer Token** must be set explicitly via `X_BEARER_TOKEN` — get it from https://developer.x.com/en/portal/dashboard
