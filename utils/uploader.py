import os
import logging
from utils.youtube import get_youtube_service, upload_scene
from utils.log_utils import log_uploaded_video, log_failed_upload, get_uploaded_videos
from time import sleep
from typing import List, Any
import shutil

def upload_videos(videos: List[str], target: str, youtube_service: Any=None, delete_after_upload: bool=False)->bool:
    """
    Uploads video scenes to YouTube.
    Args:
        videos (List[str]): List of video scene file paths to upload.
        target (str): Target directory where the videos are located.
        youtube_service (Any): YouTube Data API service object. If None, it will be created.
        delete_after_upload (bool): If True, delete the local video file after successful upload.
    Returns:
        bool: True if all videos were uploaded successfully, False otherwise.
    """
    if not os.path.exists(target):
        logging.error("Target directory does not exist. Exiting.")
        return False
    if not videos:
        logging.error("No scene videos found. Exiting.")
        return False
    # You need to have the client_secret.json file in the same directory as this script.    
    # If you don't, you can download it from the Google Cloud Console. An invalid client_secret.json will cause an error.
    if youtube_service is None:
        youtube_service = get_youtube_service()
    if not youtube_service:
        logging.error("YouTube service object is None. Exiting upload.")
        return False
    uploaded_videos = get_uploaded_videos()
    # Main loop to upload videos
    for idx, scene in enumerate(videos):
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
        if idx < len(videos) - 1:
            sleep(10) # Delay before the next upload.

        #If scenes directory is empty, delete the original video directory, job is done.
    if not os.listdir(target):
        logging.info(f"Scenes directory is empty. Deleting original video directory: {target}")
        try:
            shutil.rmtree(target)
            logging.info(f"Original video directory deleted: {target}")
        except Exception as e:
            logging.error(f"Error deleting original video directory: {e}")
    return True