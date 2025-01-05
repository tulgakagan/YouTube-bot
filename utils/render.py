from moviepy import VideoFileClip, CompositeVideoClip, vfx, TextClip
import numpy as np
import logging
import utils.config as config
from utils.downloaders import download_video
from time import sleep
import os
from utils.youtube import upload_video_to_youtube
#import tempfile #If you wish to download locally

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def get_brainrot_footage(game: str=None, config_path: str="utils/configurasyon.py"):
    """
    Returns the brainrot footage for the specified game.

    Args:
        game (str): The game to get the brainrot footage for.
        resolution (tuple): Tuple of the desired resolution of the video.

    Returns:
        VideoFileClip, str: The specified game.
    """
    
    footages = config.brainrot_footage.get(game)
    if not footages:
        logging.error(f"No footage found for game '{game}'.")
        return None

    vid_list = list(footages.keys())
    logging.info(f"{len(vid_list)} footages found for game '{game}'")
    footage = np.random.choice(vid_list)
    source, footage_path = footages.get(footage)
    if not source:
        logging.error(f"Source for footage '{footage}' not found.")
        return None
    if not footage_path:
        logging.info(f"Footage path for footage '{footage}' not found. Downloading from source: {source}")
        footage_path = download_video(source, output_dir=f"footage_{game}")
    
        # Update the configurasyon module with the new footage path
        config.brainrot_footage[game][footage][1] = footage_path

        # Make the change permanent in the configuration file
        with open(config_path, 'r') as file:
            config_data = file.read()

        # Update the footage path in the configuration data
        config_data = config_data.replace(f'"{source}", None', f'"{source}", "{footage_path}"')

        # Write the updated configuration back to the file
        with open(config_path, 'w') as file:
            file.write(config_data)
        logging.info(f"Loading footage for game '{game}' from path: {footage_path}")

    result = VideoFileClip(footage_path).without_audio()
    if not result:
        logging.error(f"Error loading footage for game '{game}' from path: {footage_path}")
        return None
    return result


def render(clip: VideoFileClip, resolution: tuple=(1080, 1920), game: str=None):
    """
    Resizes, centers, and renders a video clip with optional edge blur if needed.

    Args:
        clip (VideoFileClip): The original video clip to resize.
        resolution (tuple): Tuple of the desired resolution of the video.

    Returns:
        VideoFileClip: The final video clip with the desired resolution.
    """
    brainrot_games = list(config.brainrot_footage.keys())
    if game is None:
        game = np.random.choice(brainrot_games)
        logging.info(f"No game specified. Randomly selected game: {game}")

    if game not in brainrot_games:
        logging.error(f"Game '{game}' not found in brainrot games.")
        raise ValueError(f"Game '{game}' not found in brainrot games.")
    
    try:
        #main_clip = clip.resized(height=resolution[1]//2, width=resolution[0])
        main_clip = clip.resized(height=840, width=resolution[0])
        #Fill the rest of the video with brainrot footage
        brainrot_clip = get_brainrot_footage(game)
        brainrot_clip = brainrot_clip.cropped(
            x_center=brainrot_clip.w / 2,
            width=brainrot_clip.w * 0.65
        )
        if not brainrot_clip:
           logging.error("Failed to get brainrot footage.")
           raise ValueError("Failed to get brainrot footage.")
        #Adjust the duration of the brainrot clip to match the main clip
        duration_diff = brainrot_clip.duration - main_clip.duration
        if duration_diff > 0:
            #brainrot clip is longer than main clip
            #trim the brainrot clip
            #random initialisation of the start time
            start_time = np.random.uniform(0, duration_diff)
            logging.info(f"Trimming brainrot clip to match main clip duration. Start time: {start_time}, Duration: {main_clip.duration}")
            brainrot_clip = brainrot_clip.subclipped(start_time, start_time + main_clip.duration)
        elif duration_diff < 0:
            #brainrot clip is shorter than main clip
            #loop the brainrot clip
            brainrot_clip = brainrot_clip.with_effects([vfx.Loop(duration=main_clip.duration)])

        #Resize the brainrot clip to match the main clip
        orig_w, orig_h = brainrot_clip.size
        target_h = 1080 #leaving some space for the subtitles 910
        scale_factor = target_h / orig_h
        scaled_w = int(orig_w * scale_factor)
        x_center = scaled_w / 2
        x1 = x_center - (1080 / 2)

        brainrot_clip = brainrot_clip.resized((scaled_w, target_h)) \
            .cropped(x1=x1, y1=0, width=1080, height=target_h)

        logging.info(f"Brainrot clip resized successfully. New dimensions: {brainrot_clip.size}")

        #Compose main clip and brainrot clip, with brainrot clip below and main clip on top
        logging.info(f"Main clip size and position: {main_clip.size}\n Brainrot clip size: {brainrot_clip.size}")
        sleep(1)
        video = CompositeVideoClip([main_clip.with_position("top"), brainrot_clip.with_position("bottom")], size=resolution)
        sleep(1)
        return video
    except Exception as e:
        logging.debug(f"An error occurred during rendering: {e}")
        return None

def prepare_and_upload_shorts(youtube_service, clip: VideoFileClip, timestamps: list=None,
                              resolution: tuple=(1080,1920), game: str = None,
                              transcript: list = None, base_output_path: str = "output",
                              ) -> list:
    """
    Cuts, renders, adds subtitles, and saves multiple scenes from a video clip.

    Args:
        timestamps (list): List of timestamps to split the video into scenes.
        transcript (list): List of dictionaries containing subtitle information with keys "start", "end", and "text".
        base_output_path (str): The base directory to save the rendered scenes.

    Returns:
        list: List of file paths for each rendered scene.
    """
    subclips = []  #Used only if you wish to download locally
    try:
        for i in range(len(timestamps) - 1):
            start = timestamps[i]
            end = timestamps[i + 1]
            if end-start < 20:
                logging.info(f"Scene {i+1} is too short. Skipping...")
                continue
            if end-start > 60:
                logging.error(f"Scene {i+1} is too long. Skipping...")
                continue
            logging.info(f"Rendering scene {i+1} from {start} to {end}...")
            subclip = clip.subclipped(start, end)

            subclip = render(subclip, resolution=resolution)
            # Subclip Subtitling
            final_video = subtitle_subclip(subclip, transcript, start, end, i)
            logging.info(f"Scene {i+1} rendered successfully. Duration: {final_video.duration} seconds. Saving...")
            #Download locally and upload to youtube. If you wish to only upload to youtube, comment the following lines, and uncomment the code below them.
            output_dir = os.path.join(base_output_path, "scenes")
            if not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
            out_path = f"{output_dir}/scene_{i+1}.mp4"
            final_video.write_videofile(out_path, codec="libx264")
            sleep(5) # Wait for the file to be written
            logging.info(f"Subclip {i} with subtitles saved to: {out_path}")
            subclips.append(out_path)

            vid_name = os.path.basename(base_output_path).replace("_", " ")
            title = f"Part {i+1}"
            description = f"This video has been automatically generated for my course 20875 - SOFTWARE ENGINEERING, video name: {vid_name} #shorts"
            tags = ["shorts", "funny", "scene"]
            try:
                upload_video_to_youtube(out_path, title=title, description=description, tags=tags, youtube_service=youtube_service)
                logging.info(f"Subclip {i+1} with subtitles uploaded to YouTube.")
            except Exception as e:
                logging.error(f"An error occurred during upload of subclip{i+1} to YouTube: {e}")
            
            sleep(5) # Rest for 5 seconds
        return subclips
    
            # Write to temporary file and upload to YouTube (If you wish to upload to youtube, if not, comment the following lines, including return 1)
            # with tempfile.NamedTemporaryFile(suffix=".mp4", delete=True) as temp_video_file:
            #     final_video.write_videofile(temp_video_file.name, codec="libx264")
            #     logging.info(f"Subclip {i+1} with subtitles saved to: {temp_video_file.name}")
            #     vid_name = base_output_path.replace("_", " ")
            #     title = f"Part {i+1}"
            #     description = f"This video has been automatically generated for my course 20875 - SOFTWARE ENGINEERING, video name: {vid_name} #shorts"
            #     tags = ["shorts", "funny", "scene"]
            #     upload_video_to_youtube(temp_video_file.name, title=title, description=description, tags=tags)
            #     logging.info(f"Subclip {i+1} with subtitles uploaded to YouTube.")
            #     sleep(5) # Rest for 5 seconds

        #return 1
    except Exception as e:
        logging.error(f"An error occurred during multiple rendering: {e}")

def subtitle_subclip(subclip: VideoFileClip, transcript: list[dict], start: float, end: float, i: int) -> list:
    local_transcript = []
    for entry in transcript:
        start_global = entry["start"]
        end_global = entry["end"]
        text = entry["text"]

        # If there's any overlap with the subclip
        if end_global > start and start_global < end:
            # Clip the times to subclip range
            # But typically, you just shift them; 
            # partial overlap is also possible if subtitles cross scene boundary
            local_start = max(0, start_global - start)
            local_end = max(0, end_global - start)

            # We can optionally clamp the times so subtitles don't exceed subclip duration
            # For instance:
            local_start = min(local_start, end - start)
            local_end = min(local_end, end - start)

            local_transcript.append({
                        "start": local_start,
                        "end": local_end,
                        "text": text
                    })
    logging.info(f"Transcript for scene {i+1} created: {len(local_transcript)}")
    # 2) Build subtitle clips for *this subclip*
    subtitle_clips = []
    for entry in local_transcript:
        if entry["end"] > entry["start"]:  # ensure non-zero duration
            txt_clip = (TextClip(
                text=entry["text"],
                font="Arial",
                color="white",
                font_size=60,
                stroke_color="black",
                stroke_width=2
            )
            .with_start(entry["start"]) \
            .with_end(entry["end"]) \
            .with_position(("center", 780)))  # or ("center","bottom")
            subtitle_clips.append(txt_clip)
    logging.info(f"Subtitles for scene {i+1} created: {len(subtitle_clips)}")
    #Composite subclip + local subtitles
    logging.info(f"Compositing scene {i+1} with subtitles...")
    final_video = CompositeVideoClip([subclip] + subtitle_clips)
    return final_video
