#!/usr/bin/env python3
"""
X/Twitter CLI using raw X API v2 with OAuth 1.0a, Bearer Token, and OAuth 2.0 PKCE.

Supports three authentication methods:
  - OAuth 1.0a: User context for tweets, likes, follows, mutes, blocks
  - Bearer Token: App-only for streams and full-archive search (Pro access)
  - OAuth 2.0 PKCE: User context for bookmarks

Usage:
  python3 scripts/xpost.py tweet "Hello world"
  python3 scripts/xpost.py reply <tweet-id> "Reply text"
  python3 scripts/xpost.py get <tweet-id>
  python3 scripts/xpost.py thread <tweet-id> [-n 20]
  python3 scripts/xpost.py like <tweet-id>
  python3 scripts/xpost.py unlike <tweet-id>
  python3 scripts/xpost.py follow <username>
  python3 scripts/xpost.py mute <username>
  python3 scripts/xpost.py unmute <username>
  python3 scripts/xpost.py block <username>
  python3 scripts/xpost.py unblock <username>
  python3 scripts/xpost.py search "query" [-n 10]
  python3 scripts/xpost.py search-all "query" [-n 10]       (Pro access)
  python3 scripts/xpost.py mentions [-n 10]
  python3 scripts/xpost.py timeline [-n 10]
  python3 scripts/xpost.py user <username>
  python3 scripts/xpost.py user-timeline <username> [-n 10] [--include-rts]
  python3 scripts/xpost.py thread-chain <tweet-id> [-n 20]
  python3 scripts/xpost.py quotes <tweet-id> [-n 10]
  python3 scripts/xpost.py auth                              (OAuth 2.0 PKCE setup)
  python3 scripts/xpost.py bookmarks [-n 20]
  python3 scripts/xpost.py bookmark <tweet-id>
  python3 scripts/xpost.py unbookmark <tweet-id>
  python3 scripts/xpost.py stream-rules-add "rule" [--tag TAG]
  python3 scripts/xpost.py stream-rules-list
  python3 scripts/xpost.py stream-rules-delete <rule-id>
  python3 scripts/xpost.py stream-filter [-n 10]             (Pro access)
  python3 scripts/xpost.py stream-sample [-n 10]             (Pro access)
  python3 scripts/xpost.py profile "new bio text"
  python3 scripts/xpost.py delete <tweet-id>
  python3 scripts/xpost.py verify
  python3 scripts/xpost.py me

Requires: pip install requests requests-oauthlib
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Load .env from the skill directory (parent of scripts/)
try:
    from dotenv import load_dotenv
    _env_file = Path(__file__).resolve().parent.parent / ".env"
    if _env_file.exists():
        load_dotenv(_env_file, override=True)
except ImportError:
    pass

API_BASE = "https://api.x.com/2"
TOKEN_FILE = os.path.expanduser("~/.xpost/tokens.json")


# ── Authentication: OAuth 1.0a ──


def _get_creds():
    """Load X API credentials from env or config file."""
    ck = os.environ.get("X_CONSUMER_KEY", "")
    cs = os.environ.get("X_CONSUMER_SECRET", "")
    at = os.environ.get("X_ACCESS_TOKEN", "")
    ats = os.environ.get("X_ACCESS_TOKEN_SECRET", "")

    if not all([ck, cs, at, ats]):
        try:
            with open(os.path.expanduser("~/.openclaw/openclaw.json")) as f:
                cfg = json.load(f)
            ev = cfg.get("env", {}).get("vars", {})
            ck = ck or ev.get("X_CONSUMER_KEY", "")
            cs = cs or ev.get("X_CONSUMER_SECRET", "")
            at = at or ev.get("X_ACCESS_TOKEN", "")
            ats = ats or ev.get("X_ACCESS_TOKEN_SECRET", "")
        except FileNotFoundError:
            pass

    if not all([ck, cs, at, ats]):
        print("Error: Missing X API credentials", file=sys.stderr)
        sys.exit(1)

    return ck, cs, at, ats


def get_oauth1():
    """Get requests_oauthlib OAuth1 handler for raw API calls."""
    from requests_oauthlib import OAuth1
    ck, cs, at, ats = _get_creds()
    return OAuth1(ck, cs, at, ats)


def get_client():
    """Get XDK Client for read operations (search, mentions, timeline, etc.)."""
    from xdk import Client
    from xdk.oauth1_auth import OAuth1
    ck, cs, at, ats = _get_creds()
    auth = OAuth1(
        api_key=ck,
        api_secret=cs,
        callback="https://www.google.com",
        access_token=at,
        access_token_secret=ats,
    )
    return Client(auth=auth)


# ── Authentication: Bearer Token (app-only) ──


def _get_bearer_token():
    """Get Bearer Token for app-only endpoints (streams, trends, spaces, full-archive search).

    Checks X_BEARER_TOKEN env var first, then the OpenClaw config file.
    """
    # 1. Check env var
    token = os.environ.get("X_BEARER_TOKEN", "")

    # 2. Check config file
    if not token:
        try:
            with open(os.path.expanduser("~/.openclaw/openclaw.json")) as f:
                cfg = json.load(f)
            token = cfg.get("env", {}).get("vars", {}).get("X_BEARER_TOKEN", "")
        except FileNotFoundError:
            pass

    if not token:
        print("Error: Missing X_BEARER_TOKEN. Get it from https://developer.x.com/en/portal/dashboard", file=sys.stderr)
        sys.exit(1)

    return token


def _bearer_headers():
    """Get Authorization headers for Bearer Token endpoints."""
    return {"Authorization": f"Bearer {_get_bearer_token()}"}


# ── Authentication: OAuth 2.0 PKCE ──


def _load_pkce_tokens():
    """Load stored OAuth 2.0 PKCE tokens from disk."""
    try:
        with open(TOKEN_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _save_pkce_tokens(tokens):
    """Save OAuth 2.0 PKCE tokens to disk."""
    os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
    with open(TOKEN_FILE, "w") as f:
        json.dump(tokens, f, indent=2)


def _get_client_id():
    """Get OAuth 2.0 Client ID from env or config."""
    client_id = os.environ.get("X_CLIENT_ID", "")
    if not client_id:
        try:
            with open(os.path.expanduser("~/.openclaw/openclaw.json")) as f:
                cfg = json.load(f)
            client_id = cfg.get("env", {}).get("vars", {}).get("X_CLIENT_ID", "")
        except FileNotFoundError:
            pass
    if not client_id:
        print("Error: Missing X_CLIENT_ID. Required for OAuth 2.0 PKCE (bookmarks).", file=sys.stderr)
        sys.exit(1)
    return client_id


def _get_client_secret():
    """Get OAuth 2.0 Client Secret from env or config (optional for public clients)."""
    secret = os.environ.get("X_CLIENT_SECRET", "")
    if not secret:
        try:
            with open(os.path.expanduser("~/.openclaw/openclaw.json")) as f:
                cfg = json.load(f)
            secret = cfg.get("env", {}).get("vars", {}).get("X_CLIENT_SECRET", "")
        except FileNotFoundError:
            pass
    return secret


def _refresh_pkce_token(refresh_token):
    """Refresh an expired OAuth 2.0 PKCE access token."""
    import requests
    import time

    client_id = _get_client_id()
    client_secret = _get_client_secret()

    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": client_id,
    }

    auth = None
    if client_secret:
        auth = (client_id, client_secret)

    resp = requests.post("https://api.x.com/2/oauth2/token", data=data, auth=auth)
    if not resp.ok:
        print(f"Error refreshing token: {resp.status_code} {resp.text}", file=sys.stderr)
        print("Run 'xpost auth' to re-authorize.", file=sys.stderr)
        sys.exit(1)

    result = resp.json()
    tokens = {
        "access_token": result["access_token"],
        "refresh_token": result.get("refresh_token", refresh_token),
        "expires_at": int(time.time()) + result.get("expires_in", 7200),
    }
    _save_pkce_tokens(tokens)
    return tokens["access_token"]


def _get_oauth2_pkce_token():
    """Get a valid OAuth 2.0 PKCE access token, refreshing if expired."""
    import time

    tokens = _load_pkce_tokens()
    if not tokens:
        print("Error: No OAuth 2.0 tokens found. Run 'xpost auth' first.", file=sys.stderr)
        sys.exit(1)

    # Check expiry (refresh 60s before actual expiry)
    if time.time() >= tokens.get("expires_at", 0) - 60:
        refresh = tokens.get("refresh_token")
        if not refresh:
            print("Error: No refresh token. Run 'xpost auth' to re-authorize.", file=sys.stderr)
            sys.exit(1)
        return _refresh_pkce_token(refresh)

    return tokens["access_token"]


def _oauth2_headers():
    """Get Authorization headers for OAuth 2.0 PKCE endpoints."""
    return {"Authorization": f"Bearer {_get_oauth2_pkce_token()}"}


# ── Common Helpers ──


def _get_my_user_id():
    """Get the authenticated user's ID via OAuth 1.0a. Cached per process."""
    if not hasattr(_get_my_user_id, "_cached"):
        import requests
        auth = get_oauth1()
        resp = requests.get(f"{API_BASE}/users/me", auth=auth)
        if not resp.ok:
            print(f"Error getting user: {resp.status_code} {resp.text}", file=sys.stderr)
            sys.exit(1)
        _get_my_user_id._cached = resp.json()["data"]["id"]
    return _get_my_user_id._cached


def _resolve_username(username):
    """Resolve a @username to a user ID."""
    import requests
    auth = get_oauth1()
    target = username.lstrip("@")
    resp = requests.get(f"{API_BASE}/users/by/username/{target}", auth=auth)
    if not resp.ok:
        print(f"Error resolving @{target}: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    return resp.json()["data"]["id"]


def _get_my_id(client):
    """Get user ID from XDK client (legacy helper for XDK-based commands)."""
    me = client.users.get_me()
    if hasattr(me, 'data') and isinstance(me.data, dict):
        return me.data['id']
    me_str = str(me)
    import re
    match = re.search(r"id='?(\d+)", me_str)
    if not match:
        print("Could not get user ID", file=sys.stderr)
        sys.exit(1)
    return match.group(1)


def _post_tweet(payload: dict) -> dict:
    """Post a tweet using raw requests + OAuth1 (bypasses broken XDK models)."""
    import requests
    auth = get_oauth1()
    resp = requests.post(f"{API_BASE}/tweets", json=payload, auth=auth)
    if not resp.ok:
        print(f"Error: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    return resp.json()


def _delete_tweet(tweet_id: str) -> dict:
    """Delete a tweet using raw requests + OAuth1."""
    import requests
    auth = get_oauth1()
    resp = requests.delete(f"{API_BASE}/tweets/{tweet_id}", auth=auth)
    if not resp.ok:
        print(f"Error: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    return resp.json()


def _merge_authors(data):
    """Merge author info from includes into tweet objects for convenience."""
    users = {}
    if "includes" in data and "users" in data["includes"]:
        users = {u["id"]: u for u in data["includes"]["users"]}
    for tweet in (data.get("data") or []):
        author = users.get(tweet.get("author_id", ""), {})
        tweet["author"] = {"username": author.get("username"), "name": author.get("name")}
    return users


# ── Commands: Post & Reply ──


def cmd_tweet(args):
    text = args.text
    if len(text) > 280:
        print(f"Error: Tweet is {len(text)} chars (max 280)", file=sys.stderr)
        sys.exit(1)

    result = _post_tweet({"text": text})
    print(json.dumps(result, indent=2, default=str))


def cmd_reply(args):
    text = args.text
    if len(text) > 280:
        print(f"Error: Reply is {len(text)} chars (max 280)", file=sys.stderr)
        sys.exit(1)

    result = _post_tweet({
        "text": text,
        "reply": {"in_reply_to_tweet_id": args.tweet_id},
    })
    print(json.dumps(result, indent=2, default=str))


def cmd_delete(args):
    result = _delete_tweet(args.tweet_id)
    print(json.dumps(result, indent=2, default=str))


# ── Commands: Read ──


def cmd_get(args):
    """Fetch a single tweet by ID with author info."""
    import requests
    auth = get_oauth1()
    params = {
        "tweet.fields": "created_at,author_id,conversation_id,in_reply_to_user_id,text,public_metrics",
        "expansions": "author_id",
        "user.fields": "username,name",
    }
    resp = requests.get(f"{API_BASE}/tweets/{args.tweet_id}", params=params, auth=auth)
    if not resp.ok:
        print(f"Error: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    data = resp.json()
    # Merge author info into tweet for convenience
    if "includes" in data and "users" in data["includes"]:
        users = {u["id"]: u for u in data["includes"]["users"]}
        tweet = data.get("data", {})
        author = users.get(tweet.get("author_id", ""), {})
        tweet["author"] = {"username": author.get("username"), "name": author.get("name")}
    print(json.dumps(data.get("data", data), indent=2, default=str))


def cmd_thread(args):
    """Fetch a conversation thread by tweet ID."""
    import requests
    auth = get_oauth1()
    # First get the tweet to find conversation_id
    resp = requests.get(
        f"{API_BASE}/tweets/{args.tweet_id}",
        params={"tweet.fields": "conversation_id"},
        auth=auth,
    )
    if not resp.ok:
        print(f"Error fetching tweet: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    tweet_data = resp.json().get("data", {})
    convo_id = tweet_data.get("conversation_id", args.tweet_id)

    # Search for all tweets in the conversation
    n = max(args.n, 10)
    params = {
        "query": f"conversation_id:{convo_id}",
        "tweet.fields": "created_at,author_id,in_reply_to_user_id,text,public_metrics",
        "expansions": "author_id",
        "user.fields": "username,name",
        "max_results": n,
    }
    resp = requests.get(f"{API_BASE}/tweets/search/recent", params=params, auth=auth)
    if not resp.ok:
        print(f"Error searching thread: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    data = resp.json()
    _merge_authors(data)
    for tweet in (data.get("data") or []):
        print(json.dumps(tweet, indent=2, default=str))


def cmd_thread_chain(args):
    """Walk an author's full thread chain starting from a tweet.
    Follows the conversation_id and filters to only the original author's tweets,
    ordered chronologically."""
    import requests
    auth = get_oauth1()
    # Get the starting tweet
    resp = requests.get(
        f"{API_BASE}/tweets/{args.tweet_id}",
        params={
            "tweet.fields": "conversation_id,author_id,created_at,text,public_metrics",
            "expansions": "author_id",
            "user.fields": "username,name",
        },
        auth=auth,
    )
    if not resp.ok:
        print(f"Error fetching tweet: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    result = resp.json()
    tweet_data = result.get("data", {})
    convo_id = tweet_data.get("conversation_id", args.tweet_id)
    author_id = tweet_data.get("author_id", "")
    # Resolve author username
    users = {}
    if "includes" in result and "users" in result["includes"]:
        users = {u["id"]: u for u in result["includes"]["users"]}
    author_username = users.get(author_id, {}).get("username", "unknown")

    # Search for all tweets in conversation by same author
    n = max(args.n, 10)
    params = {
        "query": f"conversation_id:{convo_id} from:{author_username}",
        "tweet.fields": "created_at,author_id,in_reply_to_user_id,text,public_metrics",
        "max_results": n,
        "sort_order": "recency",
    }
    resp = requests.get(f"{API_BASE}/tweets/search/recent", params=params, auth=auth)
    if not resp.ok:
        print(f"Error searching thread: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    data = resp.json()
    tweets = data.get("data") or []

    # Add the root tweet if it's not in results (it's the conversation starter)
    root_ids = {t["id"] for t in tweets}
    if convo_id not in root_ids:
        tweets.append(tweet_data)

    # Sort chronologically
    tweets.sort(key=lambda t: t.get("created_at", ""))

    for tweet in tweets:
        tweet["author"] = {"username": author_username}
        print(json.dumps(tweet, indent=2, default=str))

    if not tweets:
        print(f"No thread found for conversation {convo_id}.", file=sys.stderr)


def cmd_quotes(args):
    """Fetch quote tweets of a specific tweet."""
    import requests
    auth = get_oauth1()
    n = max(args.n, 10)
    params = {
        "max_results": n,
        "tweet.fields": "created_at,author_id,text,public_metrics",
        "expansions": "author_id",
        "user.fields": "username,name",
    }
    resp = requests.get(f"{API_BASE}/tweets/{args.tweet_id}/quote_tweets", params=params, auth=auth)
    if not resp.ok:
        print(f"Error: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    data = resp.json()
    _merge_authors(data)
    for tweet in (data.get("data") or []):
        print(json.dumps(tweet, indent=2, default=str))
    if not data.get("data"):
        print("No quote tweets found.", file=sys.stderr)


def cmd_search(args):
    """Search recent tweets (last 7 days)."""
    import requests
    auth = get_oauth1()
    n = max(args.n, 10)  # API minimum is 10
    params = {
        "query": args.query,
        "max_results": min(n, 100),
        "tweet.fields": "created_at,author_id,conversation_id,text,public_metrics",
        "expansions": "author_id",
        "user.fields": "username,name",
    }
    resp = requests.get(f"{API_BASE}/tweets/search/recent", params=params, auth=auth)
    if not resp.ok:
        print(f"Error: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    data = resp.json()
    _merge_authors(data)
    for tweet in (data.get("data") or []):
        print(json.dumps(tweet, indent=2, default=str))
    if not data.get("data"):
        print("No results found.", file=sys.stderr)


def cmd_mentions(args):
    """Get your recent mentions."""
    import requests
    auth = get_oauth1()
    user_id = _get_my_user_id()
    n = max(args.n, 5)
    params = {
        "max_results": min(n, 100),
        "tweet.fields": "created_at,author_id,conversation_id,text,public_metrics",
        "expansions": "author_id",
        "user.fields": "username,name",
    }
    resp = requests.get(f"{API_BASE}/users/{user_id}/mentions", params=params, auth=auth)
    if not resp.ok:
        print(f"Error: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    data = resp.json()
    _merge_authors(data)
    for tweet in (data.get("data") or []):
        print(json.dumps(tweet, indent=2, default=str))
    if not data.get("data"):
        print("No mentions found.", file=sys.stderr)


def cmd_timeline(args):
    """Get your home timeline."""
    import requests
    auth = get_oauth1()
    user_id = _get_my_user_id()
    n = max(args.n, 5)
    params = {
        "max_results": min(n, 100),
        "tweet.fields": "created_at,author_id,conversation_id,text,public_metrics",
        "expansions": "author_id",
        "user.fields": "username,name",
    }
    resp = requests.get(f"{API_BASE}/users/{user_id}/timelines/reverse_chronological", params=params, auth=auth)
    if not resp.ok:
        print(f"Error: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    data = resp.json()
    _merge_authors(data)
    for tweet in (data.get("data") or []):
        print(json.dumps(tweet, indent=2, default=str))
    if not data.get("data"):
        print("No timeline tweets found.", file=sys.stderr)


# ── Commands: Research ──


def cmd_user(args):
    """Look up a user's profile by username."""
    import requests
    auth = get_oauth1()
    target = args.username.lstrip("@")
    params = {
        "user.fields": "created_at,description,location,public_metrics,verified,url,pinned_tweet_id",
    }
    resp = requests.get(f"{API_BASE}/users/by/username/{target}", params=params, auth=auth)
    if not resp.ok:
        print(f"Error: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    data = resp.json().get("data", resp.json())
    print(json.dumps(data, indent=2, default=str))


def cmd_user_timeline(args):
    """Fetch recent tweets from a specific user."""
    import requests
    auth = get_oauth1()
    target = args.username.lstrip("@")
    user_id = _resolve_username(target)
    # Fetch their tweets
    n = max(args.n, 5)
    params = {
        "max_results": n,
        "tweet.fields": "created_at,author_id,conversation_id,in_reply_to_user_id,text,public_metrics",
        "exclude": "retweets" if not args.include_rts else "",
    }
    if not params["exclude"]:
        del params["exclude"]
    resp = requests.get(f"{API_BASE}/users/{user_id}/tweets", params=params, auth=auth)
    if not resp.ok:
        print(f"Error: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    data = resp.json()
    for tweet in (data.get("data") or []):
        tweet["author"] = {"username": target}
        print(json.dumps(tweet, indent=2, default=str))
    if not data.get("data"):
        print(f"No tweets found for @{target}.", file=sys.stderr)


# ── Commands: Research (social graph) ──


def cmd_followers(args):
    """List followers of a user."""
    import requests
    auth = get_oauth1()
    target = args.username.lstrip("@")
    user_id = _resolve_username(target)
    n = min(max(args.n, 1), 1000)
    params = {
        "max_results": n,
        "user.fields": "username,name,public_metrics,description,verified",
    }
    resp = requests.get(f"{API_BASE}/users/{user_id}/followers", params=params, auth=auth)
    if not resp.ok:
        print(f"Error: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    data = resp.json()
    for user in (data.get("data") or []):
        print(json.dumps(user, indent=2, default=str))
    if not data.get("data"):
        print(f"No followers found for @{target}.", file=sys.stderr)


def cmd_following(args):
    """List users that a user is following."""
    import requests
    auth = get_oauth1()
    target = args.username.lstrip("@")
    user_id = _resolve_username(target)
    n = min(max(args.n, 1), 1000)
    params = {
        "max_results": n,
        "user.fields": "username,name,public_metrics,description,verified",
    }
    resp = requests.get(f"{API_BASE}/users/{user_id}/following", params=params, auth=auth)
    if not resp.ok:
        print(f"Error: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    data = resp.json()
    for user in (data.get("data") or []):
        print(json.dumps(user, indent=2, default=str))
    if not data.get("data"):
        print(f"@{target} is not following anyone.", file=sys.stderr)


def cmd_liked(args):
    """List tweets liked by a user."""
    import requests
    auth = get_oauth1()
    target = args.username.lstrip("@")
    user_id = _resolve_username(target)
    n = min(max(args.n, 5), 100)
    params = {
        "max_results": n,
        "tweet.fields": "created_at,author_id,text,public_metrics",
        "expansions": "author_id",
        "user.fields": "username,name",
    }
    resp = requests.get(f"{API_BASE}/users/{user_id}/liked_tweets", params=params, auth=auth)
    if not resp.ok:
        print(f"Error: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    data = resp.json()
    _merge_authors(data)
    for tweet in (data.get("data") or []):
        print(json.dumps(tweet, indent=2, default=str))
    if not data.get("data"):
        print(f"No liked tweets found for @{target}.", file=sys.stderr)


def cmd_liking_users(args):
    """List users who liked a tweet."""
    import requests
    auth = get_oauth1()
    params = {
        "user.fields": "username,name,public_metrics,verified",
    }
    resp = requests.get(f"{API_BASE}/tweets/{args.tweet_id}/liking_users", params=params, auth=auth)
    if not resp.ok:
        print(f"Error: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    data = resp.json()
    for user in (data.get("data") or []):
        print(json.dumps(user, indent=2, default=str))
    if not data.get("data"):
        print("No liking users found.", file=sys.stderr)


def cmd_retweeters(args):
    """List users who retweeted a tweet."""
    import requests
    auth = get_oauth1()
    params = {
        "user.fields": "username,name,public_metrics,verified",
    }
    resp = requests.get(f"{API_BASE}/tweets/{args.tweet_id}/retweeted_by", params=params, auth=auth)
    if not resp.ok:
        print(f"Error: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    data = resp.json()
    for user in (data.get("data") or []):
        print(json.dumps(user, indent=2, default=str))
    if not data.get("data"):
        print("No retweeters found.", file=sys.stderr)


# ── Commands: Engage ──


def cmd_like(args):
    """Like a tweet."""
    import requests
    auth = get_oauth1()
    user_id = _get_my_user_id()
    resp = requests.post(
        f"{API_BASE}/users/{user_id}/likes",
        json={"tweet_id": args.tweet_id},
        auth=auth,
    )
    if not resp.ok:
        print(f"Error: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(resp.json(), indent=2, default=str))


def cmd_unlike(args):
    """Unlike a tweet."""
    import requests
    auth = get_oauth1()
    user_id = _get_my_user_id()
    resp = requests.delete(f"{API_BASE}/users/{user_id}/likes/{args.tweet_id}", auth=auth)
    if not resp.ok:
        print(f"Error: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(resp.json(), indent=2, default=str))


def cmd_follow(args):
    """Follow a user by username."""
    import requests
    auth = get_oauth1()
    user_id = _get_my_user_id()
    target_id = _resolve_username(args.username)
    resp = requests.post(
        f"{API_BASE}/users/{user_id}/following",
        json={"target_user_id": target_id},
        auth=auth,
    )
    if not resp.ok:
        print(f"Error: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(resp.json(), indent=2, default=str))


def cmd_unfollow(args):
    """Unfollow a user by username."""
    import requests
    auth = get_oauth1()
    user_id = _get_my_user_id()
    target_id = _resolve_username(args.username)
    resp = requests.delete(f"{API_BASE}/users/{user_id}/following/{target_id}", auth=auth)
    if not resp.ok:
        print(f"Error: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(resp.json(), indent=2, default=str))


def cmd_retweet(args):
    """Retweet a tweet."""
    import requests
    auth = get_oauth1()
    user_id = _get_my_user_id()
    resp = requests.post(
        f"{API_BASE}/users/{user_id}/retweets",
        json={"tweet_id": args.tweet_id},
        auth=auth,
    )
    if not resp.ok:
        print(f"Error: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(resp.json(), indent=2, default=str))


def cmd_unretweet(args):
    """Undo a retweet."""
    import requests
    auth = get_oauth1()
    user_id = _get_my_user_id()
    resp = requests.delete(f"{API_BASE}/users/{user_id}/retweets/{args.tweet_id}", auth=auth)
    if not resp.ok:
        print(f"Error: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(resp.json(), indent=2, default=str))


# ── Commands: Moderate (mute/block) ──


def cmd_mute(args):
    """Mute a user by username."""
    import requests
    auth = get_oauth1()
    user_id = _get_my_user_id()
    target_id = _resolve_username(args.username)
    resp = requests.post(
        f"{API_BASE}/users/{user_id}/muting",
        json={"target_user_id": target_id},
        auth=auth,
    )
    if not resp.ok:
        print(f"Error: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(resp.json(), indent=2, default=str))


def cmd_unmute(args):
    """Unmute a user by username."""
    import requests
    auth = get_oauth1()
    user_id = _get_my_user_id()
    target_id = _resolve_username(args.username)
    resp = requests.delete(f"{API_BASE}/users/{user_id}/muting/{target_id}", auth=auth)
    if not resp.ok:
        print(f"Error: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(resp.json(), indent=2, default=str))


def cmd_block(args):
    """Block a user by username."""
    import requests
    auth = get_oauth1()
    user_id = _get_my_user_id()
    target_id = _resolve_username(args.username)
    resp = requests.post(
        f"{API_BASE}/users/{user_id}/blocking",
        json={"target_user_id": target_id},
        auth=auth,
    )
    if not resp.ok:
        print(f"Error: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(resp.json(), indent=2, default=str))


def cmd_unblock(args):
    """Unblock a user by username."""
    import requests
    auth = get_oauth1()
    user_id = _get_my_user_id()
    target_id = _resolve_username(args.username)
    resp = requests.delete(f"{API_BASE}/users/{user_id}/blocking/{target_id}", auth=auth)
    if not resp.ok:
        print(f"Error: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(resp.json(), indent=2, default=str))


# ── Commands: Hide Replies ──


def cmd_hide(args):
    """Hide a reply to one of your tweets."""
    import requests
    auth = get_oauth1()
    resp = requests.put(
        f"{API_BASE}/tweets/{args.tweet_id}/hidden",
        json={"hidden": True},
        auth=auth,
    )
    if not resp.ok:
        print(f"Error: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(resp.json(), indent=2, default=str))


def cmd_unhide(args):
    """Unhide a reply to one of your tweets."""
    import requests
    auth = get_oauth1()
    resp = requests.put(
        f"{API_BASE}/tweets/{args.tweet_id}/hidden",
        json={"hidden": False},
        auth=auth,
    )
    if not resp.ok:
        print(f"Error: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(resp.json(), indent=2, default=str))


# ── Commands: Direct Messages ──


def cmd_dm(args):
    """Send a direct message to a user."""
    import requests
    auth = get_oauth1()
    target_id = _resolve_username(args.username)
    payload = {"text": args.text}
    resp = requests.post(
        f"{API_BASE}/dm_conversations/with/{target_id}/messages",
        json=payload,
        auth=auth,
    )
    if not resp.ok:
        print(f"Error: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(resp.json(), indent=2, default=str))


def cmd_dm_list(args):
    """List recent DM events."""
    import requests
    auth = get_oauth1()
    n = min(max(args.n, 1), 100)
    params = {
        "max_results": n,
        "dm_event.fields": "id,text,event_type,created_at,sender_id,dm_conversation_id,attachments",
    }
    resp = requests.get(f"{API_BASE}/dm_events", params=params, auth=auth)
    if not resp.ok:
        print(f"Error: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    data = resp.json()
    for event in (data.get("data") or []):
        print(json.dumps(event, indent=2, default=str))
    if not data.get("data"):
        print("No DM events found.", file=sys.stderr)


def cmd_dm_conversation(args):
    """List DM events in a specific conversation."""
    import requests
    auth = get_oauth1()
    n = min(max(args.n, 1), 100)
    params = {
        "max_results": n,
        "dm_event.fields": "id,text,event_type,created_at,sender_id,dm_conversation_id,attachments",
    }
    resp = requests.get(
        f"{API_BASE}/dm_conversations/{args.conversation_id}/dm_events",
        params=params, auth=auth,
    )
    if not resp.ok:
        print(f"Error: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    data = resp.json()
    for event in (data.get("data") or []):
        print(json.dumps(event, indent=2, default=str))
    if not data.get("data"):
        print("No DM events found in this conversation.", file=sys.stderr)


# ── Commands: Account ──


def cmd_verify(args):
    """Verify OAuth 1.0a credentials work."""
    import requests
    auth = get_oauth1()
    resp = requests.get(f"{API_BASE}/users/me", auth=auth)
    if not resp.ok:
        print(f"Error: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    data = resp.json().get("data", {})
    print(f"Authenticated as: @{data.get('username')} ({data.get('name')})")


def cmd_me(args):
    """Get your own profile info."""
    import requests
    auth = get_oauth1()
    params = {
        "user.fields": "id,username,name,description,location,url,created_at,public_metrics,verified",
    }
    resp = requests.get(f"{API_BASE}/users/me", params=params, auth=auth)
    if not resp.ok:
        print(f"Error: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(resp.json().get("data", {}), indent=2, default=str))


def cmd_profile(args):
    """Update profile bio — uses v1.1 API (XDK doesn't cover this)."""
    import hashlib
    import hmac
    import base64
    import time
    import urllib.parse
    import urllib.request

    ck, cs, at, ats = _get_creds()

    url = "https://api.twitter.com/1.1/account/update_profile.json"
    params = {"description": args.text}

    oauth = {
        "oauth_consumer_key": ck,
        "oauth_nonce": hashlib.md5(str(time.time()).encode()).hexdigest(),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_token": at,
        "oauth_version": "1.0",
    }
    all_params = {**oauth, **params}
    sorted_params = "&".join(
        f'{urllib.parse.quote(k, safe="")}'
        f'={urllib.parse.quote(str(v), safe="")}'
        for k, v in sorted(all_params.items())
    )
    base_string = f'POST&{urllib.parse.quote(url, safe="")}&{urllib.parse.quote(sorted_params, safe="")}'
    signing_key = f'{urllib.parse.quote(cs, safe="")}&{urllib.parse.quote(ats, safe="")}'
    sig = base64.b64encode(
        hmac.new(signing_key.encode(), base_string.encode(), hashlib.sha1).digest()
    ).decode()
    oauth["oauth_signature"] = sig
    auth_header = "OAuth " + ", ".join(
        f'{k}="{urllib.parse.quote(v, safe="")}"' for k, v in sorted(oauth.items())
    )

    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(
        url, data=data, method="POST",
        headers={"Authorization": auth_header, "Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())
        print(f"Bio updated: {result['description']}")


# ── Commands: OAuth 2.0 PKCE Auth ──


def cmd_auth(args):
    """Run the OAuth 2.0 Authorization Code with PKCE flow interactively."""
    import base64
    import hashlib
    import secrets
    import time
    import webbrowser
    from http.server import HTTPServer, BaseHTTPRequestHandler
    from urllib.parse import urlencode, urlparse, parse_qs
    import requests

    client_id = _get_client_id()
    client_secret = _get_client_secret()

    # Generate PKCE parameters
    code_verifier = secrets.token_urlsafe(96)[:128]
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).rstrip(b"=").decode()
    state = secrets.token_urlsafe(32)

    redirect_uri = "http://127.0.0.1:8017/callback"
    scopes = "bookmark.read bookmark.write tweet.read users.read offline.access"

    auth_url = "https://twitter.com/i/oauth2/authorize?" + urlencode({
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": scopes,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    })

    # Capture the authorization code via local HTTP server
    captured = {}

    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            query = parse_qs(urlparse(self.path).query)
            captured["code"] = query.get("code", [None])[0]
            captured["state"] = query.get("state", [None])[0]
            captured["error"] = query.get("error", [None])[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            if captured.get("code"):
                self.wfile.write(b"<html><body><h2>Authorization successful!</h2>"
                                 b"<p>You can close this tab and return to the terminal.</p>"
                                 b"</body></html>")
            else:
                error = captured.get("error", "unknown")
                self.wfile.write(f"<html><body><h2>Authorization failed: {error}</h2>"
                                 f"</body></html>".encode())

        def log_message(self, format, *log_args):
            pass  # Suppress HTTP server logs

    print("Starting OAuth 2.0 PKCE authorization flow...")
    print(f"Opening browser for authorization...")
    print(f"If the browser doesn't open, visit:\n  {auth_url}\n")

    server = HTTPServer(("127.0.0.1", 8017), CallbackHandler)
    webbrowser.open(auth_url)

    # Wait for the callback (single request)
    server.handle_request()
    server.server_close()

    if captured.get("error"):
        print(f"Authorization failed: {captured['error']}", file=sys.stderr)
        sys.exit(1)

    code = captured.get("code")
    if not code:
        print("Error: No authorization code received.", file=sys.stderr)
        sys.exit(1)

    if captured.get("state") != state:
        print("Error: State mismatch — possible CSRF attack.", file=sys.stderr)
        sys.exit(1)

    # Exchange authorization code for tokens
    token_data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "code_verifier": code_verifier,
        "client_id": client_id,
    }

    token_auth = None
    if client_secret:
        token_auth = (client_id, client_secret)

    resp = requests.post("https://api.x.com/2/oauth2/token", data=token_data, auth=token_auth)
    if not resp.ok:
        print(f"Error exchanging code for token: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)

    result = resp.json()
    tokens = {
        "access_token": result["access_token"],
        "refresh_token": result.get("refresh_token", ""),
        "expires_at": int(time.time()) + result.get("expires_in", 7200),
    }
    _save_pkce_tokens(tokens)

    print(f"Authorization successful! Tokens saved to {TOKEN_FILE}")
    print(f"Token expires in {result.get('expires_in', 7200) // 60} minutes (auto-refreshes).")


# ── Commands: Bookmarks (OAuth 2.0 PKCE) ──


def _enrich_tweets_oauth2(tweets, headers):
    """Fetch full tweet details for tweets that are missing text (e.g. from bookmarks).

    Uses the OAuth 2.0 token to do a batch /2/tweets lookup and merges text,
    author info, and metrics back into the original tweet objects.
    """
    import requests

    if not tweets:
        return tweets

    ids_missing_text = [t["id"] for t in tweets if not t.get("text")]
    if not ids_missing_text:
        return tweets  # all tweets already have text

    # Batch lookup — /2/tweets accepts up to 100 IDs per request
    full_map = {}
    for i in range(0, len(ids_missing_text), 100):
        batch = ids_missing_text[i : i + 100]
        params = {
            "ids": ",".join(batch),
            "tweet.fields": "created_at,author_id,text,public_metrics",
            "expansions": "author_id",
            "user.fields": "username,name",
        }
        resp = requests.get(f"{API_BASE}/tweets", params=params, headers=headers)
        if resp.ok:
            lookup = resp.json()
            _merge_authors(lookup)
            for t in (lookup.get("data") or []):
                full_map[t["id"]] = t

    # Merge fetched details back into original tweets
    for tweet in tweets:
        if tweet["id"] in full_map:
            tweet.update(full_map[tweet["id"]])

    return tweets


def cmd_bookmarks(args):
    """List bookmarked tweets."""
    import requests

    # Get user ID via OAuth 2.0 (use /2/users/me with PKCE token)
    headers = _oauth2_headers()
    me_resp = requests.get(f"{API_BASE}/users/me", headers=headers)
    if not me_resp.ok:
        print(f"Error getting user: {me_resp.status_code} {me_resp.text}", file=sys.stderr)
        sys.exit(1)
    user_id = me_resp.json()["data"]["id"]

    n = max(args.n, 1)
    params = {
        "max_results": min(n, 100),
        "tweet.fields": "created_at,author_id,text,public_metrics",
        "expansions": "author_id",
        "user.fields": "username,name",
    }
    resp = requests.get(f"{API_BASE}/users/{user_id}/bookmarks", params=params, headers=headers)
    if not resp.ok:
        print(f"Error: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    data = resp.json()
    _merge_authors(data)
    tweets = data.get("data") or []
    # Enrich tweets that may be missing text (API sometimes returns only IDs)
    _enrich_tweets_oauth2(tweets, headers)
    for tweet in tweets:
        print(json.dumps(tweet, indent=2, default=str))
    if not tweets:
        print("No bookmarks found.", file=sys.stderr)


def cmd_bookmark(args):
    """Bookmark a tweet."""
    import requests

    headers = _oauth2_headers()
    headers["Content-Type"] = "application/json"
    me_resp = requests.get(f"{API_BASE}/users/me", headers=_oauth2_headers())
    if not me_resp.ok:
        print(f"Error getting user: {me_resp.status_code} {me_resp.text}", file=sys.stderr)
        sys.exit(1)
    user_id = me_resp.json()["data"]["id"]

    resp = requests.post(
        f"{API_BASE}/users/{user_id}/bookmarks",
        json={"tweet_id": args.tweet_id},
        headers=headers,
    )
    if not resp.ok:
        print(f"Error: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(resp.json(), indent=2, default=str))


def cmd_unbookmark(args):
    """Remove a bookmark."""
    import requests

    headers = _oauth2_headers()
    me_resp = requests.get(f"{API_BASE}/users/me", headers=headers)
    if not me_resp.ok:
        print(f"Error getting user: {me_resp.status_code} {me_resp.text}", file=sys.stderr)
        sys.exit(1)
    user_id = me_resp.json()["data"]["id"]

    resp = requests.delete(
        f"{API_BASE}/users/{user_id}/bookmarks/{args.tweet_id}",
        headers=headers,
    )
    if not resp.ok:
        print(f"Error: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(resp.json(), indent=2, default=str))


# ── Commands: Bookmark Folders (OAuth 2.0 PKCE) ──


def cmd_bookmark_folders(args):
    """List bookmark folders."""
    import requests
    headers = _oauth2_headers()
    me_resp = requests.get(f"{API_BASE}/users/me", headers=headers)
    if not me_resp.ok:
        print(f"Error getting user: {me_resp.status_code} {me_resp.text}", file=sys.stderr)
        sys.exit(1)
    user_id = me_resp.json()["data"]["id"]

    resp = requests.get(f"{API_BASE}/users/{user_id}/bookmarks/folders", headers=headers)
    if not resp.ok:
        print(f"Error: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    data = resp.json()
    for folder in (data.get("data") or []):
        print(json.dumps(folder, indent=2, default=str))
    if not data.get("data"):
        print("No bookmark folders found.", file=sys.stderr)


def cmd_bookmarks_folder(args):
    """List bookmarks in a specific folder."""
    import requests
    headers = _oauth2_headers()
    me_resp = requests.get(f"{API_BASE}/users/me", headers=headers)
    if not me_resp.ok:
        print(f"Error getting user: {me_resp.status_code} {me_resp.text}", file=sys.stderr)
        sys.exit(1)
    user_id = me_resp.json()["data"]["id"]

    n = max(args.n, 1)
    params = {
        "max_results": min(n, 100),
        "tweet.fields": "created_at,author_id,text,public_metrics",
        "expansions": "author_id",
        "user.fields": "username,name",
    }
    resp = requests.get(
        f"{API_BASE}/users/{user_id}/bookmarks/folders/{args.folder_id}",
        params=params, headers=headers,
    )
    if not resp.ok:
        print(f"Error: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    data = resp.json()
    _merge_authors(data)
    tweets = data.get("data") or []
    _enrich_tweets_oauth2(tweets, headers)
    for tweet in tweets:
        print(json.dumps(tweet, indent=2, default=str))
    if not tweets:
        print("No bookmarks found in this folder.", file=sys.stderr)


# ── Commands: Filtered Stream (Bearer Token, Pro access) ──


def cmd_stream_rules_add(args):
    """Add a rule to the filtered stream."""
    import requests

    rule = {"value": args.rule}
    if args.tag:
        rule["tag"] = args.tag

    resp = requests.post(
        f"{API_BASE}/tweets/search/stream/rules",
        json={"add": [rule]},
        headers=_bearer_headers(),
    )
    if not resp.ok:
        print(f"Error: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(resp.json(), indent=2, default=str))


def cmd_stream_rules_list(args):
    """List all filtered stream rules."""
    import requests

    resp = requests.get(
        f"{API_BASE}/tweets/search/stream/rules",
        headers=_bearer_headers(),
    )
    if not resp.ok:
        print(f"Error: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    data = resp.json()
    rules = data.get("data") or []
    if not rules:
        print("No stream rules configured.", file=sys.stderr)
    else:
        for rule in rules:
            print(json.dumps(rule, indent=2, default=str))


def cmd_stream_rules_delete(args):
    """Delete a filtered stream rule by ID."""
    import requests

    resp = requests.post(
        f"{API_BASE}/tweets/search/stream/rules",
        json={"delete": {"ids": [args.rule_id]}},
        headers=_bearer_headers(),
    )
    if not resp.ok:
        print(f"Error: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(resp.json(), indent=2, default=str))


def cmd_stream_filter(args):
    """Connect to filtered stream and collect tweets (Pro access required)."""
    import requests

    n = args.n
    params = {
        "tweet.fields": "created_at,author_id,text,public_metrics",
        "expansions": "author_id",
        "user.fields": "username,name",
    }
    resp = requests.get(
        f"{API_BASE}/tweets/search/stream",
        params=params,
        headers=_bearer_headers(),
        stream=True,
    )
    if not resp.ok:
        print(f"Error: {resp.status_code} {resp.text}", file=sys.stderr)
        if resp.status_code == 403:
            print("Hint: Filtered stream requires Pro access ($5,000/month).", file=sys.stderr)
        sys.exit(1)

    count = 0
    try:
        for line in resp.iter_lines():
            if not line:
                continue  # Skip keep-alive newlines
            try:
                tweet_data = json.loads(line)
                print(json.dumps(tweet_data, indent=2, default=str))
                count += 1
                if count >= n:
                    break
            except json.JSONDecodeError:
                continue
    except KeyboardInterrupt:
        pass
    finally:
        resp.close()


# ── Commands: Volume Stream (Bearer Token, Pro access) ──


def cmd_stream_sample(args):
    """Connect to 1% volume stream and collect tweets (Pro access required)."""
    import requests

    n = args.n
    params = {
        "tweet.fields": "created_at,author_id,text,public_metrics",
        "expansions": "author_id",
        "user.fields": "username,name",
    }
    resp = requests.get(
        f"{API_BASE}/tweets/sample/stream",
        params=params,
        headers=_bearer_headers(),
        stream=True,
    )
    if not resp.ok:
        print(f"Error: {resp.status_code} {resp.text}", file=sys.stderr)
        if resp.status_code == 403:
            print("Hint: Volume stream requires Pro access ($5,000/month).", file=sys.stderr)
        sys.exit(1)

    count = 0
    try:
        for line in resp.iter_lines():
            if not line:
                continue  # Skip keep-alive newlines
            try:
                tweet_data = json.loads(line)
                print(json.dumps(tweet_data, indent=2, default=str))
                count += 1
                if count >= n:
                    break
            except json.JSONDecodeError:
                continue
    except KeyboardInterrupt:
        pass
    finally:
        resp.close()


# ── Commands: Full-Archive Search (Bearer Token, Pro access) ──


def cmd_search_all(args):
    """Search the full archive of tweets (Pro access required)."""
    import requests

    n = max(args.n, 10)
    params = {
        "query": args.query,
        "max_results": min(n, 500),
        "tweet.fields": "created_at,author_id,conversation_id,text,public_metrics",
        "expansions": "author_id",
        "user.fields": "username,name",
    }
    resp = requests.get(
        f"{API_BASE}/tweets/search/all",
        params=params,
        headers=_bearer_headers(),
    )
    if not resp.ok:
        print(f"Error: {resp.status_code} {resp.text}", file=sys.stderr)
        if resp.status_code == 403:
            print("Hint: Full-archive search requires Pro access ($5,000/month).", file=sys.stderr)
        sys.exit(1)
    data = resp.json()
    _merge_authors(data)
    for tweet in (data.get("data") or []):
        print(json.dumps(tweet, indent=2, default=str))
    if not data.get("data"):
        print("No results found.", file=sys.stderr)


# ── Commands: Lists ──


def cmd_my_lists(args):
    """List your owned lists."""
    import requests
    auth = get_oauth1()
    user_id = _get_my_user_id()
    params = {"list.fields": "description,member_count,follower_count,created_at,private"}
    resp = requests.get(f"{API_BASE}/users/{user_id}/owned_lists", params=params, auth=auth)
    if not resp.ok:
        print(f"Error: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    data = resp.json()
    for lst in (data.get("data") or []):
        print(json.dumps(lst, indent=2, default=str))
    if not data.get("data"):
        print("No lists found.", file=sys.stderr)


def cmd_list_get(args):
    """Look up a list by ID."""
    import requests
    auth = get_oauth1()
    params = {"list.fields": "description,member_count,follower_count,created_at,private,owner_id"}
    resp = requests.get(f"{API_BASE}/lists/{args.list_id}", params=params, auth=auth)
    if not resp.ok:
        print(f"Error: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    data = resp.json().get("data", resp.json())
    print(json.dumps(data, indent=2, default=str))


def cmd_list_create(args):
    """Create a new list."""
    import requests
    auth = get_oauth1()
    payload = {"name": args.name}
    if args.description:
        payload["description"] = args.description
    if args.private:
        payload["private"] = True
    resp = requests.post(f"{API_BASE}/lists", json=payload, auth=auth)
    if not resp.ok:
        print(f"Error: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(resp.json(), indent=2, default=str))


def cmd_list_delete(args):
    """Delete a list you own."""
    import requests
    auth = get_oauth1()
    resp = requests.delete(f"{API_BASE}/lists/{args.list_id}", auth=auth)
    if not resp.ok:
        print(f"Error: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(resp.json(), indent=2, default=str))


def cmd_list_tweets(args):
    """Fetch tweets from a list."""
    import requests
    auth = get_oauth1()
    n = min(max(args.n, 1), 100)
    params = {
        "max_results": n,
        "tweet.fields": "created_at,author_id,text,public_metrics",
        "expansions": "author_id",
        "user.fields": "username,name",
    }
    resp = requests.get(f"{API_BASE}/lists/{args.list_id}/tweets", params=params, auth=auth)
    if not resp.ok:
        print(f"Error: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    data = resp.json()
    _merge_authors(data)
    for tweet in (data.get("data") or []):
        print(json.dumps(tweet, indent=2, default=str))
    if not data.get("data"):
        print("No tweets found in this list.", file=sys.stderr)


def cmd_list_members(args):
    """List members of a list."""
    import requests
    auth = get_oauth1()
    params = {"user.fields": "username,name,public_metrics,verified"}
    resp = requests.get(f"{API_BASE}/lists/{args.list_id}/members", params=params, auth=auth)
    if not resp.ok:
        print(f"Error: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    data = resp.json()
    for user in (data.get("data") or []):
        print(json.dumps(user, indent=2, default=str))
    if not data.get("data"):
        print("No members found in this list.", file=sys.stderr)


def cmd_list_add_member(args):
    """Add a user to a list."""
    import requests
    auth = get_oauth1()
    target_id = _resolve_username(args.username)
    resp = requests.post(
        f"{API_BASE}/lists/{args.list_id}/members",
        json={"user_id": target_id},
        auth=auth,
    )
    if not resp.ok:
        print(f"Error: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(resp.json(), indent=2, default=str))


def cmd_list_remove_member(args):
    """Remove a user from a list."""
    import requests
    auth = get_oauth1()
    target_id = _resolve_username(args.username)
    resp = requests.delete(f"{API_BASE}/lists/{args.list_id}/members/{target_id}", auth=auth)
    if not resp.ok:
        print(f"Error: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(resp.json(), indent=2, default=str))


# ── Commands: Trends (Bearer Token) ──


def cmd_trends(args):
    """Get personalized or location-based trends."""
    import requests
    headers = _bearer_headers()
    resp = requests.get(f"{API_BASE}/trends/by/woeid/{args.woeid}", headers=headers)
    if not resp.ok:
        print(f"Error: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    data = resp.json()
    for trend in (data.get("data") or []):
        print(json.dumps(trend, indent=2, default=str))
    if not data.get("data"):
        print("No trends found.", file=sys.stderr)


# ── Commands: Spaces (Bearer Token) ──


def cmd_spaces_search(args):
    """Search for Spaces."""
    import requests
    headers = _bearer_headers()
    params = {
        "query": args.query,
        "space.fields": "title,host_ids,created_at,participant_count,state,lang",
    }
    resp = requests.get(f"{API_BASE}/spaces/search", params=params, headers=headers)
    if not resp.ok:
        print(f"Error: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    data = resp.json()
    for space in (data.get("data") or []):
        print(json.dumps(space, indent=2, default=str))
    if not data.get("data"):
        print("No spaces found.", file=sys.stderr)


def cmd_space_get(args):
    """Look up a Space by ID."""
    import requests
    headers = _bearer_headers()
    params = {
        "space.fields": "title,host_ids,created_at,participant_count,state,lang,scheduled_start",
    }
    resp = requests.get(f"{API_BASE}/spaces/{args.space_id}", params=params, headers=headers)
    if not resp.ok:
        print(f"Error: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    data = resp.json().get("data", resp.json())
    print(json.dumps(data, indent=2, default=str))


# ── CLI Entry Point ──


def main():
    parser = argparse.ArgumentParser(description="X/Twitter CLI (v2 API + OAuth1/Bearer/PKCE)")
    sub = parser.add_subparsers(dest="command", required=True)

    # Post & Reply
    p_tweet = sub.add_parser("tweet", help="Post a tweet")
    p_tweet.add_argument("text", help="Tweet text (max 280 chars)")

    p_reply = sub.add_parser("reply", help="Reply to a tweet")
    p_reply.add_argument("tweet_id", help="Tweet ID to reply to")
    p_reply.add_argument("text", help="Reply text (max 280 chars)")

    p_delete = sub.add_parser("delete", help="Delete a tweet")
    p_delete.add_argument("tweet_id", help="Tweet ID to delete")

    # Read
    p_get = sub.add_parser("get", help="Fetch a tweet by ID")
    p_get.add_argument("tweet_id", help="Tweet ID")

    p_thread = sub.add_parser("thread", help="Fetch conversation thread")
    p_thread.add_argument("tweet_id", help="Any tweet ID in the thread")
    p_thread.add_argument("-n", type=int, default=20, help="Max results")

    p_thread_chain = sub.add_parser("thread-chain", help="Walk an author's full thread")
    p_thread_chain.add_argument("tweet_id", help="Any tweet ID in the thread")
    p_thread_chain.add_argument("-n", type=int, default=20, help="Max results")

    p_quotes = sub.add_parser("quotes", help="Get quote tweets of a tweet")
    p_quotes.add_argument("tweet_id", help="Tweet ID")
    p_quotes.add_argument("-n", type=int, default=10, help="Max results")

    p_search = sub.add_parser("search", help="Search recent tweets")
    p_search.add_argument("query", help="Search query")
    p_search.add_argument("-n", type=int, default=10, help="Max results")

    p_mentions = sub.add_parser("mentions", help="Get your mentions")
    p_mentions.add_argument("-n", type=int, default=10, help="Max results")

    p_timeline = sub.add_parser("timeline", help="Get your timeline")
    p_timeline.add_argument("-n", type=int, default=10, help="Max results")

    # Research
    p_user = sub.add_parser("user", help="Look up a user's profile")
    p_user.add_argument("username", help="Username to look up (with or without @)")

    p_user_tl = sub.add_parser("user-timeline", help="Get a user's recent tweets")
    p_user_tl.add_argument("username", help="Username (with or without @)")
    p_user_tl.add_argument("-n", type=int, default=10, help="Max results")
    p_user_tl.add_argument("--include-rts", action="store_true", help="Include retweets")

    p_followers = sub.add_parser("followers", help="List a user's followers")
    p_followers.add_argument("username", help="Username (with or without @)")
    p_followers.add_argument("-n", type=int, default=100, help="Max results (up to 1000)")

    p_following = sub.add_parser("following", help="List who a user follows")
    p_following.add_argument("username", help="Username (with or without @)")
    p_following.add_argument("-n", type=int, default=100, help="Max results (up to 1000)")

    p_liked = sub.add_parser("liked", help="List tweets liked by a user")
    p_liked.add_argument("username", help="Username (with or without @)")
    p_liked.add_argument("-n", type=int, default=20, help="Max results")

    p_liking = sub.add_parser("liking-users", help="List users who liked a tweet")
    p_liking.add_argument("tweet_id", help="Tweet ID")

    p_retweeters = sub.add_parser("retweeters", help="List users who retweeted a tweet")
    p_retweeters.add_argument("tweet_id", help="Tweet ID")

    # Engage
    p_like = sub.add_parser("like", help="Like a tweet")
    p_like.add_argument("tweet_id", help="Tweet ID to like")

    p_unlike = sub.add_parser("unlike", help="Unlike a tweet")
    p_unlike.add_argument("tweet_id", help="Tweet ID to unlike")

    p_follow = sub.add_parser("follow", help="Follow a user")
    p_follow.add_argument("username", help="Username to follow (with or without @)")

    p_unfollow = sub.add_parser("unfollow", help="Unfollow a user")
    p_unfollow.add_argument("username", help="Username to unfollow (with or without @)")

    p_retweet = sub.add_parser("retweet", help="Retweet a tweet")
    p_retweet.add_argument("tweet_id", help="Tweet ID to retweet")

    p_unretweet = sub.add_parser("unretweet", help="Undo a retweet")
    p_unretweet.add_argument("tweet_id", help="Tweet ID to unretweet")

    # Hide replies
    p_hide = sub.add_parser("hide", help="Hide a reply to your tweet")
    p_hide.add_argument("tweet_id", help="Tweet ID to hide")

    p_unhide = sub.add_parser("unhide", help="Unhide a reply to your tweet")
    p_unhide.add_argument("tweet_id", help="Tweet ID to unhide")

    # Moderate
    p_mute = sub.add_parser("mute", help="Mute a user")
    p_mute.add_argument("username", help="Username to mute (with or without @)")

    p_unmute = sub.add_parser("unmute", help="Unmute a user")
    p_unmute.add_argument("username", help="Username to unmute (with or without @)")

    p_block = sub.add_parser("block", help="Block a user")
    p_block.add_argument("username", help="Username to block (with or without @)")

    p_unblock = sub.add_parser("unblock", help="Unblock a user")
    p_unblock.add_argument("username", help="Username to unblock (with or without @)")

    # Direct Messages
    p_dm = sub.add_parser("dm", help="Send a DM to a user")
    p_dm.add_argument("username", help="Username to message (with or without @)")
    p_dm.add_argument("text", help="Message text")

    p_dm_list = sub.add_parser("dm-list", help="List recent DM events")
    p_dm_list.add_argument("-n", type=int, default=20, help="Max results")

    p_dm_convo = sub.add_parser("dm-conversation", help="List DMs in a conversation")
    p_dm_convo.add_argument("conversation_id", help="DM conversation ID")
    p_dm_convo.add_argument("-n", type=int, default=20, help="Max results")

    # Account
    sub.add_parser("verify", help="Verify authentication")
    sub.add_parser("me", help="Get your profile info")

    p_profile = sub.add_parser("profile", help="Update your bio")
    p_profile.add_argument("text", help="New bio text")

    # OAuth 2.0 PKCE
    sub.add_parser("auth", help="Authorize OAuth 2.0 PKCE (required for bookmarks)")

    # Bookmarks (requires OAuth 2.0 PKCE — run 'auth' first)
    p_bookmarks = sub.add_parser("bookmarks", help="List your bookmarks (requires 'auth')")
    p_bookmarks.add_argument("-n", type=int, default=20, help="Max results")

    p_bookmark = sub.add_parser("bookmark", help="Bookmark a tweet (requires 'auth')")
    p_bookmark.add_argument("tweet_id", help="Tweet ID to bookmark")

    p_unbookmark = sub.add_parser("unbookmark", help="Remove a bookmark (requires 'auth')")
    p_unbookmark.add_argument("tweet_id", help="Tweet ID to unbookmark")

    p_bfold = sub.add_parser("bookmark-folders", help="List bookmark folders (requires 'auth')")

    p_bfoldt = sub.add_parser("bookmarks-folder", help="Bookmarks in a folder (requires 'auth')")
    p_bfoldt.add_argument("folder_id", help="Folder ID")
    p_bfoldt.add_argument("-n", type=int, default=20, help="Max results")

    # Filtered Stream (Pro access)
    p_sr_add = sub.add_parser("stream-rules-add", help="Add a filtered stream rule (Pro)")
    p_sr_add.add_argument("rule", help="Stream rule (e.g. 'keyword1 OR keyword2')")
    p_sr_add.add_argument("--tag", default=None, help="Optional label for the rule")

    sub.add_parser("stream-rules-list", help="List filtered stream rules (Pro)")

    p_sr_del = sub.add_parser("stream-rules-delete", help="Delete a stream rule (Pro)")
    p_sr_del.add_argument("rule_id", help="Rule ID to delete")

    p_sf = sub.add_parser("stream-filter", help="Connect to filtered stream (Pro)")
    p_sf.add_argument("-n", type=int, default=10, help="Number of tweets to collect")

    # Volume Stream (Pro access)
    p_ss = sub.add_parser("stream-sample", help="Connect to 1%% volume stream (Pro)")
    p_ss.add_argument("-n", type=int, default=10, help="Number of tweets to collect")

    # Full-Archive Search (Pro access)
    p_sa = sub.add_parser("search-all", help="Full-archive search (Pro)")
    p_sa.add_argument("query", help="Search query")
    p_sa.add_argument("-n", type=int, default=10, help="Max results")

    # Lists
    sub.add_parser("my-lists", help="List your owned lists")

    p_list = sub.add_parser("list", help="Look up a list by ID")
    p_list.add_argument("list_id", help="List ID")

    p_lc = sub.add_parser("list-create", help="Create a new list")
    p_lc.add_argument("name", help="List name")
    p_lc.add_argument("--description", default=None, help="List description")
    p_lc.add_argument("--private", action="store_true", help="Make the list private")

    p_ld = sub.add_parser("list-delete", help="Delete a list")
    p_ld.add_argument("list_id", help="List ID to delete")

    p_lt = sub.add_parser("list-tweets", help="Get tweets from a list")
    p_lt.add_argument("list_id", help="List ID")
    p_lt.add_argument("-n", type=int, default=20, help="Max results")

    p_lm = sub.add_parser("list-members", help="List members of a list")
    p_lm.add_argument("list_id", help="List ID")

    p_la = sub.add_parser("list-add-member", help="Add a user to a list")
    p_la.add_argument("list_id", help="List ID")
    p_la.add_argument("username", help="Username to add (with or without @)")

    p_lr = sub.add_parser("list-remove-member", help="Remove a user from a list")
    p_lr.add_argument("list_id", help="List ID")
    p_lr.add_argument("username", help="Username to remove (with or without @)")

    # Trends
    p_trends = sub.add_parser("trends", help="Get trends for a location (WOEID)")
    p_trends.add_argument("--woeid", type=int, default=1, help="WOEID (default: 1 = worldwide)")

    # Spaces
    p_spaces = sub.add_parser("spaces", help="Search for Spaces")
    p_spaces.add_argument("query", help="Search query")

    p_space = sub.add_parser("space", help="Look up a Space by ID")
    p_space.add_argument("space_id", help="Space ID")

    args = parser.parse_args()

    commands = {
        # Post & Reply
        "tweet": cmd_tweet,
        "reply": cmd_reply,
        "delete": cmd_delete,
        # Read
        "get": cmd_get,
        "thread": cmd_thread,
        "thread-chain": cmd_thread_chain,
        "quotes": cmd_quotes,
        "search": cmd_search,
        "mentions": cmd_mentions,
        "timeline": cmd_timeline,
        # Research
        "user": cmd_user,
        "user-timeline": cmd_user_timeline,
        "followers": cmd_followers,
        "following": cmd_following,
        "liked": cmd_liked,
        "liking-users": cmd_liking_users,
        "retweeters": cmd_retweeters,
        # Engage
        "like": cmd_like,
        "unlike": cmd_unlike,
        "follow": cmd_follow,
        "unfollow": cmd_unfollow,
        "retweet": cmd_retweet,
        "unretweet": cmd_unretweet,
        "hide": cmd_hide,
        "unhide": cmd_unhide,
        # Moderate
        "mute": cmd_mute,
        "unmute": cmd_unmute,
        "block": cmd_block,
        "unblock": cmd_unblock,
        # Direct Messages
        "dm": cmd_dm,
        "dm-list": cmd_dm_list,
        "dm-conversation": cmd_dm_conversation,
        # Account
        "verify": cmd_verify,
        "me": cmd_me,
        "profile": cmd_profile,
        # Auth
        "auth": cmd_auth,
        # Bookmarks
        "bookmarks": cmd_bookmarks,
        "bookmark": cmd_bookmark,
        "unbookmark": cmd_unbookmark,
        "bookmark-folders": cmd_bookmark_folders,
        "bookmarks-folder": cmd_bookmarks_folder,
        # Lists
        "my-lists": cmd_my_lists,
        "list": cmd_list_get,
        "list-create": cmd_list_create,
        "list-delete": cmd_list_delete,
        "list-tweets": cmd_list_tweets,
        "list-members": cmd_list_members,
        "list-add-member": cmd_list_add_member,
        "list-remove-member": cmd_list_remove_member,
        # Trends
        "trends": cmd_trends,
        # Spaces
        "spaces": cmd_spaces_search,
        "space": cmd_space_get,
        # Streams (Pro)
        "stream-rules-add": cmd_stream_rules_add,
        "stream-rules-list": cmd_stream_rules_list,
        "stream-rules-delete": cmd_stream_rules_delete,
        "stream-filter": cmd_stream_filter,
        "stream-sample": cmd_stream_sample,
        # Full-archive search (Pro)
        "search-all": cmd_search_all,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
