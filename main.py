import os
import logging
from utils.downloaders import download_video_if_needed
from utils.processors import detect_scenes
from utils.render import prepare_and_upload_shorts, prepare_shorts
from utils.transcribers import get_transcript
from utils.youtube import get_youtube_service, upload_video_to_youtube
import utils.config as config
from moviepy import VideoFileClip
import sys
from time import sleep
import random

# Configure logging
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.info)  # Change to INFO or ERROR in production

#Initialize YouTube API service

def main(input):
    """
    The main function.
    1. Downloads the video
    2. Gets the transcript
    3. Detects scenes
    4. Prepares and uploads shorts
    """
    logging.info("Starting process...")
    # Get configuration
    transcriber = config.TRANSCRIBER
    model = config.PREFERRED_MODELS.get(transcriber, None)
    youtube_service = get_youtube_service() # Initialize YouTube API service, comment this line if you are not uploading to YouTube

    # Download Video
    downloaded_path = download_video_if_needed(input)
    if not downloaded_path:
        logging.error("Could not find video. Exiting.")
        return

    # Get transcript
    transcript = get_transcript(downloaded_path=downloaded_path, video_url = input, transcriber=transcriber, model=model)
    if not transcript:
        logging.error("Could not get transcript. Exiting.")
        return
    # Detect scenes
    scene_timestamps = detect_scenes(downloaded_path, threshold=0.8)
    if not scene_timestamps:
        logging.error("Could not detect scenes. Exiting.")
        return

    # Convert to multilpe scene shorts with vertical 9x16 with brainrot footage and subtitles
    target = os.path.dirname(downloaded_path)
    clip = VideoFileClip(downloaded_path)
    final_videos = prepare_shorts(clip = clip, timestamps=scene_timestamps, transcript=transcript, base_output_path=target)

    # Upload to YouTube
    for idx, video in enumerate(final_videos):
        logging.info(f"Uploading scene {idx+1} to YouTube...")
        # Prepare metadata
        vid_name = os.path.basename(target).replace("_", " ")
        title = f"Part {idx+1}"
        description = f"This video has been automatically generated for my course 20875 - SOFTWARE ENGINEERING, video name: {vid_name} #shorts"
        tags = ["shorts", "funny", "scene"]
        # Upload
        upload_video_to_youtube(video, title=title, description=description, tags=tags, youtube_service=youtube_service)
        logging.info(f"Scene {idx+1} with subtitles uploaded to YouTube.")
        # Delay before the next upload, to avoid rate limiting by YouTube (bot detection)
        if idx < len(final_videos) - 1:
            delay = random.randint(600, 1200)  # Random delay between 10 to 20 minutes
            mins, secs = delay//60, delay%60
            logging.info(f"Waiting for {mins} minutes, {secs} seconds before uploading the next video...")
            sleep(delay)
    return 1
    
if __name__ == "__main__":
    if len(sys.argv) < 2:
        logging.error("Please provide a video URL.")
        sys.exit(1)
    input_link = sys.argv[1]
    success = main(input_link)
    if success:
        logging.info("Process completed successfully.")
    else:
        logging.error("Process failed.")