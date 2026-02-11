# music-dl

music-dl is an automated tool to build and manage a local music library. It takes a list of songs, downloads high-quality audio from YouTube, and automatically fetches synchronized lyrics from multiple international databases (LRCLIB, NetEase, QQ Music, and more).

It is designed to run inside Docker, ensuring it works perfectly on any machine without messing up your system dependencies.

## Features

*   **High-Quality Audio:** Downloads audio as MP3 (192kbps).
*   **Smart Metadata:** Automatically cleans titles (removes "Official Video", "4K", etc.) and detects the correct Artist and Title.
*   **Synchronized Lyrics:** Fetches time-synced lyrics (.lrc) from 6 different sources.
*   **Universal Compatibility:**
    *   **Embeds lyrics** directly into the MP3 (ID3 tags) for mobile players.
    *   **Generates .lrc files** for modern music players (Lollypop, Amberol).
    *   **Generates .srt files** so lyrics display automatically in VLC Media Player.
*   **Library Repair:** Scans your existing folder to find and fix missing lyrics for files you already downloaded.
*   **Folder Organization:** Automatically sorts music into subfolders based on your configuration.

## Prerequisites

You only need **Docker** installed on your machine.

*   **Ubuntu/Debian:** `sudo apt install docker.io`
*   **Fedora:** `sudo dnf install docker`
*   **Arch:** `sudo pacman -S docker`

*Note: You may need to run docker commands with `sudo` depending on your system configuration.*

## Installation

1.  Download or clone this repository to a folder on your computer.
2.  Open your terminal and navigate to that folder:
    ```bash
    cd path/to/music-dl
    ```

## Configuration: songs.txt

The `songs.txt` file is where you list the music you want to download. You can organize your library using a simple syntax.

### Syntax Guide

*   **Song Name:** Just type the artist and title (or a YouTube URL).
*   **Folders:** Use `#` to create a folder. Use `##` to create a subfolder inside the previous one.
*   **Comments:** Use `//` to add notes (the script ignores everything after `//`).

### Example `songs.txt`

```text
# Pop
Michael Jackson - Billie Jean
The Weeknd - Blinding Lights // This will be saved in downloads/Pop

# Rock
## Classic Rock
AC/DC - Back in Black
Queen - Bohemian Rhapsody // Saved in downloads/Rock/Classic Rock

## Alternative
Nirvana - Smells Like Teen Spirit // Saved in downloads/Rock/Alternative

# Soundtracks
Hans Zimmer - Time
```

### Resulting Directory Structure

```text
downloads/
├── Pop/
│   ├── Michael Jackson - Billie Jean.mp3
│   └── The Weeknd - Blinding Lights.mp3
├── Rock/
│   ├── Classic Rock/
│   │   ├── AC/DC - Back in Black.mp3
│   │   └── Queen - Bohemian Rhapsody.mp3
│   └── Alternative/
│       └── Nirvana - Smells Like Teen Spirit.mp3
└── Soundtracks/
    └── Hans Zimmer - Time.mp3
```

## Usage

To run the tool, use the following command in your terminal. This command builds the environment and runs the script in one go.

```bash
docker build -t music-dl . && docker run -it -v $(pwd)/downloads:/app/downloads music-dl
```

### Explanation of the command:
*   `docker build -t music-dl .`: Builds the tool.
*   `-v $(pwd)/downloads:/app/downloads`: This maps the `downloads` folder inside the container to the `downloads` folder on your actual computer. This ensures your music is saved to your hard drive, not lost inside Docker.

## Advanced Configuration

You can tweak internal settings by editing the `config.py` file.

### Logging / Debugging
If the script is crashing or behaving unexpectedly, you can enable logging to generate a detailed report.

1.  Open `config.py`.
2.  Change `ENABLE_LOGGING = False` to `ENABLE_LOGGING = True`.
3.  Run the script again.
4.  A file named `debug.log` will appear in your `downloads` folder. You can read this file to see exactly what happened.

### Metadata Cleaning
If you find that the script is not removing certain words from song titles (like "Official 4K Video"), you can add them to the `JUNK_KEYWORDS` list in `config.py`.

## Troubleshooting

### Permission Denied
If you get a "permission denied" error when running the docker command, use `sudo`:
```bash
sudo docker build -t music-dl . && sudo docker run -it -v $(pwd)/downloads:/app/downloads music-dl
```

### Lyrics not showing in VLC
VLC treats MP3s as audio, so it hides subtitles by default. To see lyrics:
1.  Play the song.
2.  Go to **Audio** > **Visualizations** > **Spectrometer** (or any visualization).
3.  Go to **Subtitle** > **Sub Track** > **Track 1**.

### Lyrics not showing in Lollypop/Gnome Music
Ensure you have refreshed your library. Lollypop sometimes requires a restart to read the new tags embedded in the MP3 files.

---
This project was vibe coded
