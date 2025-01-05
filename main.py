import os
import logging
from googleapiclient.discovery import build
from utils.downloaders import download_video
from utils.processors import detect_scenes
from utils.render import prepare_and_upload_shorts
from utils.transcribers import get_transcript
from utils.youtube import get_youtube_service
import utils.config as config
from moviepy import VideoFileClip
from time import sleep
import sys

# Configure logging
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.DEBUG)  # Change to INFO or ERROR in production

#Initialize YouTube API service

def main(video_url):
    logging.info("Starting process...")
    transcriber = config.TRANSCRIBER
    model = config.PREFERRED_MODELS.get(transcriber, None)
    youtube_service = get_youtube_service() # comment this line if you are not using youtube service
    # Download Video
    downloaded_path = download_video(video_url)
    if not downloaded_path:
        logging.error("Could not download video. Exiting.")
        return

    # Get transcript
    transcript = get_transcript(downloaded_path=downloaded_path, video_url = video_url, transcriber=transcriber, model=model)
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
    rendered_vids = prepare_and_upload_shorts(clip = clip,
                                        resolution=(1080, 1920),
                                        timestamps = scene_timestamps,
                                        transcript=transcript,
                                        base_output_path=target,
                                        youtube_service=youtube_service) # 1080x1920
    return rendered_vids
    
if __name__ == "__main__":
    if len(sys.argv) < 2:
        logging.error("Please provide a video URL.")
        sys.exit(1)
    input_link = sys.argv[1]
    main(input_link)