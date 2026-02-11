import os
import re
from mutagen.mp3 import MP3
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

def embed_lyrics(mp3_path, lyrics_text):
    """
    Embeds lyrics into MP3 ID3 tags.
    Uses v2.3 for maximum compatibility with VLC, Lollypop, and Android.
    """
    try:
        # Ensure the file exists
        if not os.path.exists(mp3_path):
            return False

        audio = MP3(mp3_path, ID3=ID3)
        
        # Create ID3 tags if they don't exist
        try:
            audio.add_tags()
        except:
            pass
            
        # 1. USLT (Unsynchronized lyrics) - Standard for most players
        audio.tags.add(
            USLT(
                encoding=Encoding.UTF8,
                lang='eng',
                desc='lyrics',
                text=lyrics_text
            )
        )
        
        # 2. TXXX:LYRICS - Specifically for Lollypop and some GNOME players
        audio.tags.add(
            TXXX(
                encoding=Encoding.UTF8,
                desc='LYRICS',
                text=lyrics_text
            )
        )
        
        # Save as ID3 v2.3
        audio.save(v2_version=3)
        return True
    except Exception as e:
        print(f"   - [FileProcessor] Embedding error: {e}")
        return False