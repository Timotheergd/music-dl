import requests
import re
import base64
import xml.etree.ElementTree as ET
import config

class LyricsEngine:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': config.USER_AGENT})

    def search(self, artist, title, duration):
        """
        Orchestrates the search across 6 strategies.
        Handles deduplication and cleaning.
        """
        # 1. Deduplicate: Prevent "Artist - Artist - Song"
        if artist.lower() in title.lower():
            title = re.sub(re.escape(artist), '', title, flags=re.IGNORECASE).strip(' -–—|')
        
        # 2. Final Safety: If artist is Unknown, try to split title
        if artist.lower() == "unknown" and " - " in title:
            artist, title = title.split(" - ", 1)

        print(f"   - [Lyrics] Searching for: '{artist} - {title}' ({duration}s)")

        # Strategy Chain
        strategies = [
            ("LRCLIB", self._get_lrclib, [artist, title, duration]),
            ("NetEase", self._get_netease, [artist, title]),
            ("QQ Music", self._get_qq, [artist, title]),
            ("Megalyrics", self._get_megalyrics, [artist, title]),
            ("Gecimi", self._get_gecimi, [artist, title]),
            ("Lyrics.ovh", self._get_ovh, [artist, title])
        ]

        for name, func, args in strategies:
            try:
                print(f"     > Checking {name}...")
                result = func(*args)
                if result:
                    return result
            except Exception as e:
                continue # Move to next strategy on failure
        
        return None

    def _get_lrclib(self, artist, title, duration):
        params = {'artist_name': artist, 'track_name': title, 'duration': duration}
        r = self.session.get(config.LRCLIB_URL, params=params, timeout=config.TIMEOUT)
        if r.status_code == 200:
            return r.json().get('syncedLyrics') or r.json().get('plainLyrics')
        return None

    def _get_netease(self, artist, title):
        search_params = {'s': f"{artist} {title}", 'type': 1, 'limit': 1}
        r = self.session.post(config.NETEASE_SEARCH_URL, data=search_params, timeout=config.TIMEOUT)
        data = r.json()
        if 'result' in data and data['result'].get('songs'):
            song_id = data['result']['songs'][0]['id']
            lyric_r = self.session.get(f"{config.NETEASE_LYRIC_URL}?os=pc&id={song_id}&lv=-1&kv=-1&tv=-1")
            return lyric_r.json().get('lrc', {}).get('lyric')
        return None

    def _get_qq(self, artist, title):
        headers = {'Referer': 'https://y.qq.com/'}
        search_params = {'w': f"{artist} {title}", 'format': 'json', 'n': 1}
        r = self.session.get(config.QQ_SEARCH_URL, params=search_params, headers=headers, timeout=config.TIMEOUT)
        data = r.json()
        if 'data' in data and data['data']['song']['list']:
            song_mid = data['data']['song']['list'][0]['songmid']
            lyric_params = {'songmid': song_mid, 'format': 'json', 'nobase64': 0}
            lyric_r = self.session.get(config.QQ_LYRIC_URL, params=lyric_params, headers=headers)
            lyric_data = lyric_r.json()
            if 'lyric' in lyric_data:
                return base64.b64decode(lyric_data['lyric']).decode('utf-8')
        return None

    def _get_megalyrics(self, artist, title):
        params = {'action': 'findLyric', 'artist': artist, 'title': title}
        r = self.session.get(config.MEGALYRICS_URL, params=params, timeout=config.TIMEOUT)
        root = ET.fromstring(r.content)
        for lyric in root.findall('lyric'):
            if lyric.get('type') == 'lrc' or lyric.text:
                return lyric.text
        return None

    def _get_gecimi(self, artist, title):
        r = self.session.get(f"{config.GECIMI_URL}/{title}/{artist}", timeout=config.TIMEOUT)
        data = r.json()
        if 'result' in data and data['result']:
            lrc_url = data['result'][0]['lrc']
            return self.session.get(lrc_url).text
        return None

    def _get_ovh(self, artist, title):
        r = self.session.get(f"{config.OVH_URL}/{artist}/{title}", timeout=config.TIMEOUT)
        if r.status_code == 200:
            return r.json().get('lyrics')
        return None