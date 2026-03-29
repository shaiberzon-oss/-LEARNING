"""YouTube connector — fetches videos from a playlist via YouTube Data API v3."""
from googleapiclient.discovery import build


def list_channel_playlists(channel_query: str, api_key: str) -> list[dict]:
    """List playlists for a channel ID or search for playlists by query."""
    youtube = build("youtube", "v3", developerKey=api_key)

    if channel_query.startswith("UC"):
        # It's a channel ID — list that channel's playlists
        request = youtube.playlists().list(
            part="snippet,contentDetails",
            channelId=channel_query,
            maxResults=25,
        )
        response = request.execute()
        playlists = []
        for item in response.get("items", []):
            snippet = item.get("snippet", {})
            thumbs = snippet.get("thumbnails", {})
            thumb = (thumbs.get("medium", {}).get("url") or thumbs.get("default", {}).get("url", ""))
            playlists.append({
                "id": item.get("id", ""),
                "title": snippet.get("title", "Untitled"),
                "description": snippet.get("description", "")[:100],
                "thumbnail": thumb,
                "count": item.get("contentDetails", {}).get("itemCount", 0),
                "channel": snippet.get("channelTitle", ""),
            })
    else:
        # Search for playlists by query
        request = youtube.search().list(
            part="snippet",
            q=channel_query,
            type="playlist",
            maxResults=15,
        )
        response = request.execute()
        playlists = []
        for item in response.get("items", []):
            snippet = item.get("snippet", {})
            pl_id = item.get("id", {}).get("playlistId", "")
            if not pl_id:
                continue
            thumbs = snippet.get("thumbnails", {})
            thumb = (thumbs.get("default", {}).get("url") or thumbs.get("medium", {}).get("url", ""))
            playlists.append({
                "id": pl_id,
                "title": snippet.get("title", "Untitled"),
                "description": snippet.get("description", "")[:100],
                "thumbnail": thumb,
                "count": 0,
                "channel": snippet.get("channelTitle", ""),
            })

    return playlists


def fetch_playlist(playlist_id: str, api_key: str) -> list[dict]:
    """Fetch all videos in a YouTube playlist. Returns list of item dicts."""
    youtube = build("youtube", "v3", developerKey=api_key)
    items = []
    next_page_token = None

    while True:
        request = youtube.playlistItems().list(
            part="snippet,contentDetails",
            playlistId=playlist_id,
            maxResults=50,
            pageToken=next_page_token,
        )
        response = request.execute()

        for item in response.get("items", []):
            snippet = item.get("snippet", {})
            video_id = snippet.get("resourceId", {}).get("videoId", "")
            if not video_id:
                continue

            thumbnails = snippet.get("thumbnails", {})
            thumbnail = (
                thumbnails.get("medium", {}).get("url")
                or thumbnails.get("default", {}).get("url", "")
            )
            published = snippet.get("publishedAt", "")[:10] if snippet.get("publishedAt") else ""

            items.append({
                "source": "youtube",
                "source_id": f"yt_{video_id}",
                "title": snippet.get("title", "Unknown Video"),
                "content": snippet.get("description", ""),
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "thumbnail": thumbnail,
                "created_at": published,
            })

        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break

    return items
