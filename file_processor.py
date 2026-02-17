import os
import re
import config
import logger
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4, MP4Cover
from mutagen.id3 import ID3, USLT, TXXX, Encoding

def lrc_to_srt(lrc_text):
    """
    Converts LRC format to SRT format.
    Essential for VLC to display lyrics automatically.
    """
    if not lrc_text:
        return ""

    lines = lrc_text.splitlines()
    srt_output = []
    index = 1

    # Regex to find [mm:ss.xx] or [mm:ss:xxx]
    pattern = re.compile(r'\[(\d+):(\d+\.\d+)\](.*)')

    parsed_lines = []
    for line in lines:
        match = pattern.match(line)
        if match:
            minutes = int(match.group(1))
            seconds = float(match.group(2))
            text = match.group(3).strip()
            if not text: continue # Skip empty lyric lines

            total_seconds = (minutes * 60) + seconds
            parsed_lines.append((total_seconds, text))

    if not parsed_lines:
        return ""

    for i in range(len(parsed_lines)):
        start_time = parsed_lines[i][0]
        # End time is the start of the next line, or start + 4 seconds if last line
        end_time = parsed_lines[i+1][0] if i+1 < len(parsed_lines) else start_time + 4

        def format_time(seconds):
            msec = int((seconds % 1) * 1000)
            td_sec = int(seconds % 60)
            td_min = int((seconds // 60) % 60)
            td_hr = int(seconds // 3600)
            return f"{td_hr:02}:{td_min:02}:{td_sec:02},{msec:03}"

        srt_output.append(f"{index}")
        srt_output.append(f"{format_time(start_time)} --> {format_time(end_time)}")
        srt_output.append(parsed_lines[i][1])
        srt_output.append("")
        index += 1

    return "\n".join(srt_output)

def embed_lyrics(file_path, lyrics_text):
    """
    Embeds lyrics into M4A (AAC) files using iTunes-style metadata.
    """
    try:
        if not os.path.exists(file_path):
            return False

        audio = MP4(file_path)

        # M4A uses specific atom names for lyrics
        # '©lyr' is the standard Unsynchronized Lyrics tag
        audio['\xa9lyr'] = lyrics_text

        # Some players look for a custom 'LYRICS' atom
        # We add it as a freeform atom just in case
        audio['----:com.apple.iTunes:LYRICS'] = lyrics_text.encode('utf-8')

        audio.save()
        return True
    except Exception as e:
        logger.log(2, f"   - [FileProcessor] Embedding error: {e}")
        return False

def embed_metadata(file_path, lyrics=None, ytid=None):
    """Generic M4A metadata embedder."""
    try:
        # Prevent trying to embed in MP4 videos (Mutagen MP4 is for audio containers)
        if file_path.endswith(".mp4") and config.DOWNLOAD_VIDEO:
            return False

        audio = MP4(file_path)
        if lyrics:
            audio['\xa9lyr'] = lyrics
        if ytid:
            audio[config.YTID_KEY] = ytid.encode('utf-8')
        audio.save()
        return True
    except Exception as e:
        logger.log(2, f"   - [FileProcessor] Metadata error: {e}")
        return False

def extract_ytid(file_path):
    """Reads the hidden YouTube ID from an M4A file."""
    try:
        audio = MP4(file_path)
        if config.YTID_KEY in audio:
            return audio[config.YTID_KEY][0].decode('utf-8')
    except:
        pass
    return None
