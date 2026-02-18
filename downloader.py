import os
import time
import yt_dlp
import config
import metadata_utils
import file_processor
import logger
import cover_engine
import re
import copy

class Downloader:
    def __init__(self, lyrics_engine, registry, existing_ids):
        self.lyrics_engine = lyrics_engine
        self.registry = registry
        self.existing_ids = existing_ids
        self.cover_engine = cover_engine.CoverEngine()

        self.base_opts = {
            'noplaylist': False,
            'ignoreerrors': True,
            'extract_flat': 'in_playlist',
            'quiet': True,
            'no_warnings': True,
        }

    def _get_opts_for_format(self, fmt, output_path):
        """Generates yt-dlp options for a specific format (audio/video)."""
        opts = self.base_opts.copy()
        opts['outtmpl'] = f'{output_path}/%(title)s.%(ext)s'

        if fmt == config.VIDEO_FORMAT:
            opts['format'] = 'bestvideo+bestaudio/best'
            opts['merge_output_format'] = 'mp4'
        else:
            # Audio (m4a)
            opts['format'] = 'bestaudio[ext=m4a]/bestaudio/best'
            opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'm4a',
            }]
        return opts

    def _extract_id_from_url(self, url):
        """Extracts the 11-char ID without hitting the network."""
        pattern = r"(?:v=|\/)([0-9A-Za-z_-]{11}).*"
        match = re.search(pattern, url)
        return match.group(1) if match else None

    def _is_playlist(self, query):
        """Checks if the query is a YouTube playlist."""
        return "list=" in query.lower()

    def process_query(self, query, target_folder=None, override_mode=None):
        """
        Handles a single URL/Search.
        target_folder: The specific subfolder (e.g. /app/downloads/Rock)
        override_mode: 'audio', 'video', or 'both'
        """
        # 1. INSTANT CHECK (Skip ONLY if NOT a playlist)
        if not self._is_playlist(query):
            if self.registry.is_downloaded(query):
                logger.log(5, f"   - [FastSkip] Query '{query}' already in registry.")
                return

            if query.startswith('http'):
                ytid = self._extract_id_from_url(query)
                if ytid and self.registry.is_downloaded(ytid):
                    logger.log(5, f"   - [FastSkip] ID {ytid} already in registry.")
                    return

        logger.log(4, f"\n[Downloader] Processing: {query}")

        # 2. Determine Output Path
        output_path = target_folder if target_folder else config.DOWNLOAD_DIR
        if not os.path.exists(output_path):
            os.makedirs(output_path)

        search_query = query if query.startswith('http') else f"ytsearch1:{query}"

        # 3. Initial Scan (Use base options just to get the list)
        with yt_dlp.YoutubeDL(self.base_opts) as ydl:
            try:
                info = ydl.extract_info(search_query, download=False)
                if not info:
                    logger.log(3, f"   - Could not access: {query}")
                    return

                video_list = info['entries'] if 'entries' in info else [info]
                logger.log(4, f"   - Found {len(video_list)} potential track(s).")

                for entry in video_list:
                    if not entry: continue

                    # Availability Check
                    title = entry.get('title', '')
                    if title in ['[Private video]', '[Deleted video]', None]:
                        continue

                    # Fast Skip Check (RAM/Registry)
                    ytid = entry.get('id')
                    if ytid and (ytid in self.existing_ids or self.registry.is_downloaded(ytid)):
                        continue

                    # Process Track (Returns True if download happened)
                    # We pass 'ydl' but it won't be used for download, only for metadata if needed
                    did_download = self._download_and_process_track(ydl, entry, query, output_path, override_mode)

                    if did_download:
                        time.sleep(1)

            except Exception as e:
                logger.log(2, f"   - Critical Downloader Error: {e}")

    def _download_and_process_track(self, ydl_unused, entry, original_query, output_path, override_mode=None):
        """
        Internal method.
        Handles Audio, Video, or Both based on config.
        """
        try:
            ytid = entry.get('id')
            if not ytid: return False

            # 1. Determine what we need to download
            needed_exts = config.get_extensions(override_mode)
            download_occurred = False

            # 2. Fetch Metadata (Once for all formats)
            video_url = entry.get('webpage_url') or entry.get('url') or f"https://www.youtube.com/watch?v={ytid}"

            logger.log(5, f"   - [Network] Fetching metadata: {ytid}")

            # Use a temporary YDL instance just for metadata extraction
            with yt_dlp.YoutubeDL(self.base_opts) as meta_ydl:
                video = meta_ydl.extract_info(video_url, download=False)

            if not video: return False

            artist, title = metadata_utils.extract_professional_metadata(video)
            duration = video.get('duration', 0)
            album = video.get('album', 'Unknown')
            yt_thumb = video.get('thumbnail')

            # 3. Loop through required formats (Audio, Video, or Both)
            for ext in needed_exts:
                # Create specific options for this format
                fmt_opts = self._get_opts_for_format(ext, output_path)

                # Create a clean copy of metadata for this iteration
                # This prevents 'yt-dlp' from polluting the dictionary with state
                # from the previous format (e.g. m4a download affecting mp4 logic)
                video_copy = copy.deepcopy(video)

                # Prepare filename
                with yt_dlp.YoutubeDL(fmt_opts) as fmt_ydl:
                    # Use video_copy here
                    temp_filename = fmt_ydl.prepare_filename(video_copy)
                    final_file = os.path.splitext(temp_filename)[0] + f".{ext}"

                    # Disk Check
                    if os.path.exists(final_file):
                        continue

                    # DOWNLOAD
                    logger.log(4, f"   - Downloading ({ext}): {artist} - {title}")
                    # Use video_copy here
                    fmt_ydl.process_info(video_copy)
                    download_occurred = True

                    # POST-PROCESS (Lyrics/Cover)
                    lyrics = self.lyrics_engine.search(artist, title, duration)
                    cover_data = self.cover_engine.get_cover(artist, title, album, output_path, yt_thumb)

                    # Embed (Function handles extension check internally)
                    file_processor.embed_metadata(final_file, lyrics=lyrics, ytid=ytid, cover_data=cover_data)

                    # Save sidecars (LRC/SRT)
                    if lyrics:
                        base_path = os.path.splitext(final_file)[0]
                        with open(f"{base_path}.lrc", "w", encoding="utf-8") as f: f.write(lyrics)
                        srt = file_processor.lrc_to_srt(lyrics)
                        if srt:
                            with open(f"{base_path}.srt", "w", encoding="utf-8") as f: f.write(srt)

            # 4. Finalize
            if download_occurred:
                self.existing_ids.add(ytid)
                if self._is_playlist(original_query):
                    self.registry.add(ytid, ytid)
                else:
                    self.registry.add(original_query, ytid)
                self.registry.save()
                return True

            return False

        except Exception as e:
            logger.log(2, f"   - Track Error: {e}")
            return False
