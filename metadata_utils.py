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

    # 3. Sanitization (The "stereomusicvideo" fix)
    if any(junk in artist.lower() for junk in config.JUNK_UPLOADERS) and ' - ' in title:
        parts = re.split(r' [-–—|:] ', title, maxsplit=1)
        if len(parts) == 2:
            artist, title = parts[0], parts[1]

    return clean_metadata(artist), clean_metadata(title)

def parse_filename_robustly(filename):
    """Guesses Artist and Title from a filename for library scans."""
    name = os.path.splitext(filename)[0]
    
    # Try splitting by standard dash
    match = re.search(r'^(.*?) [-–—|] (.*)$', name)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    
    # Fallback for "Artist-Title"
    if "-" in name:
        parts = name.split("-")
        return parts[0].strip(), "-".join(parts[1:]).strip()
        
    return "Unknown", name