import os
import logging
from utils.downloaders import download_video_if_needed
from utils.processors import detect_scenes
from utils.render import prepare_shorts
from utils.transcribers import get_transcript
from utils.youtube import get_youtube_service, upload_scene
from utils.log_utils import log_uploaded_video, log_failed_upload, get_uploaded_videos
import utils.config as config
from moviepy import VideoFileClip
import sys
from time import sleep

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
    clip = VideoFileClip(downloaded_path)
    final_videos = prepare_shorts(clip = clip, timestamps=scene_timestamps, transcript=transcript, base_output_path=target)

    # Get list of already uploaded videos
    uploaded_videos = get_uploaded_videos()

    # Youtube service check
    if not youtube_service:
        logging.error("YouTube service object is None. Exiting upload.")
        return True

    # Main loop to upload videos

    for idx, scene in enumerate(final_videos):
        if scene in uploaded_videos:
            logging.info(f"Video {scene} already uploaded. Skipping...")
            if delete_after_upload:
                try:
                    os.remove(scene)
                    logging.info(f"Scene {idx+1} deleted. Path: {scene}")
                except Exception as e:
                    logging.error(f"Error deleting scene {idx+1}: {e}")
            continue
        success, limit = upload_scene(scene_path=scene, idx=idx, dir_name=target, youtube_service=youtube_service)
        if not success:
            log_failed_upload(scene)
            if limit:
                break
            else:
                continue
        log_uploaded_video(scene)

        #Delete local file after successful upload
        if delete_after_upload:
            try:
                os.remove(scene)
                logging.info(f"Scene {idx+1} deleted. Path: {scene}")
            except Exception as e:
                logging.error(f"Error deleting scene {idx+1}: {e}")
        if idx < len(final_videos) - 1:
            sleep(10) # Delay before the next upload.

    return True

def main_upload_only(scenes_directory: str):
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
    
    uploaded_videos = get_uploaded_videos()
    delete_after_upload = config.DELETE_AFTER_UPLOAD

    target = os.path.dirname(scenes_directory)
    video_list = sorted(os.listdir(scenes_directory))
    video_list = [video for video in video_list if video.endswith(".mp4")] #Include only .mp4 files

    # Main loop to upload videos
    for idx, scene in enumerate(video_list):
        if scene == ".DS_Store":  # Skip .DS_Store
            continue

        scene_path = os.path.join(scenes_directory, scene)
        if scene_path in uploaded_videos:
            if delete_after_upload:
                try:
                    os.remove(scene)
                    logging.info(f"Scene {idx+1} deleted. Path: {scene}")
                except Exception as e:
                    logging.error(f"Error deleting scene {idx+1}: {e}")
            continue
        success, limit = upload_scene(scene_path=scene_path, idx=idx, dir_name=target, youtube_service=youtube_service)
        if not success:
            log_failed_upload(scene_path)
            if limit:
                break
            else:
                continue
        #log_uploaded_video(scene_path) # Log the uploaded video

        #Delete local file after successful upload
        if delete_after_upload:
            try:
                os.remove(scene)
                logging.info(f"Scene {idx+1} deleted. Path: {scene}")
            except Exception as e:
                logging.error(f"Error deleting scene {idx+1}: {e}")
        if idx < len(video_list) - 1:
            sleep(10) # Delay before the next upload.
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