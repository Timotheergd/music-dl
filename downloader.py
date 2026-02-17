import os
import time
import yt_dlp
import config
import metadata_utils
import file_processor
import logger
import cover_engine
import re

class Downloader:
    def __init__(self, lyrics_engine, registry, existing_ids):
        self.lyrics_engine = lyrics_engine
        self.registry = registry
        self.existing_ids = existing_ids

        self.base_opts = {
            'noplaylist': False,
            'ignoreerrors': True,
            'extract_flat': 'in_playlist',
            'quiet': True,
            'no_warnings': True,
        }

        if config.DOWNLOAD_VIDEO:
            self.mode_opts = {
                'format': 'bestvideo+bestaudio/best',
                'merge_output_format': 'mp4',
                'outtmpl': f'{config.DOWNLOAD_DIR}/%(title)s.%(ext)s',
            }
        else:
            # AUDIO MODE (M4A)
            self.mode_opts = {
                'format': 'bestaudio[ext=m4a]/bestaudio/best', # Prefer native M4A
                'outtmpl': f'{config.DOWNLOAD_DIR}/%(title)s.%(ext)s',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'm4a', # Ensure container is M4A
                }],
            }

        self.ydl_opts = {**self.base_opts, **self.mode_opts}
        self.cover_engine = cover_engine.CoverEngine()

    def _extract_id_from_url(self, url):
        """Extracts the 11-char ID without hitting the network."""
        pattern = r"(?:v=|\/)([0-9A-Za-z_-]{11}).*"
        match = re.search(pattern, url)
        return match.group(1) if match else None

    def _is_playlist(self, query):
        """Checks if the query is a YouTube playlist."""
        return "list=" in query.lower()

    def process_query(self, query, target_folder=None):
        """
        Handles a single URL/Search.
        target_folder: The specific subfolder (e.g. /app/downloads/Rock)
        """
        # 1. INSTANT CHECK: Registry
        # If the exact text "Adele - Hello" or the URL is in our JSON, skip now.
        if self.registry.is_downloaded(query):
            logger.log(4, f"   - [FastSkip] Query '{query}' already in registry.")
            return

        # 2. INSTANT CHECK: URL Regex
        if query.startswith('http'):
            ytid = self._extract_id_from_url(query)
            if ytid and self.registry.is_downloaded(query, ytid):
                logger.log(5, f"   - [FastSkip] ID {ytid} already in registry.")
                return

        # 3. NETWORK CALL (Only if the two checks above fail)
        logger.log(4, f"\n[Downloader] Processing: {query}")

        # 1. Determine Output Path
        # If main.py sent a folder, use it. Otherwise use default.
        output_path = target_folder if target_folder else config.DOWNLOAD_DIR

        # Ensure the folder exists
        if not os.path.exists(output_path):
            os.makedirs(output_path)

        # 2. Create a copy of options and update the path
        # We must do this so we don't permanently change the default options
        current_opts = self.ydl_opts.copy()
        current_opts['outtmpl'] = f'{output_path}/%(title)s.%(ext)s'

        search_query = query if query.startswith('http') else f"ytsearch1:{query}"

        # Use 'current_opts' instead of 'self.ydl_opts'
        with yt_dlp.YoutubeDL(current_opts) as ydl:
            try:
                # ... (The rest of the logic is identical to before) ...
                # Just ensure you use 'ydl' which is now initialized with 'current_opts'

                info = ydl.extract_info(search_query, download=False)
                if not info:
                    logger.log(3, f"   - Could not access: {query}")
                    return

                video_list = info['entries'] if 'entries' in info else [info]
                logger.log(4, f"   - Found {len(video_list)} potential track(s).")

                for entry in video_list:
                    if not entry: continue

                    # 1. Availability Check
                    title = entry.get('title', '')
                    if title in ['[Private video]', '[Deleted video]', None]:
                        continue

                    # 2. THE FAST SKIP (The Fix)
                    ytid = entry.get('id')

                    # We check three things in order of speed:
                    # - Is it in RAM (Disk Index)?
                    # - Is it in the Registry by its ID?
                    if ytid and (ytid in self.existing_ids or self.registry.is_downloaded(ytid)):
                        continue

                    # 3. Process only if not skipped
                    self._download_and_process_track(ydl, entry, query, output_path)
                    time.sleep(1)
            except Exception as e:
                logger.log(2, f"   - Track Error: {e}")

    def _download_and_process_track(self, ydl, entry, original_query, output_path):
        """Internal method to handle a single track's lifecycle."""
        try:
            ytid = entry.get('id')
            if not ytid: return

            # 1. Check RAM/Registry (Instant)
            if ytid in self.existing_ids or self.registry.is_downloaded(original_query, ytid):
                return

            # 2. Check Disk (Instant - No Network)
            # We use prepare_filename on the 'entry' (flat data)
            target_ext = config.get_extension()
            temp_filename = ydl.prepare_filename(entry)
            final_file = os.path.splitext(temp_filename)[0] + f".{target_ext}"

            if os.path.exists(final_file):
                # Update our indexes so we skip even faster next time
                self.existing_ids.add(ytid)
                self.registry.add(original_query, ytid)
                self.registry.save()
                return # SKIP NOW before calling extract_info

            # 3. NETWORK CALL (Only reached if file does NOT exist on disk)
            logger.log(4, f"   - [Network] Fetching metadata: {ytid}")
            video_url = entry.get('webpage_url') or entry.get('url') or f"https://www.youtube.com/watch?v={ytid}"
            video = ydl.extract_info(video_url, download=False)

            if not video_url:
                # Fallback: Construct URL from ID if possible
                if entry.get('id'):
                    video_url = f"https://www.youtube.com/watch?v={entry['id']}"
                else:
                    logger.log(2, f"   - Error: Could not determine video URL.{video_url}")
                    return

            # Fetch full metadata (needed because of extract_flat)
            video = ydl.extract_info(video_url, download=False)
            if not video: return

            # Expert-tier metadata extraction
            artist, title = metadata_utils.extract_professional_metadata(video)
            duration = video.get('duration', 0)

            # Use generic extensions from config
            target_ext = config.get_extension()

            temp_filename = ydl.prepare_filename(video)
            final_file = os.path.splitext(temp_filename)[0] + f".{target_ext}"

            if os.path.exists(final_file):
                logger.log(4, f"   - Skipping: '{os.path.basename(final_file)}' already exists.")
                return

            # Actual Download
            logger.log(4, f"   - Downloading: {artist} - {title}")
            ydl.process_info(video)

            album = video.get('album', 'Unknown')
            yt_thumb = video.get('thumbnail')

            cover_data = self.cover_engine.get_cover(artist, title, album, output_path, yt_thumb)

            # Lyrics Retrieval
            lyrics = self.lyrics_engine.search(artist, title, duration)

            # Embed both Lyrics (if found) AND the YTID
            file_processor.embed_metadata(final_file, lyrics=lyrics, ytid=ytid, cover_data=cover_data)

            # Add to master list so we don't download it twice in the same session
            self.existing_ids.add(ytid)

            if lyrics:
                base_path = os.path.splitext(final_file)[0]

                # Save LRC
                with open(f"{base_path}.lrc", "w", encoding="utf-8") as f:
                    f.write(lyrics)

                # Save SRT
                srt_content = file_processor.lrc_to_srt(lyrics)
                if srt_content:
                    with open(f"{base_path}.srt", "w", encoding="utf-8") as f:
                        f.write(srt_content)

                # Embed (Audio Only)
                if not config.DOWNLOAD_VIDEO:
                    file_processor.embed_lyrics(final_file, lyrics)
                    logger.log(4, f"   - Success: Audio and Lyrics processed.")
                else:
                    logger.log(4, f"   - Success: Video downloaded. Lyrics saved externally.")
            else:
                logger.log(3, f"   - No lyrics found for: {title}")

            # 4. Update Registry
            if self._is_playlist(original_query):
                # For playlists, we register the ID as the key
                # This ensures the skip check in process_query works instantly
                self.registry.add(ytid, ytid)
            else:
                # For single songs, we register both the search string and the ID
                self.registry.add(original_query, ytid)

            self.existing_ids.add(ytid)
            self.registry.save()

            # Extract Album Name (Used for cache fingerprinting)
            album = video.get('album', 'Unknown')
            yt_thumb = video.get('thumbnail')

            # Get Cover
            cover_data = self.cover_engine.get_cover(artist, title, album, output_path, yt_thumb)

            # Embed everything
            file_processor.embed_metadata(final_file, lyrics=lyrics, ytid=ytid, cover_data=cover_data)

        except Exception as e:
            logger.log(2, f"   - Track Error: {e}")
