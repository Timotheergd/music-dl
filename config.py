import os

# Paths
DOWNLOAD_DIR = "/app/downloads"
SONG_LIST = "songs.txt"

# Network Settings
TIMEOUT = 10
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/91.0.4472.124 Safari/537.36"
)

# API Endpoints
LRCLIB_URL = "https://lrclib.net/api/get"
NETEASE_SEARCH_URL = "http://music.163.com/api/search/get/web"
NETEASE_LYRIC_URL = "http://music.163.com/api/song/lyric"
QQ_SEARCH_URL = "https://c.y.qq.com/soso/fcgi-bin/client_search_cp"
QQ_LYRIC_URL = "https://c.y.qq.com/lyric/fcgi-bin/fcg_query_lyric_new.fcg"
MEGALYRICS_URL = "http://api.megalyrics.net/xmlserver.php"
GECIMI_URL = "https://gecimi.com/api/lyric"
OVH_URL = "https://api.lyrics.ovh/v1"

# Metadata Cleaning
JUNK_KEYWORDS = [
    r'\(Official Music Video\)', r'\(Official Video\)', r'\(Official Audio\)',
    r'\(Lyric Video\)', r'\(Lyrics\)', r'\[HQ\]', r'\[HD\]', r'\[4K\]',
    r'\(Remastered\)', r'\(Live\)', r'\(Video\)', r'Official Music Video',
    r'Official Video', r'VEVO', r'- Topic',
    r'(?i)\bby\b', r'(?i)\bpar\b'
    r'(?i)\b8\s?bit\b', r'(?i)\barranged\s+by\b', r'(?i)\bperformed\s+by\b',
    r'(?i)\bft\b', r'(?i)\bfeat\b', r'(?i)\bversion\b', r'(?i)\bost\b',
    r'(?i)\bsoundtrack\b', r'(?i)\btheme\b', r'\(.*?\)', r'\[.*?\]'
]

# Junk Uploaders (The "stereomusicvideo" fix)
JUNK_UPLOADERS = ['vevo', 'official', 'records', 'music', 'video', 'stereo', 'channel', 'topic']

# Logging Levels:
# 0: OFF (Mute everything)
# 1: CRITICAL (Only system crashes)
# 2: ERROR (Download failures)
# 3: WARNING (Lyrics not found, blocked videos)
# 4: INFO (Standard progress, default)
# 5: DEBUG (FastSkip details, Registry Sync, internal logic)
LOG_LEVEL = 5
LOG_FILE = "debug.log"

# Metadata Keys
YTID_KEY = "----:com.apple.iTunes:YTID"

REGISTRY_FILE = ".registry.json"

# File Format
DOWNLOAD_VIDEO = False  # Set to True to download Video (MP4) instead of Audio (MP3)
AUDIO_FORMAT = "m4a"
VIDEO_FORMAT = "mp4"

# Logic helper
def get_extension():
    return VIDEO_FORMAT if DOWNLOAD_VIDEO else AUDIO_FORMAT

# Image Settings
IMAGE_SIZE = 600
IMAGE_QUALITY = 80
ITUNES_API_URL = "https://itunes.apple.com/search"

# Library Scan Settings
SKIP_LIBRARY_SCAN = False  # Set to True to skip the entire scan at the end
REPAIR_LYRICS = False       # Try to find missing .lrc/.srt files
REPAIR_COVERS = True       # Try to find missing embedded covers or cover.jp
