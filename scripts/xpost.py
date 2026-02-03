#!/usr/bin/env python3
"""
X/Twitter CLI using raw X API v2 with OAuth 1.0a.

XDK v0.5.0 has broken Pydantic models (empty model_fields, model_dump returns {}).
This script uses XDK only for OAuth1 setup + read endpoints, and raw requests
for write operations (tweet, reply, delete).

Usage:
  python3 scripts/xpost.py tweet "Hello world"
  python3 scripts/xpost.py reply <tweet-id> "Reply text"
  python3 scripts/xpost.py get <tweet-id>
  python3 scripts/xpost.py thread <tweet-id> [-n 20]
  python3 scripts/xpost.py like <tweet-id>
  python3 scripts/xpost.py unlike <tweet-id>
  python3 scripts/xpost.py follow <username>
  python3 scripts/xpost.py search "query" [-n 10]
  python3 scripts/xpost.py mentions [-n 10]
  python3 scripts/xpost.py timeline [-n 10]
  python3 scripts/xpost.py profile "new bio text"
  python3 scripts/xpost.py delete <tweet-id>
  python3 scripts/xpost.py verify
  python3 scripts/xpost.py me

Requires: pip install xdk requests-oauthlib
"""

import argparse
import json
import os
import sys

API_BASE = "https://api.x.com/2"


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


# ── Commands ──


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


def cmd_verify(args):
    client = get_client()
    me = client.users.get_me()
    print(f"Authenticated as: {me}")


def cmd_me(args):
    client = get_client()
    me = client.users.get_me()
    print(json.dumps(me, indent=2, default=str))


def cmd_search(args):
    client = get_client()
    n = max(args.n, 10)  # API minimum is 10
    results = client.posts.search_recent(query=args.query, max_results=n)
    for page in results:
        for tweet in (page.data or []):
            print(json.dumps(tweet, indent=2, default=str))
        break  # First page only


def _get_my_id(client):
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


def cmd_mentions(args):
    client = get_client()
    user_id = _get_my_id(client)
    n = max(args.n, 5)
    results = client.users.get_mentions(id=user_id, max_results=n)
    for page in results:
        for tweet in (page.data or []):
            print(json.dumps(tweet, indent=2, default=str))
        break


def cmd_timeline(args):
    client = get_client()
    user_id = _get_my_id(client)
    n = max(args.n, 5)
    results = client.users.get_timeline(id=user_id, max_results=n)
    for page in results:
        for tweet in (page.data or []):
            print(json.dumps(tweet, indent=2, default=str))
        break


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
    users = {}
    if "includes" in data and "users" in data["includes"]:
        users = {u["id"]: u for u in data["includes"]["users"]}
    for tweet in (data.get("data") or []):
        author = users.get(tweet.get("author_id", ""), {})
        tweet["author"] = {"username": author.get("username"), "name": author.get("name")}
        print(json.dumps(tweet, indent=2, default=str))


def cmd_like(args):
    """Like a tweet."""
    import requests
    auth = get_oauth1()
    # Need our user ID
    me_resp = requests.get(f"{API_BASE}/users/me", auth=auth)
    if not me_resp.ok:
        print(f"Error getting user: {me_resp.status_code}", file=sys.stderr)
        sys.exit(1)
    user_id = me_resp.json()["data"]["id"]
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
    me_resp = requests.get(f"{API_BASE}/users/me", auth=auth)
    if not me_resp.ok:
        print(f"Error getting user: {me_resp.status_code}", file=sys.stderr)
        sys.exit(1)
    user_id = me_resp.json()["data"]["id"]
    resp = requests.delete(f"{API_BASE}/users/{user_id}/likes/{args.tweet_id}", auth=auth)
    if not resp.ok:
        print(f"Error: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(resp.json(), indent=2, default=str))


def cmd_follow(args):
    """Follow a user by username."""
    import requests
    auth = get_oauth1()
    # Get our ID
    me_resp = requests.get(f"{API_BASE}/users/me", auth=auth)
    if not me_resp.ok:
        print(f"Error getting user: {me_resp.status_code}", file=sys.stderr)
        sys.exit(1)
    user_id = me_resp.json()["data"]["id"]
    # Resolve target username to ID
    target = args.username.lstrip("@")
    resp = requests.get(f"{API_BASE}/users/by/username/{target}", auth=auth)
    if not resp.ok:
        print(f"Error resolving @{target}: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    target_id = resp.json()["data"]["id"]
    # Follow
    resp = requests.post(
        f"{API_BASE}/users/{user_id}/following",
        json={"target_user_id": target_id},
        auth=auth,
    )
    if not resp.ok:
        print(f"Error: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(resp.json(), indent=2, default=str))


def cmd_retweet(args):
    """Retweet a tweet."""
    import requests
    auth = get_oauth1()
    me_resp = requests.get(f"{API_BASE}/users/me", auth=auth)
    if not me_resp.ok:
        print(f"Error getting user: {me_resp.status_code}", file=sys.stderr)
        sys.exit(1)
    user_id = me_resp.json()["data"]["id"]
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
    me_resp = requests.get(f"{API_BASE}/users/me", auth=auth)
    if not me_resp.ok:
        print(f"Error getting user: {me_resp.status_code}", file=sys.stderr)
        sys.exit(1)
    user_id = me_resp.json()["data"]["id"]
    resp = requests.delete(f"{API_BASE}/users/{user_id}/retweets/{args.tweet_id}", auth=auth)
    if not resp.ok:
        print(f"Error: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(resp.json(), indent=2, default=str))


def cmd_delete(args):
    result = _delete_tweet(args.tweet_id)
    print(json.dumps(result, indent=2, default=str))


def main():
    parser = argparse.ArgumentParser(description="X/Twitter CLI (v2 API + OAuth1)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_tweet = sub.add_parser("tweet", help="Post a tweet")
    p_tweet.add_argument("text", help="Tweet text (max 280 chars)")

    p_reply = sub.add_parser("reply", help="Reply to a tweet")
    p_reply.add_argument("tweet_id", help="Tweet ID to reply to")
    p_reply.add_argument("text", help="Reply text (max 280 chars)")

    sub.add_parser("verify", help="Verify authentication")
    sub.add_parser("me", help="Get your profile info")

    p_search = sub.add_parser("search", help="Search recent tweets")
    p_search.add_argument("query", help="Search query")
    p_search.add_argument("-n", type=int, default=10, help="Max results")

    p_mentions = sub.add_parser("mentions", help="Get your mentions")
    p_mentions.add_argument("-n", type=int, default=10, help="Max results")

    p_timeline = sub.add_parser("timeline", help="Get your timeline")
    p_timeline.add_argument("-n", type=int, default=10, help="Max results")

    p_profile = sub.add_parser("profile", help="Update your bio")
    p_profile.add_argument("text", help="New bio text")

    p_get = sub.add_parser("get", help="Fetch a tweet by ID")
    p_get.add_argument("tweet_id", help="Tweet ID")

    p_thread = sub.add_parser("thread", help="Fetch conversation thread")
    p_thread.add_argument("tweet_id", help="Any tweet ID in the thread")
    p_thread.add_argument("-n", type=int, default=20, help="Max results")

    p_like = sub.add_parser("like", help="Like a tweet")
    p_like.add_argument("tweet_id", help="Tweet ID to like")

    p_unlike = sub.add_parser("unlike", help="Unlike a tweet")
    p_unlike.add_argument("tweet_id", help="Tweet ID to unlike")

    p_follow = sub.add_parser("follow", help="Follow a user")
    p_follow.add_argument("username", help="Username to follow (with or without @)")

    p_retweet = sub.add_parser("retweet", help="Retweet a tweet")
    p_retweet.add_argument("tweet_id", help="Tweet ID to retweet")

    p_unretweet = sub.add_parser("unretweet", help="Undo a retweet")
    p_unretweet.add_argument("tweet_id", help="Tweet ID to unretweet")

    p_delete = sub.add_parser("delete", help="Delete a tweet")
    p_delete.add_argument("tweet_id", help="Tweet ID to delete")

    args = parser.parse_args()

    commands = {
        "tweet": cmd_tweet,
        "reply": cmd_reply,
        "verify": cmd_verify,
        "me": cmd_me,
        "search": cmd_search,
        "mentions": cmd_mentions,
        "timeline": cmd_timeline,
        "profile": cmd_profile,
        "get": cmd_get,
        "thread": cmd_thread,
        "like": cmd_like,
        "unlike": cmd_unlike,
        "follow": cmd_follow,
        "retweet": cmd_retweet,
        "unretweet": cmd_unretweet,
        "delete": cmd_delete,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
