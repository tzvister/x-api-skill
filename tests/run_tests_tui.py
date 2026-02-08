#!/usr/bin/env python3
"""
Interactive TUI for exploring xpost functionality.
Runs real commands against the live X API and shows the output.

Each demo asks you for input with a sensible default — press Enter to
accept the default or type your own value.

Usage:
    python3 tests/run_tests_tui.py
"""

import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

# ── Paths ──

ROOT_DIR = Path(__file__).resolve().parent.parent
SCRIPT = ROOT_DIR / "scripts" / "xpost.py"

# Load .env
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT_DIR / ".env", override=True)
except ImportError:
    pass

# ── ANSI ──

BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
WHITE = "\033[37m"
RESET = "\033[0m"


# ── Runner ──

def xpost(*args, timeout=30):
    """Run an xpost command, return (ok, stdout, stderr)."""
    cmd = [sys.executable, str(SCRIPT)] + list(args)
    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=timeout, env=os.environ.copy(), cwd=str(ROOT_DIR),
        )
        return r.returncode == 0, r.stdout.strip(), r.stderr.strip()
    except subprocess.TimeoutExpired:
        return False, "", "Timed out (this is normal for streaming endpoints)"


def pretty_json(text, max_lines=40):
    """Try to pretty-print JSON output, truncating if long."""
    try:
        parsed = json.loads(text)
        formatted = json.dumps(parsed, indent=2)
    except (json.JSONDecodeError, TypeError):
        formatted = text
    lines = formatted.splitlines()
    if len(lines) > max_lines:
        return "\n".join(lines[:max_lines]) + f"\n{DIM}... ({len(lines) - max_lines} more lines){RESET}"
    return formatted


# ── Display ──

def clear():
    os.system("cls" if os.name == "nt" else "clear")


def header():
    print(f"\n{BOLD}{CYAN}  xpost — Interactive API Explorer{RESET}")
    print(f"  {DIM}Run commands against the live X API and see results{RESET}")
    print(f"  {CYAN}{'─' * 52}{RESET}")


def show_result(label, ok, stdout, stderr):
    """Display the result of a command."""
    if ok:
        print(f"\n  {GREEN}OK{RESET} {BOLD}{label}{RESET}")
        if stdout:
            for line in pretty_json(stdout).splitlines():
                print(f"    {line}")
        elif stderr:
            # Show informational stderr (e.g. "No liked tweets found") when stdout is empty
            for line in stderr.splitlines()[:5]:
                print(f"    {DIM}{line}{RESET}")
    else:
        print(f"\n  {RED}ERROR{RESET} {BOLD}{label}{RESET}")
        if stderr:
            for line in stderr.splitlines()[:10]:
                print(f"    {YELLOW}{line}{RESET}")
        if stdout:
            for line in stdout.splitlines()[:5]:
                print(f"    {DIM}{line}{RESET}")
    print()


def ask(prompt, default=""):
    """Prompt the user for input with a default value. Enter accepts default."""
    try:
        hint = f" [{default}]" if default else ""
        val = input(f"  {BOLD}{prompt}{RESET}{DIM}{hint}{RESET}: ").strip()
        return val if val else default
    except (EOFError, KeyboardInterrupt):
        print()
        return default


def confirm_write(action="This will write to X"):
    """Ask user to confirm a write operation. Returns True if confirmed, False to skip."""
    try:
        val = input(f"  {YELLOW}{action}. Proceed? (y/n){RESET} [{BOLD}y{RESET}]: ").strip().lower()
        if val in ("n", "no", "skip"):
            print(f"  {DIM}Skipped write operations.{RESET}\n")
            return False
        return True
    except (EOFError, KeyboardInterrupt):
        print()
        return False


def pause():
    try:
        input(f"  {DIM}Press Enter to continue...{RESET}")
    except (EOFError, KeyboardInterrupt):
        print()


# ── Test Definitions ──
# Each test is a (name, description, callable) tuple.
# The callable runs the test and prints results.


def build_tests():
    """Build the list of available tests."""
    target = os.environ.get("TEST_TARGET_USERNAME", "").strip().lstrip("@")
    tests = []

    # ── 1. Auth & Account ──

    def run_verify():
        print(f"\n  {DIM}Checking OAuth 1.0a credentials...{RESET}")
        ok, out, err = xpost("verify")
        show_result("xpost verify", ok, out, err)

    tests.append(("Verify credentials", "Check that your OAuth 1.0a keys work", run_verify))

    def run_me():
        print(f"\n  {DIM}Fetching your profile...{RESET}")
        ok, out, err = xpost("me")
        show_result("xpost me", ok, out, err)

    tests.append(("My profile", "Fetch your authenticated user info", run_me))

    # ── 2. User Lookup & Timeline ──

    def run_user():
        username = ask("Username to look up", "NASA")
        ok, out, err = xpost("user", username)
        show_result(f"xpost user {username}", ok, out, err)

    tests.append(("Look up user", "Fetch any user's profile — bio, location, follower counts", run_user))

    def run_user_timeline():
        username = ask("Username to read", "NASA")
        count = ask("How many tweets", "5")
        ok, out, err = xpost("user-timeline", username, "-n", count)
        show_result(f"xpost user-timeline {username} -n {count}", ok, out, err)

    tests.append(("User timeline", "Get a user's latest tweets", run_user_timeline))

    def run_search():
        query = ask("Search query", "AI agents 2026")
        count = ask("How many results", "5")
        ok, out, err = xpost("search", query, "-n", count)
        show_result(f'xpost search "{query}" -n {count}', ok, out, err)

    tests.append(("Search tweets", "Search recent tweets for any topic", run_search))

    def run_mentions():
        count = ask("How many mentions", "5")
        ok, out, err = xpost("mentions", "-n", count)
        show_result(f"xpost mentions -n {count}", ok, out, err)

    tests.append(("My mentions", "Fetch tweets that mention you", run_mentions))

    def run_timeline():
        count = ask("How many tweets", "5")
        ok, out, err = xpost("timeline", "-n", count)
        show_result(f"xpost timeline -n {count}", ok, out, err)

    tests.append(("My timeline", "Fetch your home timeline (tweets from people you follow)", run_timeline))

    # ── 3. Social Graph ──

    def run_followers():
        username = ask("Whose followers to list", "openai")
        count = ask("How many", "10")
        ok, out, err = xpost("followers", username, "-n", count)
        show_result(f"xpost followers {username} -n {count}", ok, out, err)

    tests.append(("Followers", "List followers of any account", run_followers))

    def run_following():
        username = ask("Whose following list", "openai")
        count = ask("How many", "10")
        ok, out, err = xpost("following", username, "-n", count)
        show_result(f"xpost following {username} -n {count}", ok, out, err)

    tests.append(("Following", "List accounts that a user follows", run_following))

    def run_liked():
        username = ask("Whose liked tweets (most accounts have private likes — use your own)", "me")
        if username == "me":
            # Resolve to the authenticated user
            ok, out, err = xpost("me")
            if ok:
                try:
                    username = json.loads(out).get("username", "me")
                except (json.JSONDecodeError, TypeError, AttributeError):
                    pass
        count = ask("How many", "5")
        ok, out, err = xpost("liked", username, "-n", count)
        show_result(f"xpost liked {username} -n {count}", ok, out, err)

    tests.append(("Liked tweets", "See tweets you (or another user) have liked — most accounts have private likes", run_liked))

    # ── 4. Tweet Lifecycle ──

    def run_tweet_lifecycle():
        text = ask("Tweet text", f"Hello from xpost! Testing the full tweet lifecycle [{uuid.uuid4().hex[:6]}]")

        if not confirm_write("This will post a tweet, reply, then delete both"):
            return

        print(f"\n  {DIM}1. Posting tweet...{RESET}")
        ok, out, err = xpost("tweet", text)
        show_result(f'xpost tweet "{text}"', ok, out, err)
        if not ok:
            return

        tweet_id = json.loads(out).get("data", {}).get("id")
        if not tweet_id:
            print(f"    {RED}Could not extract tweet ID{RESET}")
            return

        time.sleep(2)

        # Get
        print(f"  {DIM}2. Fetching tweet back by ID...{RESET}")
        ok, out, err = xpost("get", tweet_id)
        show_result(f"xpost get {tweet_id}", ok, out, err)

        # Reply
        reply_text = ask("Reply text", f"Replying to myself from xpost!")
        print(f"  {DIM}3. Replying to tweet...{RESET}")
        ok, out, err = xpost("reply", tweet_id, reply_text)
        show_result(f'xpost reply {tweet_id} "{reply_text}"', ok, out, err)
        reply_id = None
        if ok:
            reply_id = json.loads(out).get("data", {}).get("id")
            time.sleep(2)

            # Thread
            print(f"  {DIM}4. Fetching conversation thread...{RESET}")
            ok, out, err = xpost("thread", tweet_id)
            show_result(f"xpost thread {tweet_id}", ok, out, err)

        # Cleanup
        print(f"  {DIM}Cleaning up...{RESET}")
        if reply_id:
            xpost("delete", reply_id)
            print(f"    Deleted reply {reply_id}")
        xpost("delete", tweet_id)
        print(f"    Deleted tweet {tweet_id}")

    tests.append(("Tweet lifecycle", "Post, fetch, reply, read thread, then delete — full round-trip", run_tweet_lifecycle))

    def run_tweet_too_long():
        if not confirm_write("This will attempt to post 281 chars (rejected client-side, never actually posts)"):
            return
        print(f"\n  {DIM}Attempting to post 281 characters (limit is 280)...{RESET}")
        ok, out, err = xpost("tweet", "x" * 281)
        show_result('xpost tweet "xxx...x" (281 chars)', ok, out, err)
        if not ok:
            print(f"    {GREEN}(Expected! 280 char limit enforced){RESET}")

    tests.append(("Tweet too long", "Try posting 281 characters — should fail with validation error", run_tweet_too_long))

    # ── 5. Engagement ──

    def run_like_unlike():
        text = ask("Tweet text to like/unlike", f"Testing the like button [{uuid.uuid4().hex[:6]}]")
        if not confirm_write("This will post a tweet, like it, unlike it, then delete"):
            return
        print(f"\n  {DIM}Posting a tweet to engage with...{RESET}")
        ok, out, err = xpost("tweet", text)
        if not ok:
            show_result("xpost tweet", ok, out, err)
            return
        tweet_id = json.loads(out).get("data", {}).get("id")
        show_result(f'xpost tweet "{text}"', ok, out, err)
        time.sleep(1)

        print(f"  {DIM}Liking tweet {tweet_id}...{RESET}")
        ok, out, err = xpost("like", tweet_id)
        show_result(f"xpost like {tweet_id}", ok, out, err)

        print(f"  {DIM}Unliking tweet {tweet_id}...{RESET}")
        ok, out, err = xpost("unlike", tweet_id)
        show_result(f"xpost unlike {tweet_id}", ok, out, err)

        print(f"  {DIM}Cleaning up...{RESET}")
        xpost("delete", tweet_id)
        print(f"    Deleted tweet {tweet_id}")

    tests.append(("Like / Unlike", "Post a tweet, like it, then unlike it", run_like_unlike))

    def run_liking_users():
        if not confirm_write("This will post a tweet, like it, check liking-users, then delete"):
            return
        text = f"Who likes this? [{uuid.uuid4().hex[:6]}]"
        print(f"\n  {DIM}Posting a tweet and liking it...{RESET}")
        ok, out, err = xpost("tweet", text)
        if not ok:
            show_result("xpost tweet", ok, out, err)
            return
        tweet_id = json.loads(out).get("data", {}).get("id")
        show_result(f'xpost tweet "{text}"', ok, out, err)
        time.sleep(1)
        xpost("like", tweet_id)
        print(f"  {DIM}Liked! Now checking who liked it...{RESET}")
        time.sleep(2)
        ok, out, err = xpost("liking-users", tweet_id)
        show_result(f"xpost liking-users {tweet_id}", ok, out, err)
        print(f"  {DIM}Cleaning up...{RESET}")
        xpost("unlike", tweet_id)
        xpost("delete", tweet_id)
        print(f"    Deleted tweet {tweet_id}")

    tests.append(("Liking users", "Post a tweet, like it, then list users who liked it", run_liking_users))

    def run_retweet_unretweet():
        text = ask("Tweet text to retweet", f"Retweet round-trip test [{uuid.uuid4().hex[:6]}]")
        if not confirm_write("This will post a tweet, retweet it, unretweet, then delete"):
            return
        print(f"\n  {DIM}Posting a tweet to retweet...{RESET}")
        ok, out, err = xpost("tweet", text)
        if not ok:
            show_result("xpost tweet", ok, out, err)
            return
        tweet_id = json.loads(out).get("data", {}).get("id")
        show_result(f'xpost tweet "{text}"', ok, out, err)
        time.sleep(1)

        print(f"  {DIM}Retweeting...{RESET}")
        ok, out, err = xpost("retweet", tweet_id)
        show_result(f"xpost retweet {tweet_id}", ok, out, err)
        time.sleep(1)

        print(f"  {DIM}Undoing retweet...{RESET}")
        ok, out, err = xpost("unretweet", tweet_id)
        show_result(f"xpost unretweet {tweet_id}", ok, out, err)

        print(f"  {DIM}Cleaning up...{RESET}")
        xpost("delete", tweet_id)
        print(f"    Deleted tweet {tweet_id}")

    tests.append(("Retweet / Unretweet", "Post a tweet, retweet it, then undo the retweet", run_retweet_unretweet))

    def run_retweeters():
        if not confirm_write("This will post a tweet, retweet it, check retweeters, then delete"):
            return
        text = f"Who retweeted this? [{uuid.uuid4().hex[:6]}]"
        print(f"\n  {DIM}Posting a tweet and retweeting it...{RESET}")
        ok, out, err = xpost("tweet", text)
        if not ok:
            show_result("xpost tweet", ok, out, err)
            return
        tweet_id = json.loads(out).get("data", {}).get("id")
        show_result(f'xpost tweet "{text}"', ok, out, err)
        time.sleep(1)
        xpost("retweet", tweet_id)
        print(f"  {DIM}Retweeted! Now checking who retweeted it...{RESET}")
        time.sleep(2)
        ok, out, err = xpost("retweeters", tweet_id)
        show_result(f"xpost retweeters {tweet_id}", ok, out, err)
        print(f"  {DIM}Cleaning up...{RESET}")
        xpost("unretweet", tweet_id)
        xpost("delete", tweet_id)
        print(f"    Deleted tweet {tweet_id}")

    tests.append(("Retweeters", "Post a tweet, retweet it, then list who retweeted", run_retweeters))

    # ── 6. Follow / Unfollow ──

    def run_follow_unfollow():
        username = ask("Username to follow/unfollow", target or "NASA")
        if not confirm_write(f"This will follow @{username} then immediately unfollow"):
            return
        print(f"\n  {DIM}Following @{username}...{RESET}")
        ok, out, err = xpost("follow", username)
        show_result(f"xpost follow {username}", ok, out, err)
        if ok:
            time.sleep(1)
            print(f"  {DIM}Unfollowing @{username}...{RESET}")
            ok, out, err = xpost("unfollow", username)
            show_result(f"xpost unfollow {username}", ok, out, err)

    tests.append(("Follow / Unfollow", "Follow a user and immediately unfollow them", run_follow_unfollow))

    # ── 7. Hide / Unhide Replies ──

    def run_hide_unhide():
        parent_text = ask("Parent tweet text", f"Testing reply hiding [{uuid.uuid4().hex[:6]}]")
        reply_text = ask("Reply to hide", "This reply will be hidden and then unhidden!")
        if not confirm_write("This will post a tweet + reply, hide/unhide the reply, then delete both"):
            return
        print(f"\n  {DIM}Posting parent tweet...{RESET}")
        ok, out, err = xpost("tweet", parent_text)
        if not ok:
            show_result("xpost tweet", ok, out, err)
            return
        tweet_id = json.loads(out).get("data", {}).get("id")
        show_result(f'xpost tweet "{parent_text}"', ok, out, err)
        time.sleep(1)

        print(f"  {DIM}Posting reply...{RESET}")
        ok, out, err = xpost("reply", tweet_id, reply_text)
        if not ok:
            show_result("xpost reply", ok, out, err)
            xpost("delete", tweet_id)
            return
        reply_id = json.loads(out).get("data", {}).get("id")
        show_result(f'xpost reply {tweet_id} "{reply_text}"', ok, out, err)
        time.sleep(1)

        print(f"  {DIM}Hiding reply {reply_id}...{RESET}")
        ok, out, err = xpost("hide", reply_id)
        show_result(f"xpost hide {reply_id}", ok, out, err)
        time.sleep(1)

        print(f"  {DIM}Unhiding reply {reply_id}...{RESET}")
        ok, out, err = xpost("unhide", reply_id)
        show_result(f"xpost unhide {reply_id}", ok, out, err)

        print(f"  {DIM}Cleaning up...{RESET}")
        xpost("delete", reply_id)
        xpost("delete", tweet_id)
        print(f"    Deleted reply and parent tweet")

    tests.append(("Hide / Unhide reply", "Post a reply, hide it from the conversation, then unhide", run_hide_unhide))

    # ── 8. Moderation ──

    def run_mute_unmute():
        username = ask("Username to mute/unmute", target or "xDevelopers")
        if not confirm_write(f"This will mute @{username} then immediately unmute"):
            return
        print(f"\n  {DIM}Muting @{username}...{RESET}")
        ok, out, err = xpost("mute", username)
        show_result(f"xpost mute {username}", ok, out, err)
        if ok:
            time.sleep(1)
            print(f"  {DIM}Unmuting @{username}...{RESET}")
            ok, out, err = xpost("unmute", username)
            show_result(f"xpost unmute {username}", ok, out, err)

    tests.append(("Mute / Unmute", "Mute a user (hides their tweets from your timeline), then unmute", run_mute_unmute))

    def run_block_unblock():
        username = ask("Username to block/unblock", target or "xDevelopers")
        if not confirm_write(f"This will block @{username} then immediately unblock"):
            return
        print(f"\n  {DIM}Blocking @{username}...{RESET}")
        ok, out, err = xpost("block", username)
        show_result(f"xpost block {username}", ok, out, err)
        if ok:
            time.sleep(1)
            print(f"  {DIM}Unblocking @{username}...{RESET}")
            ok, out, err = xpost("unblock", username)
            show_result(f"xpost unblock {username}", ok, out, err)

    tests.append(("Block / Unblock", "Block a user (prevents all interaction), then unblock", run_block_unblock))

    # ── 9. Direct Messages ──

    def run_dm_list():
        count = ask("How many DM events", "5")
        ok, out, err = xpost("dm-list", "-n", count)
        show_result(f"xpost dm-list -n {count}", ok, out, err)

    tests.append(("List DMs", "Show your most recent DM events (messages sent and received)", run_dm_list))

    def run_dm_send():
        username = ask("Username to DM", target or "")
        if not username:
            print(f"  {YELLOW}No username provided, skipping.{RESET}")
            return
        message = ask("Message text", f"Hey! This is a test DM from xpost [{uuid.uuid4().hex[:6]}]")
        if not confirm_write(f"This will send a DM to @{username}"):
            return
        ok, out, err = xpost("dm", username, message)
        show_result(f'xpost dm {username} "{message}"', ok, out, err)

    tests.append(("Send DM", "Send a direct message to any user", run_dm_send))

    # ── 10. Bearer Token / Streams ──

    def run_stream_rules():
        print(f"\n  {DIM}Listing current rules...{RESET}")
        ok, out, err = xpost("stream-rules-list")
        show_result("xpost stream-rules-list", ok, out, err)
        if not ok:
            return

        rule = ask("Stream filter rule to add", "breaking news OR #trending")
        tag = ask("Rule label/tag", "demo")
        if not confirm_write("This will add a stream rule then immediately delete it"):
            return

        print(f"  {DIM}Adding rule: \"{rule}\"...{RESET}")
        ok, out, err = xpost("stream-rules-add", rule, "--tag", tag)
        show_result(f'xpost stream-rules-add "{rule}" --tag "{tag}"', ok, out, err)
        if not ok:
            return

        rule_id = None
        try:
            rules = json.loads(out).get("data", [])
            if rules:
                rule_id = rules[0].get("id")
        except (json.JSONDecodeError, TypeError):
            pass

        if rule_id:
            print(f"  {DIM}Deleting rule {rule_id}...{RESET}")
            ok, out, err = xpost("stream-rules-delete", rule_id)
            show_result(f"xpost stream-rules-delete {rule_id}", ok, out, err)

    tests.append(("Stream rules", "Add, list, and delete a filtered stream rule (Pro tier)", run_stream_rules))

    def run_stream_filter():
        print(f"\n  {DIM}Connecting to filtered stream (will timeout if no matching tweets)...{RESET}")
        ok, out, err = xpost("stream-filter", "-n", "1", timeout=10)
        show_result("xpost stream-filter -n 1", ok, out, err)

    tests.append(("Filtered stream", "Connect to filtered stream — receives tweets matching your rules (Pro)", run_stream_filter))

    def run_stream_sample():
        print(f"\n  {DIM}Connecting to 1% volume stream...{RESET}")
        ok, out, err = xpost("stream-sample", "-n", "1", timeout=10)
        show_result("xpost stream-sample -n 1", ok, out, err)

    tests.append(("Volume stream", "Connect to the 1% sample stream of all tweets (Pro)", run_stream_sample))

    def run_search_all():
        query = ask("Full-archive search query", "from:NASA moon landing")
        count = ask("How many results", "5")
        ok, out, err = xpost("search-all", query, "-n", count)
        show_result(f'xpost search-all "{query}" -n {count}', ok, out, err)

    tests.append(("Full-archive search", "Search ALL historical tweets, not just recent (Pro)", run_search_all))

    # ── 11. Bookmarks ──

    def run_bookmarks_list():
        count = ask("How many bookmarks", "5")
        ok, out, err = xpost("bookmarks", "-n", count)
        show_result(f"xpost bookmarks -n {count}", ok, out, err)

    tests.append(("List bookmarks", "Show your most recent bookmarked tweets", run_bookmarks_list))

    def run_bookmark_add():
        text = ask("Tweet text to bookmark", f"Bookmarking this for later [{uuid.uuid4().hex[:6]}]")
        if not confirm_write("This will post a tweet, bookmark it, verify, then clean up"):
            return
        print(f"\n  {DIM}Posting a tweet...{RESET}")
        ok, out, err = xpost("tweet", text)
        if not ok:
            show_result("xpost tweet", ok, out, err)
            return
        tweet_id = json.loads(out).get("data", {}).get("id")
        show_result(f'xpost tweet "{text}"', ok, out, err)
        time.sleep(1)

        # Bookmark it
        print(f"  {DIM}Bookmarking tweet {tweet_id}...{RESET}")
        ok, out, err = xpost("bookmark", tweet_id)
        show_result(f"xpost bookmark {tweet_id}", ok, out, err)

        if not ok:
            print(f"  {DIM}Cleaning up...{RESET}")
            xpost("delete", tweet_id)
            print(f"    Deleted tweet {tweet_id}")
            return

        time.sleep(1)

        # List bookmarks to show it's there
        print(f"  {DIM}Fetching bookmarks to confirm...{RESET}")
        ok, out, err = xpost("bookmarks", "-n", "5")
        show_result("xpost bookmarks -n 5", ok, out, err)

        # Unbookmark and clean up
        print(f"  {DIM}Cleaning up...{RESET}")
        xpost("unbookmark", tweet_id)
        print(f"    Unbookmarked tweet {tweet_id}")
        xpost("delete", tweet_id)
        print(f"    Deleted tweet {tweet_id}")

    tests.append(("Bookmark a tweet", "Post a tweet, bookmark it, verify it appears in bookmarks, then clean up", run_bookmark_add))

    def run_bookmark_folders():
        print(f"\n  {DIM}Listing bookmark folders...{RESET}")
        ok, out, err = xpost("bookmark-folders")
        show_result("xpost bookmark-folders", ok, out, err)

    tests.append(("Bookmark folders", "List your bookmark folders (if you've organized bookmarks into folders)", run_bookmark_folders))

    # ── 12. Lists ──

    def run_my_lists():
        print(f"\n  {DIM}Listing your owned lists...{RESET}")
        ok, out, err = xpost("my-lists")
        show_result("xpost my-lists", ok, out, err)

    tests.append(("My lists", "Show all X Lists you've created", run_my_lists))

    def run_list_lifecycle():
        list_name = ask("New list name", f"xpost-demo-{uuid.uuid4().hex[:6]}")
        list_desc = ask("List description", "A demo list created by xpost")
        member = ask("Username to add as member", target or "NASA")

        if not confirm_write("This will create a list, add/remove a member, then delete the list"):
            return

        print(f"\n  {DIM}1. Creating list \"{list_name}\"...{RESET}")
        ok, out, err = xpost("list-create", list_name, "--description", list_desc)
        show_result(f'xpost list-create "{list_name}" --description "{list_desc}"', ok, out, err)
        if not ok:
            return
        list_id = json.loads(out).get("data", {}).get("id")
        if not list_id:
            print(f"    {RED}Could not extract list ID{RESET}")
            return

        time.sleep(1)

        # Lookup
        print(f"  {DIM}2. Looking up list by ID...{RESET}")
        ok, out, err = xpost("list", list_id)
        show_result(f"xpost list {list_id}", ok, out, err)

        # Add member
        print(f"  {DIM}3. Adding @{member} to list...{RESET}")
        ok, out, err = xpost("list-add-member", list_id, member)
        show_result(f"xpost list-add-member {list_id} {member}", ok, out, err)
        time.sleep(1)

        # Members
        print(f"  {DIM}4. Listing members...{RESET}")
        ok, out, err = xpost("list-members", list_id)
        show_result(f"xpost list-members {list_id}", ok, out, err)

        # Tweets
        print(f"  {DIM}5. Fetching tweets from list...{RESET}")
        ok, out, err = xpost("list-tweets", list_id, "-n", "3")
        show_result(f"xpost list-tweets {list_id} -n 3", ok, out, err)

        # Remove member
        print(f"  {DIM}6. Removing @{member} from list...{RESET}")
        ok, out, err = xpost("list-remove-member", list_id, member)
        show_result(f"xpost list-remove-member {list_id} {member}", ok, out, err)

        # Delete
        print(f"  {DIM}7. Deleting list...{RESET}")
        ok, out, err = xpost("list-delete", list_id)
        show_result(f"xpost list-delete {list_id}", ok, out, err)

    tests.append(("List lifecycle", "Create a list, add a member, view tweets, remove member, delete list", run_list_lifecycle))

    # ── 13. Trends & Spaces ──

    def run_trends():
        woeid = ask("WOEID (1=worldwide, 23424977=US, 23424975=UK)", "1")
        ok, out, err = xpost("trends", "--woeid", woeid)
        show_result(f"xpost trends --woeid {woeid}", ok, out, err)

    tests.append(("Trends", "See what's trending — worldwide or for a specific country", run_trends))

    def run_spaces():
        query = ask("Search Spaces about", "AI startups")
        ok, out, err = xpost("spaces", query)
        show_result(f'xpost spaces "{query}"', ok, out, err)

    tests.append(("Search Spaces", "Find live or scheduled X Spaces on a topic", run_spaces))

    # ── 14. Profile ──

    def run_profile():
        bio = ask("New bio text", f"Building cool things with xpost | {uuid.uuid4().hex[:6]}")
        if not confirm_write("This will change your X bio"):
            return
        ok, out, err = xpost("profile", bio)
        show_result(f'xpost profile "{bio}"', ok, out, err)

    tests.append(("Update profile bio", "Change your X bio text (uses v1.1 API)", run_profile))

    return tests


# ── Main Loop ──

def main():
    tests = build_tests()

    while True:
        clear()
        header()
        print()

        for i, (name, desc, _) in enumerate(tests, 1):
            print(f"  {BOLD}{CYAN}{i:2d}{RESET}  {BOLD}{name}{RESET}")
            print(f"      {DIM}{desc}{RESET}")

        print(f"\n  {BOLD}{CYAN} a{RESET}  {BOLD}Run all{RESET}")
        print(f"      {DIM}Execute every test sequentially{RESET}")
        print(f"\n  {BOLD}{CYAN} q{RESET}  {BOLD}Quit{RESET}\n")

        try:
            choice = input(f"  {BOLD}Choose> {RESET}").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if choice == "q":
            break
        elif choice == "a":
            clear()
            header()
            for i, (name, desc, fn) in enumerate(tests, 1):
                print(f"\n  {CYAN}{'━' * 52}{RESET}")
                print(f"  {BOLD}[{i}/{len(tests)}] {name}{RESET}")
                print(f"  {DIM}{desc}{RESET}")
                fn()
                pause()
            continue
        else:
            try:
                idx = int(choice)
                if 1 <= idx <= len(tests):
                    name, desc, fn = tests[idx - 1]
                    clear()
                    header()
                    print(f"\n  {BOLD}{name}{RESET}")
                    print(f"  {DIM}{desc}{RESET}")
                    fn()
                    pause()
            except ValueError:
                continue


if __name__ == "__main__":
    main()
