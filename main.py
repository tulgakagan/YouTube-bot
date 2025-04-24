import os
import logging
from utils.downloaders import download_video_if_needed
from utils.processors import detect_scenes
from utils.render import prepare_shorts
from utils.transcribers import get_transcript
from utils.youtube import get_youtube_service
from utils.uploader import upload_videos
import utils.config as config
from moviepy import VideoFileClip
import sys

# Configure logging
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
def main(input: str) -> bool:
    """
    The main function.
    1. Downloads the video
    2. Gets the transcript
    3. Detects scenes
    4. Prepares and uploads shorts
    """
    config.check_config()  # Check if the configuration is correct
    logging.info("Configuration is correct, starting the process...")

    # Initialize services and configuration
    transcriber = config.TRANSCRIBER
    assemblyai_token = config.ASSEMBLYAI_API_KEY if transcriber == "assemblyai" else None
    delete_after_upload = config.DELETE_AFTER_UPLOAD
    model = config.PREFERRED_MODELS.get(transcriber, None)

    # You need to have the client_secret.json file in the same directory as this script.
    # If you don't, you can download it from the Google Cloud Console. An invalid client_secret.json will cause an error.
    youtube_service = get_youtube_service()
    if not youtube_service:
        logging.error("YouTube service object is None. Exiting upload.")
        return False
    # Download Video
    downloaded_path = download_video_if_needed(input)
    if not downloaded_path:
        logging.error("Could not find video. Exiting.")
        return False

    # Get transcript
    transcript = get_transcript(downloaded_path=downloaded_path, video_url = input, transcriber=transcriber, model=model, assemblyai_token=assemblyai_token)
    if not transcript:
        logging.error("Could not get transcript. Exiting.")
        return False
    
    # Detect scenes
    scene_timestamps = detect_scenes(downloaded_path, threshold=0.8)
    if not scene_timestamps:
        logging.error("Could not detect scenes. Exiting.")
        return False

    # Convert to multiple scene shorts with vertical 9x16 with brainrot footage and subtitles
    target = os.path.dirname(downloaded_path)
    with VideoFileClip(downloaded_path) as clip:
        final_videos = prepare_shorts(clip = clip, timestamps=scene_timestamps, transcript=transcript, base_output_path=target)

    # Upload videos
    success = upload_videos(videos=final_videos,
                            target=target,
                            youtube_service=youtube_service,
                            delete_after_upload=delete_after_upload)
    if not success:
        logging.error("Upload process failed. Exiting.")
        return False
    logging.info("Upload process completed successfully.")
    return True

def main_upload_only(scenes_directory: str) -> bool:
    """
    Uploads all the scene videos in the given directory to YouTube.
    Only when you have scenes that haven't been uploaded, and you want to upload them without processing everything again.
    Args:
        scenes_directory: str: Path to the directory containing scene videos.
    """
    if not os.path.exists(scenes_directory):
        logging.error("Scenes directory does not exist. Exiting.")
        return False

    # You need to have the client_secret.json file in the same directory as this script.
    # If you don't, you can download it from the Google Cloud Console. An invalid client_secret.json will cause an error.
    youtube_service = get_youtube_service()
    if not youtube_service:
        logging.error("YouTube service object is None. Exiting upload.")
        return False
    
    delete_after_upload = config.DELETE_AFTER_UPLOAD

    target = os.path.dirname(scenes_directory)
    video_list = sorted(os.listdir(scenes_directory))
    video_list = [os.path.join(scenes_directory, video) for video in video_list if video.endswith(".mp4")] #Include only .mp4 files

    # Main loop to upload videos
    success = upload_videos(videos=video_list,
                            target=target,
                            youtube_service=youtube_service,
                            delete_after_upload=delete_after_upload)
    if not success:
        logging.error("Upload process failed. Exiting.")
        return False
    logging.info("Upload process completed successfully.")
    return True

if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[2] == "--upload-only":
        scenes_directory = sys.argv[1]
        success = main_upload_only(scenes_directory)
        if success:
            logging.info("Upload process completed successfully.")
            sys.exit(0)
        else:
            logging.error("Upload process failed.")
            sys.exit(1)
    if len(sys.argv) < 2:
        logging.error("Please provide a video URL or path to a video file.")
        sys.exit(1)
    input_link = sys.argv[1]
    if not input_link:
        logging.error("Please provide a video URL or path to a video file.")
        sys.exit(1)
    success = main(input_link)
    if success:
        logging.info("Process completed successfully.")
        sys.exit(0)
    else:
        logging.error("Process failed.")
        sys.exit(1)