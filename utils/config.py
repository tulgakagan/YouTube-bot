from dotenv import load_dotenv
import os
load_dotenv()

# Modify this config file before running the main.py file.

TRANSCRIBER = "vosk"  # whisper, vosk, assemblyai

PREFERRED_MODELS = {
    "whisper": "large-v3-turbo",
    "vosk": None,
    "assemblyai": None
}
MODELS = {
    "whisper": ["tiny", "tiny.en", "base", "base.en", "small", "small.en", "medium", "medium.en", "large-v3", "large-v3-turbo"],
    "vosk": ["vosk-model-small-en-us-0.15", "vosk-model-en-us-0.42-gigaspeech", "vosk-model-en-us-0.22-lgraph"],
    "assemblyai": [None]
}
VOSK_DIRECTORY = "/Users/tulgakagan/Desktop/AI_Lecture_Notes/Software_Engineering/YouTube-bot/utils/models"
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")

LOG_DIR = os.path.join(os.getcwd(), "logs")  # Create a "logs" directory in the current working directory
os.makedirs(LOG_DIR, exist_ok=True)  # Ensure the directory exists

UPLOAD_LOG_FILE = os.path.join(LOG_DIR, "uploaded_videos.log")
FAILED_UPLOAD_LOG_FILE = os.path.join(LOG_DIR, "failed_uploads.log")

brainrot_footage = {
    "subway_surfers": {
        "vid1": ["https://www.youtube.com/watch?v=PtyvtyIs1So", "/Users/tulgakagan/Desktop/AI_Lecture_Notes/Software_Engineering/YouTube-bot/footage_subway_surfers/Subway_Surfers_-_Gameplay_5_HD_1080p60FPS/Subway_Surfers_-_Gameplay_5_HD_1080p60FPS.mp4"], # Stock footage 1
        "vid2": ["https://www.youtube.com/watch?v=HTMDNZOlUq4", "/Users/tulgakagan/Desktop/AI_Lecture_Notes/Software_Engineering/YouTube-bot/footage_subway_surfers/Subway_Surfers_But_in_Unreal_Engine_5/Subway_Surfers_But_in_Unreal_Engine_5.mp4"], # Subway Surfers but in Unreal Engine
    },
    "temple_run": {
        "vid1": ["https://www.youtube.com/watch?v=fuQf-iGCmKA", "/Users/tulgakagan/Desktop/AI_Lecture_Notes/Software_Engineering/YouTube-bot/footage_temple_run/Temple_Run_2_2023_-_Gameplay_PC_UHD_4K60FPS/Temple_Run_2_2023_-_Gameplay_PC_UHD_4K60FPS.mp4"], # Temple run 2 gameplay
        "vid2": ["https://www.youtube.com/watch?v=m-ioG4KEVyc", "/Users/tulgakagan/Desktop/AI_Lecture_Notes/Software_Engineering/YouTube-bot/footage_temple_run/Temple_RunTM_But_in_Unreal_Engine_5/Temple_RunTM_But_in_Unreal_Engine_5.mp4"], # Temple Run but in Unreal Engine
    },
    "geometry_dash": {
        "vid1": ["https://www.youtube.com/watch?v=xu1wRfUHtKg", "/Users/tulgakagan/Desktop/AI_Lecture_Notes/Software_Engineering/YouTube-bot/footage_geometry_dash/WHAT_by_Spu7Nix_Geometry_Dash_Level/WHAT_by_Spu7Nix_Geometry_Dash_Level.mp4"], # WHAT by Spu7nix
        "vid2": ["https://www.youtube.com/watch?v=PnKGb6MR9No", "/Users/tulgakagan/Desktop/AI_Lecture_Notes/Software_Engineering/YouTube-bot/footage_geometry_dash/CONICAL_DEPRESSION_by_KrmaL_FULL_SHOWCASE_HIGH_QUALITY_DEMON_Geometry_Dash/CONICAL_DEPRESSION_by_KrmaL_FULL_SHOWCASE_HIGH_QUALITY_DEMON_Geometry_Dash.mp4"], # Random level by KrMaL
        "vid3": ["https://www.youtube.com/watch?v=gok5ShDXxg4", "/Users/tulgakagan/Desktop/AI_Lecture_Notes/Software_Engineering/YouTube-bot/footage_geometry_dash/Geometry_Dash_-_Clubstep_100%_All_Coins/Geometry_Dash_-_Clubstep_100%_All_Coins.mp4"] # Clubstep
    }
}
def check_config():
    if TRANSCRIBER not in ["whisper", "vosk", "assemblyai"]:
        raise ValueError("TRANSCRIBER must be one of 'whisper', 'vosk', or 'assemblyai'")
    if TRANSCRIBER == "assemblyai" and not ASSEMBLYAI_API_KEY:
        raise ValueError("ASSEMBLYAI_API_KEY must be set in the environment variables if using AssemblyAI")
    if TRANSCRIBER == "vosk" and (not VOSK_DIRECTORY or not os.path.exists(VOSK_DIRECTORY)):
        raise ValueError("VOSK_DIRECTORY must be set in utils/config.py")
    if TRANSCRIBER == "assemblyai" and not ASSEMBLYAI_API_KEY:
        raise ValueError("ASSEMBLYAI_API_KEY must be set in the environment variables")
    if not brainrot_footage:
        raise ValueError("brainrot_footage must be set in utils/config.py")
    for game, videos in brainrot_footage.items():
        for video in videos.values():
            if not video[0]:
                raise ValueError(f"Video link must be set for {game} in utils/config.py")
    return True
