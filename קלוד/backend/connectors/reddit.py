"""Reddit connector — fetches saved posts via Reddit API (password-based OAuth)."""
import httpx


def fetch_saved_posts(username: str, client_id: str, client_secret: str,
                      password: str, max_items: int = 200) -> list[dict]:
    """Fetch saved posts/comments for a Reddit user using script-type OAuth."""
    ua = f"KnowledgeHub/1.0 by u/{username}"

    # Get access token
    r = httpx.post(
        "https://www.reddit.com/api/v1/access_token",
        auth=(client_id, client_secret),
        headers={"User-Agent": ua},
        data={"grant_type": "password", "username": username, "password": password},
        timeout=15,
    )
    r.raise_for_status()
    token = r.json().get("access_token")
    if not token:
        raise ValueError("Reddit auth failed — check client_id, client_secret, username, and password.")

    headers = {"Authorization": f"bearer {token}", "User-Agent": ua}
    items = []
    after = None

    while len(items) < max_items:
        params = {"limit": min(100, max_items - len(items))}
        if after:
            params["after"] = after

        r = httpx.get(
            f"https://oauth.reddit.com/user/{username}/saved",
            headers=headers,
            params=params,
            timeout=15,
        )
        r.raise_for_status()
        data = r.json().get("data", {})

        posts = data.get("children", [])
        if not posts:
            break

        for post in posts:
            kind = post.get("kind", "t3")
            p = post.get("data", {})
            pid = p.get("id", "")
            permalink = f"https://reddit.com{p.get('permalink', '')}"
            subreddit = p.get("subreddit", "")

            if kind == "t3":  # Post / link
                thumb = p.get("thumbnail", "")
                items.append({
                    "source": "reddit",
                    "source_id": f"reddit_{pid}",
                    "title": p.get("title", "Untitled"),
                    "content": p.get("selftext", "") or p.get("url", ""),
                    "url": permalink,
                    "thumbnail": thumb if thumb.startswith("http") else "",
                    "created_at": "",
                })
            elif kind == "t1":  # Comment
                items.append({
                    "source": "reddit",
                    "source_id": f"reddit_c_{pid}",
                    "title": f"Comment in r/{subreddit}",
                    "content": p.get("body", ""),
                    "url": permalink,
                    "thumbnail": "",
                    "created_at": "",
                })

        after = data.get("after")
        if not after:
            break

    return items
