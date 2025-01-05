# YouTube Shorts Bot

A Python pipeline developed as part of a **Software Engineering** project at **Bocconi University**, which:

1. **Downloads** a YouTube video
2. **Transcribes** audio (via official transcripts, Whisper, Vosk, or AssemblyAI)
3. **Detects Scenes** using FFmpeg-based scene detection
4. **Renders** short vertical clips (9:16) with background “brainrot” footage (like Subway Surfers) and timed subtitles
5. **Uploads** the resulting clips to YouTube as Shorts

---

## Features

- **Multiple Transcribers**: Choose from `whisper`, `vosk`, or `assemblyai` in` utils/config.py`.
- **Automated Scene Splitting**: Scenes under 20 seconds are merged; scenes over 60 seconds are split, to adhere to YouTube Shorts format standards.
- **Brainrot Footage**: The final 9:16 video has the main subclip on top and a random video game clip (Temple Run, Subway Surfers, Geometry Dash, etc...) beneath. You can customize the videos used as brainrot footage in ùtils/config.py`.
- **Subtitle Overlays**: Subtitles are positioned near the bottom of the main video, just above the 'brainrot footage'.
- **YouTube Data API**: Automatically uploads each generated scene to YouTube.

---

## Installation

1. **Clone** this repository:

   ```bash
   git clone https://github.com/<username>/tulgakagan-YouTube-bot.git
   cd tulgakagan-YouTube-bot
   ```

2. **Create a Virtual Environment** (recommended):

   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

   Make sure you have **FFmpeg** installed on your system. For example:

   - **macOS** (Homebrew): `brew install ffmpeg`
   - **Ubuntu/Debian**: `sudo apt-get update && sudo apt-get install ffmpeg`
   - **Windows**: [Download FFmpeg](https://ffmpeg.org/download.html)

4. **YouTube API Setup**:

   - Enable the **YouTube Data API v3** on your Google Cloud project.
   - Download the `client_secret.json` file from the Google Cloud Console and place it in the root folder (alongside `main.py`).
   - The script will create a `token.json` after the first run.

5. **AssemblyAI Key** (Optional):

   - If you set `TRANSCRIBER = "assemblyai"` in `utils/config.py`, insert your key in `config.ASSEMBLYAI_API_KEY` or set `export ASSEMBLYAI_API_KEY=yourkey` as an environment variable.

6. **Vosk Model** (Optional):
   - If you choose `TRANSCRIBER = "vosk"`, download a Vosk model from [Download Vosk Model](alphacephei.com/vosk/models) and place it in `config.VOSK_DIRECTORY`. Make sure to set the correct path in `utils/config.py`.

---

## Usage

From the root directory, run:

```bash
python main.py "https://www.youtube.com/watch?v=<YOUR_VIDEO_ID>"
```

**Flow:**

1. The script **downloads** the YouTube video into `output/<Title>/<Title>.mp4`.

2. It checks for an official YouTube transcript. If unavailable, it **transcribes** locally (Whisper, Vosk, or AssemblyAI).

3. It **detects** scene changes using FFmpeg.

4. For each scene that is between 20 and 60 seconds:
   - Subclips the main video
   - Renders it in 9:16 format with background footage
   - Subtitles are added
   - Saves it locally in output/scenes/
   - Uploads the clip to YouTube

You’ll be prompted for Google OAuth the first time you run it. Once complete, the clip(s) appear in your YouTube channel.

## Configuration

Edit `utils/config.py` to customize:

- `TRANSCRIBER`: Set to `whisper`, `vosk`, or `assemblyai`.
- `PREFERRED_MODELS`: A dictionary mapping transcribers to model names.
- `brainrot_footage`: Mapping of different background clips (Temple Run, Subway Surfers, etc.). If a local path is missing, the script tries to download it.

## Known Limitations

- `Long Titles`: If the YouTube title is very long, path or filename issues can arise. restrictfilenames in yt_dlp helps, but remains something to watch.
- `Scene Detection Thresholds`: The default threshold is 0.8 in `utils/processors.py`. Adjust if you’re under-splitting scenes.
- `Network Requirements`: Downloads and uploads require a stable internet connection.
- `Time Complexity`: On non-GPU utilizable devices, the `.writevideofile()` command takes up quite a long time. Combined with the added delay in between uploading videos to YouTube, the script runs slow on CPU.

## Contributing

Feel free to open issues or pull requests to improve functionality or add new features.
