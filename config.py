

# Using this config file alone should be able to get you going without further modification.

transcriber = "vosk"  # whisper, vosk, assemblyai


MODELS = {
    "whisper": ["tiny", "tiny.en", "base", "base.en", "small", "small.en", "medium", "medium.en", "large-v3", "]arge-v3-turbo"],
    "vosk": ["vosk-model-small-en-us-0.15", "vosk-model-en-us-0.42-gigaspeech", "vosk-model-en-us-0.22-lgraph"],
    "assemblyai": [None]
}

brainrot_footage = {
    "subway_surfers": {
        "vid1": ["https://www.youtube.com/watch?v=PtyvtyIs1So", "/Users/tulgakagan/Desktop/AI_Lecture_Notes/Software_Engineering/Project/utils/footage_subway_surfers/Subway_Surfers_-_Gameplay_5_HD_1080p60FPS/Subway_Surfers_-_Gameplay_5_HD_1080p60FPS.mp4"], # Stock footage 1
        "vid2": ["https://www.youtube.com/watch?v=HTMDNZOlUq4", "/Users/tulgakagan/Desktop/AI_Lecture_Notes/Software_Engineering/Project/utils/footage_subway_surfers/Subway_Surfers_But_in_Unreal_Engine_5/Subway_Surfers_But_in_Unreal_Engine_5.mp4"], # Subway Surfers but in Unreal Engine
    },
    "temple_run": {
        "vid1": ["https://www.youtube.com/watch?v=fuQf-iGCmKA", "/Users/tulgakagan/Desktop/AI_Lecture_Notes/Software_Engineering/Project/utils/footage_temple_run/Temple_Run_2_2023_-_Gameplay_PC_UHD_4K60FPS/Temple_Run_2_2023_-_Gameplay_PC_UHD_4K60FPS.f401.mp4"], # Temple run 2 gameplay
        "vid2": ["https://www.youtube.com/watch?v=m-ioG4KEVyc", "/Users/tulgakagan/Desktop/AI_Lecture_Notes/Software_Engineering/Project/utils/footage_temple_run/Temple_RunTM_But_in_Unreal_Engine_5/Temple_RunTM_But_in_Unreal_Engine_5.mp4"], # Temple Run but in Unreal Engine
    },
    "geometry_dash": {
        "vid1": ["https://www.youtube.com/watch?v=xu1wRfUHtKg", "/Users/tulgakagan/Desktop/AI_Lecture_Notes/Software_Engineering/Project/utils/footage_geometry_dash/WHAT_by_Spu7Nix_Geometry_Dash_Level/WHAT_by_Spu7Nix_Geometry_Dash_Level.mp4"], # WHAT by Spu7nix
        "vid2": ["https://www.youtube.com/watch?v=PnKGb6MR9No", "/Users/tulgakagan/Desktop/AI_Lecture_Notes/Software_Engineering/Project/utils/footage_geometry_dash/CONICAL_DEPRESSION_by_KrmaL_FULL_SHOWCASE_HIGH_QUALITY_DEMON_Geometry_Dash/CONICAL_DEPRESSION_by_KrmaL_FULL_SHOWCASE_HIGH_QUALITY_DEMON_Geometry_Dash.mp4"], # Random level by KrMaL
        "vid3": ["https://www.youtube.com/watch?v=gok5ShDXxg4", "/Users/tulgakagan/Desktop/AI_Lecture_Notes/Software_Engineering/Project/utils/footage_geometry_dash/Geometry_Dash_-_Clubstep_100%_All_Coins/Geometry_Dash_-_Clubstep_100%_All_Coins.mp4"] # Clubstep
    },
}


# Note that by default, public isn't available unless you go through an audit. Checkout: https://support.google.com/youtube/contact/yt_api_form


# for category: has to be an int, refer to YouTube Data 4 API's documentation, but as of Jan 2022,
# checkout https://techpostplus.com/youtube-video-categories-list-faqs-and-solutions/
