"""Twitter/X connector — fetches liked tweets via Twitter API v2 (Bearer Token)."""
import httpx


def fetch_liked_tweets(username: str, bearer_token: str, max_items: int = 200) -> list[dict]:
    """Fetch liked tweets for a user. Requires a Twitter Developer Bearer Token."""
    headers = {"Authorization": f"Bearer {bearer_token}"}

    # Resolve username → user ID
    r = httpx.get(
        f"https://api.twitter.com/2/users/by/username/{username}",
        headers=headers,
        timeout=15,
    )
    r.raise_for_status()
    user_data = r.json().get("data")
    if not user_data:
        raise ValueError(f"Twitter user '{username}' not found.")
    user_id = user_data["id"]

    items = []
    pagination_token = None

    while len(items) < max_items:
        params = {
            "max_results": min(100, max_items - len(items)),
            "tweet.fields": "created_at,text",
        }
        if pagination_token:
            params["pagination_token"] = pagination_token

        r = httpx.get(
            f"https://api.twitter.com/2/users/{user_id}/liked_tweets",
            headers=headers,
            params=params,
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()

        for tweet in data.get("data") or []:
            tid = tweet.get("id", "")
            text = tweet.get("text", "")
            items.append({
                "source": "twitter",
                "source_id": f"tw_{tid}",
                "title": text[:120],
                "content": text,
                "url": f"https://x.com/i/web/status/{tid}",
                "thumbnail": "",
                "created_at": tweet.get("created_at", "")[:10],
            })

        pagination_token = data.get("meta", {}).get("next_token")
        if not pagination_token:
            break

    return items


def fetch_bookmarks(user_id: str, bearer_token: str, max_items: int = 200) -> list[dict]:
    """Fetch bookmarks for a user (requires OAuth 2.0 user token with bookmarks.read scope)."""
    headers = {"Authorization": f"Bearer {bearer_token}"}
    items = []
    pagination_token = None

    while len(items) < max_items:
        params = {
            "max_results": min(100, max_items - len(items)),
            "tweet.fields": "created_at,text",
        }
        if pagination_token:
            params["pagination_token"] = pagination_token

        r = httpx.get(
            f"https://api.twitter.com/2/users/{user_id}/bookmarks",
            headers=headers,
            params=params,
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()

        for tweet in data.get("data") or []:
            tid = tweet.get("id", "")
            text = tweet.get("text", "")
            items.append({
                "source": "twitter",
                "source_id": f"tw_bm_{tid}",
                "title": text[:120],
                "content": text,
                "url": f"https://x.com/i/web/status/{tid}",
                "thumbnail": "",
                "created_at": tweet.get("created_at", "")[:10],
            })

        pagination_token = data.get("meta", {}).get("next_token")
        if not pagination_token:
            break

    return items
