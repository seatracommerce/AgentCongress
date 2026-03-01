#!/usr/bin/env python3
"""Test Twitter/X API credentials without posting. Run from project root:
    PYTHONPATH=. python backend/scripts/test_twitter.py
"""
from __future__ import annotations

import sys


def main() -> int:
    from backend.config import get_settings
    from backend.services.social_publisher import _make_tweepy_client

    settings = get_settings()
    required = [
        ("TWITTER_API_KEY", settings.twitter_api_key),
        ("TWITTER_API_SECRET", settings.twitter_api_secret),
        ("TWITTER_ACCESS_TOKEN", settings.twitter_access_token),
        ("TWITTER_ACCESS_SECRET", settings.twitter_access_secret),
    ]
    missing = [name for name, val in required if not (val and val.strip())]
    if missing:
        print("Missing or empty env vars:", ", ".join(missing))
        print("Set them in .env (see .env.example).")
        return 1

    try:
        client = _make_tweepy_client(settings)
        me = client.get_me()
        if me and me.data:
            username = getattr(me.data, "username", None) or "—"
            name = getattr(me.data, "name", None) or "—"
            print(f"Twitter API OK — authenticated as @{username} ({name})")
        else:
            print("Twitter API OK — credentials accepted.")
        return 0
    except Exception as e:
        print("Twitter API error:", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
