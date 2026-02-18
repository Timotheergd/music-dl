import re
import os
import config

def clean_metadata(text):
    """Removes junk keywords defined in config."""
    if not text:
        return ""
    for pattern in config.JUNK_KEYWORDS:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    # Remove extra spaces and trailing dashes
    text = re.sub(r'\s+', ' ', text).strip(' -–—|')
    return text

def extract_professional_metadata(info):
    """
    Heuristic extraction: Prioritizes Official Tags > Title Splitting.
    """
    # 1. Try official music tags
    artist = info.get('artist')
    title = info.get('track') or info.get('alt_title')

    # 2. If tags missing, parse the video title
    if not artist or not title:
        video_title = info.get('title', '')
        # Split by common delimiters
        parts = re.split(r' [-–—|:] ', video_title, maxsplit=1)
        if len(parts) == 2:
            artist, title = parts[0], parts[1]
        else:
            artist = info.get('uploader', 'Unknown')
            title = video_title

    # 3. Sanitization
    # If the artist is the uploader, and the title contains "artist - title", split it.
    if (" - " in title) and (artist.lower() in title.lower()):
        parts = re.split(r' [-–—|:] ', title, maxsplit=1)
        if len(parts) == 2:
            artist, title = parts[0], parts[1]

    return clean_metadata(artist), clean_metadata(title)

def parse_filename_robustly(filename):
    name = os.path.splitext(filename)[0]

    # 1. Try to split by common delimiters
    # We use a regex that looks for a dash surrounded by spaces, which is the standard
    parts = re.split(r' [-–—|] ', name)

    if len(parts) >= 2:
        # If there are multiple parts, assume the first is Artist, the rest is Title
        return parts[0].strip(), " ".join(parts[1:]).strip()

    # 2. Fallback: If no spaces around dash, try a raw dash but be careful
    if "-" in name:
        parts = name.split("-")
        if len(parts) == 2:
            return parts[0].strip(), parts[1].strip()

    # 3. No delimiters found
    return "Unknown", name
