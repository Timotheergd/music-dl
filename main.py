import os
import time
import config
import logger
import metadata_utils
import lyrics_engine
import downloader
import file_processor
from mutagen.mp3 import MP3
from mutagen.id3 import ID3

def extract_embedded_lyrics(mp3_path):
    """Helper to read USLT lyrics from an MP3 file."""
    try:
        audio = MP3(mp3_path, ID3=ID3)
        for key in audio.tags.keys():
            if key.startswith('USLT'):
                return audio.tags[key].text
    except: pass
    return None

def process_existing_library(engine):
    """
    Scans library RECURSIVELY (os.walk) to find missing lyrics in subfolders.
    """
    print("\n" + "="*40)
    print("SCANNING EXISTING LIBRARY (RECURSIVE)")
    print("="*40)

    if not os.path.exists(config.DOWNLOAD_DIR): return

    # Walk through all folders and subfolders
    for root, dirs, files in os.walk(config.DOWNLOAD_DIR):
        for filename in files:
            if not filename.endswith('.mp3'): continue

            base_name = os.path.splitext(filename)[0]
            mp3_path = os.path.join(root, filename)
            lrc_path = os.path.join(root, base_name + ".lrc")
            srt_path = os.path.join(root, base_name + ".srt")

            missing_lrc = not os.path.exists(lrc_path)
            missing_srt = not os.path.exists(srt_path)

            if missing_lrc or missing_srt:
                # ... (The rest of the scanning logic is identical to before) ...
                # ... (Copy the logic from previous main.py here) ...
                # For brevity, I will summarize the logic block:
                print(f"\n[Library Check]: {filename}")
                lyrics_text = None

                # 1. Check Local LRC
                if not missing_lrc:
                    try:
                        with open(lrc_path, "r", encoding="utf-8") as f: lyrics_text = f.read()
                    except: pass

                # 2. Check Embedded
                if not lyrics_text: lyrics_text = extract_embedded_lyrics(mp3_path)

                # 3. Search Online
                if not lyrics_text:
                    try:
                        audio = MP3(mp3_path, ID3=ID3)
                        artist = str(audio.get('TPE1', 'Unknown'))
                        title = str(audio.get('TIT2', 'Unknown'))
                        duration = int(audio.info.length)
                        if artist == "Unknown": artist, title = metadata_utils.parse_filename_robustly(filename)

                        lyrics_text = engine.search(artist, title, duration)
                        if lyrics_text: time.sleep(1.0)
                    except Exception as e: print(f"Error: {e}")

                # 4. Save
                if lyrics_text:
                    if missing_lrc:
                        with open(lrc_path, "w", encoding="utf-8") as f: f.write(lyrics_text)
                    if missing_srt:
                        srt = file_processor.lrc_to_srt(lyrics_text)
                        if srt:
                            with open(srt_path, "w", encoding="utf-8") as f: f.write(srt)
                    file_processor.embed_lyrics(mp3_path, lyrics_text)
                    print("   - Fixed missing lyrics.")

def parse_song_list(filepath):
    """
    Parses songs.txt with support for:
    - Comments (//)
    - Folder structure (#, ##)
    Returns a list of tuples: (song_query, target_folder_path)
    """
    tasks = []
    # Stack to keep track of nested folders
    # Example: ['Rock', 'Classic']
    folder_stack = []

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            # 1. Strip comments (//) and whitespace
            if '//' in line:
                line = line.split('//')[0]
            line = line.strip()

            if not line: continue

            # 2. Handle Folder Structure (#)
            if line.startswith('#'):
                # Count hashtags to determine depth (Level 1, 2, etc.)
                depth = len(line) - len(line.lstrip('#'))
                folder_name = line.lstrip('#').strip()

                # Adjust stack based on depth
                # If depth is 1, we clear stack and start new
                # If depth is 2, we keep the first parent
                # Logic: Keep the first (depth-1) items
                folder_stack = folder_stack[:depth-1]
                folder_stack.append(folder_name)

            # 3. Handle Song
            else:
                # Construct full path based on current stack
                # If stack is empty, it goes to root DOWNLOAD_DIR
                if folder_stack:
                    target_path = os.path.join(config.DOWNLOAD_DIR, *folder_stack)
                else:
                    target_path = config.DOWNLOAD_DIR

                tasks.append((line, target_path))

    return tasks

def main():

    # Setup Logging
    logger.setup()

    # Ensure download directory exists
    if not os.path.exists(config.DOWNLOAD_DIR): os.makedirs(config.DOWNLOAD_DIR)

    engine = lyrics_engine.LyricsEngine()
    dl = downloader.Downloader(engine)

    # 1. Parse the structured song list
    if os.path.exists(config.SONG_LIST):
        tasks = parse_song_list(config.SONG_LIST)
        print(f"Found {len(tasks)} items to process.")

        for query, target_folder in tasks:
            # Pass the specific folder to the downloader
            dl.process_query(query, target_folder)
            time.sleep(2)
    else:
        print(f"Warning: {config.SONG_LIST} not found.")

    # 2. Scan library (Recursive)
    process_existing_library(engine)

    print("\n" + "="*40)
    print("ALL TASKS COMPLETE")
    print("="*40)

if __name__ == "__main__":
    main()
