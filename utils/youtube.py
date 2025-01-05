from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import os

# The YouTube Data API scope for uploading videos
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

def get_credentials():
    """
    Get credentials for the YouTube API.
    If valid credentials exist, they are loaded from token.json.
    If not, a new OAuth flow is started to get new credentials.
    """
    creds = None
    
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
    return creds


def get_youtube_service():
    """
    Create a YouTube Data API service object.
    """
    creds = get_credentials()
    youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)
    return youtube

def upload_video_to_youtube(video_path, title, description, tags, youtube_service=None):
    """
    Uploads a video to YouTube using the given youtube_service.
    """
    if youtube_service is None:
        youtube_service = get_youtube_service()
    
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            # 'categoryId': '22',  # optional, e.g. '22' = People & Blogs
        },
        "status": {
            "privacyStatus": "public",  # or 'unlisted' or 'public'
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
    except Exception as e:
        print(f"An error occurred while uploading: {e}")
        raise
    return response