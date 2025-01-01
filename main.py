import os
import logging
from googleapiclient.discovery import build
from utils.downloaders import download_video
from utils.processors import add_subtitles_from_transcript, cut_and_subtitle
from utils.transcribers import get_transcript
from utils.youtube import upload_video_to_youtube
from dotenv import load_dotenv

# Load values from .env
load_dotenv()
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base").lower()  # fallback to "base" if not set
VOSK_MODEL = os.getenv("VOSK_MODEL", "vosk-model-small-en-us-0.15").lower()  # fallback to "vosk-model-small-en-us-0.15" if not set
TRANSCRIBER = os.getenv("TRANSCRIBER", "vosk").lower()  # fallback to "whisper" if not set
MODELS_DIRECTORY = os.getenv("MODELS_DIRECTORY", "/Users/tulgakagan/Desktop/AI_Lecture_Notes/Software_Engineering/Project/utils/models")
OUTPUT_DIRECTORY = os.getenv("OUTPUT_DIRECTORY", "/Users/tulgakagan/Desktop/AI_Lecture_Notes/Software_Engineering/Project/output")

# Configure logging
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.DEBUG)  # Change to INFO or ERROR in production


def main(video_url):
    logging.info("Starting process...")
    transcriber = TRANSCRIBER
    
    # 1. Download Video
    downloaded_path = download_video(video_url)
    if not downloaded_path:
        logging.error("Could not download video. Exiting.")
        return

    # 2. Get transcript
    transcript = get_transcript(video_url, downloaded_path, transcriber)
    
    # 3. Processing the video
    scene_paths = cut_and_subtitle(downloaded_path, transcript, threshold=0.8, output_dir="scenes")

    return scene_paths
    # 5. Generating subtitles
    # subtitled_output = add_subtitles_from_transcript(downloaded_path, transcript)
    # logging.info(f"Subtitled video successfully created: {subtitled_output}")

    # 6. Upload to YouTube
    title = "test-001"
    description = "This video has been automatically subtitled using AI."
    tags = ["efejuan", "gardenersson"]
    #upload_video_to_youtube(subtitled_output, title, description, tags)
    
if __name__ == "__main__":
    # Example usage:
    video_url = "https://www.youtube.com/watch?v=ishgn7-NLlU"
    #video_url = "https://www.youtube.com/watch?v=VYJtb2YXae8"
    #video_url = "https://www.youtube.com/watch?v=Nir5MNmPzZo" #Impractical Jokers
    
    main(video_url)
    logging.info("Script finished successfully.")