import os
import time
import yt_dlp
import config
import metadata_utils
import file_processor

class Downloader:
    def __init__(self, lyrics_engine):
        self.lyrics_engine = lyrics_engine
        # Base options common to both modes
        self.base_opts = {
            'noplaylist': False,
            'ignoreerrors': True,
            'extract_flat': 'in_playlist',
            'quiet': True,
            'no_warnings': True,
        }

        # Mode-specific options
        if config.DOWNLOAD_VIDEO:
            self.mode_opts = {
                'format': 'bestvideo+bestaudio/best', # Best quality
                'merge_output_format': 'mp4',         # Ensure compatibility
                'outtmpl': f'{config.DOWNLOAD_DIR}/%(title)s.%(ext)s',
            }
        else:
            self.mode_opts = {
                'format': 'bestaudio/best',
                'outtmpl': f'{config.DOWNLOAD_DIR}/%(title)s.%(ext)s',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            }

        # Merge options
        self.ydl_opts = {**self.base_opts, **self.mode_opts}

    def process_query(self, query, target_folder=None):
        """
        Handles a single URL/Search.
        target_folder: The specific subfolder (e.g. /app/downloads/Rock)
        """
        print(f"\n[Downloader] Processing: {query}")

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
                    print(f"   - Could not access: {query}")
                    return

                video_list = info['entries'] if 'entries' in info else [info]
                print(f"   - Found {len(video_list)} potential track(s).")

                for entry in video_list:
                    if not entry: continue
                    self._download_and_process_track(ydl, entry)
                    time.sleep(1.5)

            except Exception as e:
                print(f"   - Critical Downloader Error: {e}")

    def _download_and_process_track(self, ydl, entry):
        """Internal method to handle a single track's lifecycle."""
        try:
            # FIX: Robustly get the URL or ID to extract full metadata
            # Search results have 'url', direct links have 'webpage_url' or 'id'
            video_url = entry.get('webpage_url') or entry.get('url')

            if not video_url:
                # Fallback: Construct URL from ID if possible
                if entry.get('id'):
                    video_url = f"https://www.youtube.com/watch?v={entry['id']}"
                else:
                    print(f"   - Error: Could not determine video URL.")
                    return

            # Fetch full metadata (needed because of extract_flat)
            video = ydl.extract_info(video_url, download=False)
            if not video: return

            # Expert-tier metadata extraction
            artist, title = metadata_utils.extract_professional_metadata(video)
            duration = video.get('duration', 0)

            # Determine expected extension based on config
            target_ext = "mp4" if config.DOWNLOAD_VIDEO else "mp3"

            # Check if file already exists
            temp_filename = ydl.prepare_filename(video)
            # yt-dlp might return .webm/.mkv, so we strip extension and add ours
            final_file = os.path.splitext(temp_filename)[0] + f".{target_ext}"

            if os.path.exists(final_file):
                print(f"   - Skipping: '{os.path.basename(final_file)}' already exists.")
                return

            # Actual Download
            print(f"   - Downloading: {artist} - {title}")
            ydl.process_info(video)

            # Lyrics Retrieval
            lyrics = self.lyrics_engine.search(artist, title, duration)
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
                    print(f"   - Success: Audio and Lyrics processed.")
                else:
                    print(f"   - Success: Video downloaded. Lyrics saved externally.")
            else:
                print(f"   - No lyrics found for: {title}")

        except Exception as e:
            print(f"   - Track Error: {e}")
