import os
import requests
import config
import image_processor
import metadata_utils

class CoverEngine:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': config.USER_AGENT})

    def get_cover(self, artist, title, album, folder_path, yt_thumb_url):
        # 1. Clean inputs
        artist = metadata_utils.clean_metadata(artist)
        title = metadata_utils.clean_metadata(title)

        # 2. SMART RECOVERY: If artist is unknown, try to find it in the title
        if artist.lower() == "unknown" and " - " in title:
            parts = title.split(" - ", 1)
            artist, title = parts[0], parts[1]

        # 3. Generic Check (as before)
        clean_album = "".join([c for c in album if c.isalnum() or c in (' ', '-', '_')]).strip()
        is_generic = clean_album.lower() in ["unknown", "album", "video", ""] or len(clean_album) < 3

        # 4. Cache Check
        if not is_generic:
            cache_path = os.path.join(folder_path, f"Album - {clean_album}.jpg")
            if os.path.exists(cache_path):
                with open(cache_path, "rb") as f: return f.read()

        # 5. Deep Search iTunes
        image_data = self._get_itunes_cover(artist, title)

        # 6. YouTube Fallback (Only if we have a URL)
        if not image_data and yt_thumb_url:
            try:
                r = self.session.get(yt_thumb_url, timeout=5)
                if r.status_code == 200:
                    image_data = image_processor.process_to_square_jpg(r.content)
            except: pass

        # 5. Save Logic
        if image_data:
            # ONLY save cover.jpg if it's a REAL album
            # This prevents cover.jpg from appearing in random mix folders
            if not is_generic:
                # Save Album Cache
                cache_path = os.path.join(folder_path, f"Album - {clean_album}.jpg")
                with open(cache_path, "wb") as f: f.write(image_data)

                # Save Folder Icon
                folder_icon = os.path.join(folder_path, "cover.jpg")
                if not os.path.exists(folder_icon):
                    with open(folder_icon, "wb") as f: f.write(image_data)

        return image_data

    def _get_itunes_cover(self, artist, title):
        # Strategy A: Strict Search (Artist + Title)
        data = self._itunes_api_call(f"{artist} {title}")
        if data and data["resultCount"] > 0:
            return self._process_itunes_result(data["results"][0])

        # Strategy B: Relaxed Search (Title Only)
        # We only do this if Strategy A failed
        print(f"     > Strict search failed, trying relaxed search for '{title}'...")
        data = self._itunes_api_call(title)
        if data and data["resultCount"] > 0:
            result = data["results"][0]
            # VALIDATION: Only accept if the artist we are looking for
            # is mentioned in the result's artist name
            itunes_artist = result.get("artistName", "").lower()
            if artist.lower() in itunes_artist or itunes_artist in artist.lower():
                return self._process_itunes_result(result)
            else:
                print(f"     > Validation failed: iTunes found '{itunes_artist}' but we wanted '{artist}'")

        return None

    def _itunes_api_call(self, term):
        """Helper for the raw API request."""
        try:
            params = {"term": term, "media": "music", "limit": 1}
            r = self.session.get(config.ITUNES_API_URL, params=params, timeout=5)
            return r.json()
        except: return None

    def _process_itunes_result(self, result):
        """Helper to download and process the image from a result."""
        try:
            img_url = result["artworkUrl100"].replace("100x100bb", "1000x1000bb")
            img_r = self.session.get(img_url, timeout=5)
            return image_processor.process_to_square_jpg(img_r.content)
        except: return None
