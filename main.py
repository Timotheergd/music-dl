import os
import time
import config
import logger
import metadata_utils
import lyrics_engine
import downloader
import file_processor
import registry
from mutagen.mp4 import MP4  # Ensure this is at the top of main.py

def extract_embedded_lyrics(audio_path):
    """Generic helper to read lyrics from M4A atoms."""
    try:
        audio = MP4(audio_path)
        if '\xa9lyr' in audio:
            return audio['\xa9lyr'][0]
    except: pass
    return None

def build_id_index():
    print("Indexing existing library by ID...")
    id_set = set()
    ext = f".{config.AUDIO_FORMAT}"
    for root, dirs, files in os.walk(config.DOWNLOAD_DIR):
        for f in files:
            if f.endswith(ext):
                ytid = file_processor.extract_ytid(os.path.join(root, f))
                if ytid: id_set.add(ytid)
    print(f"Index complete. {len(id_set)} unique IDs found.")
    return id_set


def process_existing_library(engine):
    """
    Scans library RECURSIVELY for M4A files.
    Priority:
    1. Use existing .lrc file
    2. Use embedded M4A tags (©lyr)
    3. Search Online
    Then ensures .lrc, .srt, and embedded tags all exist.
    """
    print("\n" + "="*40)
    print("SCANNING EXISTING LIBRARY (M4A)")
    print("="*40)

    if not os.path.exists(config.DOWNLOAD_DIR):
        return

    # Walk through all folders and subfolders
    ext = f".{config.AUDIO_FORMAT}"
    for root, dirs, files in os.walk(config.DOWNLOAD_DIR):
        for filename in files:
            if not filename.endswith(ext): continue

            base_name = os.path.splitext(filename)[0]
            audio_path = os.path.join(root, filename)
            lrc_path = os.path.join(root, base_name + ".lrc")
            srt_path = os.path.join(root, base_name + ".srt")

            # Check if anything is missing
            missing_lrc = not os.path.exists(lrc_path)
            missing_srt = not os.path.exists(srt_path)

            if missing_lrc or missing_srt:
                print(f"\n[Library Check]: {filename}")
                lyrics_text = None
                source = "Unknown"

                # 1. Try to read from existing .lrc file
                if not missing_lrc:
                    try:
                        with open(lrc_path, "r", encoding="utf-8") as f:
                            lyrics_text = f.read()
                        source = "Local .lrc file"
                    except: pass

                # 2. If no .lrc, try to read from Embedded M4A Tags
                if not lyrics_text:
                    try:
                        audio = MP4(audio_path)
                        # \xa9lyr is the iTunes atom for lyrics
                        if '\xa9lyr' in audio:
                            lyrics_text = audio['\xa9lyr'][0]
                            source = "Embedded M4A Tags"
                    except: pass

                # 3. If still nothing, Search Online
                if not lyrics_text:
                    try:
                        audio = MP4(audio_path)
                        artist = audio.get('\xa9ART', ['Unknown'])[0]
                        title = audio.get('\xa9nam', ['Unknown'])[0]
                        duration = int(audio.info.length)

                        # Fallback to filename if tags are generic
                        if artist == "Unknown" or title == "Unknown":
                            artist, title = metadata_utils.parse_filename_robustly(filename)

                        print(f"   - Lyrics missing locally. Searching online...")
                        lyrics_text = engine.search(artist, title, duration)
                        if lyrics_text:
                            source = "Online Search"
                            time.sleep(1.0) # API Cooldown
                    except Exception as e:
                        print(f"   - Error reading M4A metadata: {e}")

                # 4. Finalize: Write whatever is missing
                if lyrics_text:
                    print(f"   - Found lyrics via: {source}")

                    # Write LRC if missing
                    if missing_lrc:
                        with open(lrc_path, "w", encoding="utf-8") as f:
                            f.write(lyrics_text)
                        print("   - Generated missing .lrc file")

                    # Write SRT if missing
                    if missing_srt:
                        srt_content = file_processor.lrc_to_srt(lyrics_text)
                        if srt_content:
                            with open(srt_path, "w", encoding="utf-8") as f:
                                f.write(srt_content)
                            print("   - Generated missing .srt file")

                    # Always re-embed to ensure compatibility
                    file_processor.embed_lyrics(audio_path, lyrics_text)
                else:
                    print("   - Still no lyrics found.")

def parse_song_list(filepath):
    """
    Parses songs.txt with support for:
    - Comments (//) ONLY if preceded by whitespace or at start
    - Folder structure (#, ##)
    Returns a list of tuples: (song_query, target_folder_path)
    """
    tasks = []
    folder_stack = []

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            # 1. Smart Comment Stripping
            # We only split if we see " //" (space before) or if the line starts with "//"
            # This preserves "https://..." links
            if ' // ' in line:
                line = line.split(' // ')[0]
            elif line.strip().startswith('//'):
                continue

            line = line.strip()
            if not line: continue

            # 2. Handle Folder Structure (#)
            if line.startswith('#'):
                depth = len(line) - len(line.lstrip('#'))
                folder_name = line.lstrip('#').strip()
                folder_stack = folder_stack[:depth-1]
                folder_stack.append(folder_name)

            # 3. Handle Song
            else:
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

    # Build the RAM index (Scans existing files)
    existing_ids = build_id_index()

    # Load Registry (Instant)
    reg = registry.Registry()

    # Sync Registry with Disk
    # This removes "phantom" entries for deleted files
    reg.sync_with_disk(existing_ids)

    # Initialize Engines
    engine = lyrics_engine.LyricsEngine()
    dl = downloader.Downloader(engine, reg, existing_ids)

    # Process the structured song list
    if os.path.exists(config.SONG_LIST):
        tasks = parse_song_list(config.SONG_LIST)
        if tasks:
            print(f"Found {len(tasks)} items to process.")
            for query, target_folder in tasks:
                dl.process_query(query, target_folder)
        else:
            print(f"{config.SONG_LIST} is empty.")
    else:
        # This will now ONLY print if the file is missing
        print(f"Warning: {config.SONG_LIST} not found.")

    # Scan library (Recursive)
    process_existing_library(engine)

    print("\n" + "="*40)
    print("ALL TASKS COMPLETE")
    print("="*40)

if __name__ == "__main__":
    main()
