from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.errors import HttpError
import os
import logging
from utils.config import UPLOAD_LOG_FILE, FAILED_UPLOAD_LOG_FILE

# The YouTube Data API scope for uploading videos
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

def get_credentials():
    """
    Get credentials for the YouTube API.
    If valid credentials exist, they are loaded from token.json.
    If not, a new OAuth flow is started to get new credentials.
    """
    creds = None
    
    try:
        # If a token file already exists, load it to skip re-auth
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        
        # If credentials are invalid or don't exist, go through the OAuth flow
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                # Attempt to refresh the token if possible
                creds.refresh(Request())
            else:
                # Start a new OAuth flow with your client secrets file
                flow = InstalledAppFlow.from_client_secrets_file(
                    'client_secret.json', SCOPES
                )
                creds = flow.run_local_server(port=8080)
            
            # Save the credentials for next time
            with open('token.json', 'w') as token_file:
                token_file.write(creds.to_json())
    except Exception as e:
        logging.error(f"An error occurred while getting credentials: {e}")
        return None

    return creds

def get_youtube_service():
    """
    Create a YouTube Data API service object.
    """
    creds = get_credentials()
    if not creds:
        logging.error("Could not get credentials for YouTube API. Can't get youtube service.")
        return None
    youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)
    return youtube

def upload_video_to_youtube(video_path, title, description, tags, youtube_service):
    """
    Uploads a video to YouTube using the given youtube_service.
    """
    if youtube_service is None:
        return {'error': 'youtube_service_none'}
    
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
        },
        "status": {
            "privacyStatus": "public", # or "private" or "unlisted"
            "madeForKids": False
        }
    }
    
    media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
    
    #youtube_service = get_youtube_service() if youtube_service is None else youtube_service
    request = youtube_service.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media
    )
    response = None
    try:
        response = request.execute()
        print(f"Upload successful! Video ID: {response.get('id')}")
        return response
    except HttpError as e:
        error_details = e.content.decode() if hasattr(e, 'content') else str(e)
        logging.error(f"HTTP Error: {error_details}")
        
        # Handle specific upload limit error
        if 'uploadLimitExceeded' in error_details:
            logging.error("Upload limit exceeded. Skipping further uploads for today.")
            return {"error": "uploadLimitExceeded"}
        else:
            raise
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        raise

def upload_scene(scene_path: str, idx: int, dir_name: str, youtube_service) -> bool:
    """
    Uploads a scene video to YouTube.
    Args:
        scene_path (str): Path to the scene video file.
        idx (int): Index of the scene.
        vid_name (str): Name of the video.
        youtube_service: YouTube Data API service object.
    Returns:
        tuple: (bool, bool) - (success, limit_reached)
    """
    logging.info(f"Uploading scene {idx+1} to YouTube...")
    vid_name = os.path.basename(dir_name).replace("_", " ")
    title = f"{vid_name} - Part {idx+1}"
    description = f"This video has been automatically generated for course 20875 - SOFTWARE ENGINEERING, video name: {vid_name} #shorts"
    tags = ["shorts", "funny", "scene"]
    limit_reached = False
    try:
        response = upload_video_to_youtube(scene_path, title=title, description=description, tags=tags, youtube_service=youtube_service)
        if response == {"error": "uploadLimitExceeded"}:
            logging.warning("Daily upload limit reached. Stopping uploads.")
            limit_reached = True
            return False, limit_reached
        if response == {'error': 'youtube_service_none'}:
            logging.error("YouTube service object is None. Exiting upload.")
            return False, limit_reached
        logging.info(f"Scene {idx+1} uploaded to YouTube.")
        return True, limit_reached
    except Exception as e:
        logging.error(f"Error uploading scene {idx+1}: {e}")
        return False, limit_reached