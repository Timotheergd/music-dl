import os
import time
import config
import logger
import metadata_utils
import lyrics_engine
import downloader
import file_processor
import registry
import cover_engine
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
    logger.log(4, "Indexing existing library by ID...")
    id_set = set()
    ext = f".{config.AUDIO_FORMAT}"
    for root, dirs, files in os.walk(config.DOWNLOAD_DIR):
        for f in files:
            if f.endswith(ext):
                ytid = file_processor.extract_ytid(os.path.join(root, f))
                if ytid: id_set.add(ytid)
    logger.log(4, f"Index complete. {len(id_set)} unique IDs found.")
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

    if config.SKIP_LIBRARY_SCAN:
        logger.log(4, "Skipping library scan as per config.")
        return

    logger.log(4, "\n" + "="*40)
    logger.log(4, "SCANNING EXISTING LIBRARY")
    logger.log(4, "="*40)

    if not os.path.exists(config.DOWNLOAD_DIR):
        return

    # Initialize cover engine for repairs
    c_engine = cover_engine.CoverEngine()

    # Determine which extensions to scan
    # If "both", we scan both. If "video", we scan mp4.
    target_exts = config.get_extensions()

    # Walk through all folders and subfolders
    ext = f".{config.AUDIO_FORMAT}"
    for root, dirs, files in os.walk(config.DOWNLOAD_DIR):
        for filename in files:

            # Check if file matches ANY of our target extensions
            if not any(filename.endswith(f".{ext}") for ext in target_exts):
                continue

            base_name = os.path.splitext(filename)[0]
            audio_path = os.path.join(root, filename)

            if config.REPAIR_LYRICS:
                lrc_path = os.path.join(root, base_name + ".lrc")
                srt_path = os.path.join(root, base_name + ".srt")

                # Check if anything is missing
                missing_lrc = not os.path.exists(lrc_path)
                missing_srt = not os.path.exists(srt_path)

                if missing_lrc or missing_srt:
                    logger.log(4, f"\n[Library Check]: {filename}")
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

                            logger.log(3, f"   - Lyrics missing locally. Searching online...")
                            lyrics_text = engine.search(artist, title, duration)
                            if lyrics_text:
                                source = "Online Search"
                                time.sleep(1.0) # API Cooldown
                        except Exception as e:
                            logger.log(2, f"   - Error reading M4A metadata: {e}")

                    # 4. Finalize: Write whatever is missing
                    if lyrics_text:
                        logger.log(4, f"   - Found lyrics via: {source}")

                        # Write LRC if missing
                        if missing_lrc:
                            with open(lrc_path, "w", encoding="utf-8") as f:
                                f.write(lyrics_text)
                            logger.log(4, "   - Generated missing .lrc file")

                        # Write SRT if missing
                        if missing_srt:
                            srt_content = file_processor.lrc_to_srt(lyrics_text)
                            if srt_content:
                                with open(srt_path, "w", encoding="utf-8") as f:
                                    f.write(srt_content)
                                logger.log(4, "   - Generated missing .srt file")

                        # Always re-embed to ensure compatibility
                        file_processor.embed_lyrics(audio_path, lyrics_text)
                    else:
                        logger.log(3, f"   - Still no lyrics found. for {title}-{artist}")

            # --- 2. COVER REPAIR ---
            if config.REPAIR_COVERS:

                # OPTION A: WIPE ONLY (Use this to clean your library)
                # logger.log(3, f"   - Wiping cover for: {filename}")
                # file_processor.remove_embedded_cover(audio_path)
                # continue # Skip to next song, do not repair yet

                # OPTION B: REPAIR (Use this after you have wiped and fixed the code)
                if not file_processor.has_cover(audio_path):
                    logger.log(4, f"[Repair Cover]: {filename}")
                    try:
                        audio = MP4(audio_path)
                        # 1. Try tags
                        artist = audio.get('\xa9ART', ['Unknown'])[0]
                        title = audio.get('\xa9nam', ['Unknown'])[0]
                        album = audio.get('\xa9alb', ['Unknown'])[0]

                        # 1. Filename Parsing Fallback
                        if artist.lower() == "unknown" or len(artist) < 2:
                            artist, title = metadata_utils.parse_filename_robustly(filename)

                        # 2. Final Clean
                        artist = metadata_utils.clean_metadata(artist)
                        title = metadata_utils.clean_metadata(title)

                        # 3. SPECIAL CASE: If artist is STILL unknown,
                        # we swap them if the "Title" looks like "Artist - Song"
                        # But for now, we rely on the Relaxed Search in Cover Engine

                        logger.log(5, f"   - Searching for: {artist} - {title}")

                        # Pass 'None' for yt_thumb_url because we are offline repairing
                        cover_data = c_engine.get_cover(artist, title, album, root, None)

                        if cover_data and len(cover_data) > 500:
                            file_processor.embed_metadata(audio_path, cover_data=cover_data)
                            logger.log(4, f"   - Success: Fixed cover for {title}")
                        else:
                            logger.log(3, f"   - Failed: No cover found for '{artist} - {title}'")
                    except Exception as e:
                        logger.log(2, f"   - Error processing {filename}: {e}")

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
            logger.log(4, f"Found {len(tasks)} items to process.")
            for query, target_folder in tasks:
                dl.process_query(query, target_folder)
        else:
            logger.log(3, f"{config.SONG_LIST} is empty.")
    else:
        # This will now ONLY print if the file is missing
        logger.log(3, f"Warning: {config.SONG_LIST} not found.")

    # Run Repair Scan
    if not config.SKIP_LIBRARY_SCAN:
        process_existing_library(engine)
    else:
        logger.log(4, "\nLibrary scan skipped (Config).")

    logger.log(4, "\n" + "="*40)
    logger.log(4, "ALL TASKS COMPLETE")
    logger.log(4, "="*40)

if __name__ == "__main__":
    main()
