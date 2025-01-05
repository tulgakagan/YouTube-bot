import os
from yt_dlp import YoutubeDL
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def download_video(video_url: str, output_dir: str = "output") -> str:
    """
    Download YouTube video using yt-dlp and save it to the given output directory,
    removing spaces and special characters from filenames.
    Returns the path of the downloaded video.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    # 'restrictfilenames': True => removes spaces (& and others) in the final filenames.
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4',
        'outtmpl': f"{output_dir}/%(title)s/%(title)s.%(ext)s",
        'restrictfilenames': True,
        'postprocessors': [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4'
        }],
        'nopart': True,
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            downloaded_file_path = os.path.join(
                os.getcwd(), info['requested_downloads'][0]['_filename']
            )
            logging.info(f"Download successful: {downloaded_file_path}")
            return downloaded_file_path
    except Exception as e:
        logging.error(f"Download failed: {e}")
        return None