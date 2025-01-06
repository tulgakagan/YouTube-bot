import os
from utils.config import UPLOAD_LOG_FILE, FAILED_UPLOAD_LOG_FILE
def log_uploaded_video(video_path):
    """Log a successfully uploaded video."""
    os.makedirs(os.path.dirname(UPLOAD_LOG_FILE), exist_ok=True)
    with open(UPLOAD_LOG_FILE, "a") as f:
        f.write(f"{video_path}\n")

def log_failed_upload(video_path):
    """Log a failed upload for retrying later."""
    os.makedirs(os.path.dirname(FAILED_UPLOAD_LOG_FILE), exist_ok=True)
    with open(FAILED_UPLOAD_LOG_FILE, "a") as f:
        f.write(f"{video_path}\n")

def get_uploaded_videos():
    """Retrieve the list of already uploaded videos from the log file."""
    if not os.path.exists(UPLOAD_LOG_FILE):
        return set()
    with open(UPLOAD_LOG_FILE, "r") as f:
        return set(line.strip() for line in f)

def get_failed_videos():
    """Retrieve the list of failed uploads."""
    if not os.path.exists(FAILED_UPLOAD_LOG_FILE):
        return set()
    with open(FAILED_UPLOAD_LOG_FILE, "r") as f:
        return set(line.strip() for line in f)