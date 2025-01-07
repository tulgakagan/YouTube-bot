from moviepy import VideoFileClip, CompositeVideoClip, vfx, TextClip
import numpy as np
import logging
import utils.config as config
from utils.downloaders import download_video_if_needed
from time import sleep
import os
import re

def get_brainrot_footage(game: str=None, config_path: str="utils/config.py") -> VideoFileClip:
    """
    Returns the brainrot footage for the specified game.

    Args:
        game (str): The game to get the brainrot footage for.
        config_path (str): The path to the configuration file.

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
    invalid_path = "placeholder"
    if not source:
        logging.error(f"Source for footage '{footage}' not found.")
        return None
    try:
        result = VideoFileClip(footage_path).without_audio()
    except Exception as e:
        logging.warning(f"Error loading footage for game '{game}' from path: {footage_path}. Will download from source.")
        invalid_path = f'{footage_path}'
        footage_path = None
    if not footage_path:
        logging.info(f"Footage path for footage '{footage}' not found. Downloading from source: {source}")
        footage_path = download_video_if_needed(source, output_dir=f"footage_{game}")
        sleep(1) # Wait for a second to ensure the download is complete
        # Update the config module with the new footage path
        config.brainrot_footage[game][footage][1] = footage_path

        # Make the change permanent in the config file
        with open(config_path, 'r') as file:
            config_data = file.read()

        # Update the footage path in the config data
        config_data = config_data.replace(f'"{source}", "{invalid_path}"', f'"{source}", "{footage_path}"')

        # Write the updated config back to the file
        with open(config_path, 'w') as file:
            file.write(config_data)
        logging.info(f"Loading footage for game '{game}' from path: {footage_path}")
        result = VideoFileClip(footage_path).without_audio()

    if not result:
        logging.error(f"Error loading footage for game '{game}' from path: {footage_path}")
        return None
    return result


def render(clip: VideoFileClip, resolution: tuple=(1080, 1920), game: str=None) -> VideoFileClip:
    """
    Resizes video by positioning the main clip on top of a random video game footage.

    Args:
        clip (VideoFileClip): The original video clip to resize.
        resolution (tuple): Tuple of the desired resolution of the video.
        game (str): The game to get the footage for.

    Returns:
        VideoFileClip: The final video clip with the desired resolution.
    """
    brainrot_games = list(config.brainrot_footage.keys())
    if game is None:
        game = np.random.choice(brainrot_games)
        logging.info(f"No game specified. Randomly selected game: {game}")

    elif game not in brainrot_games:
        logging.error(f"Game '{game}' not found in brainrot games.")
        raise ValueError(f"Game '{game}' not found in brainrot games.")
    
    try:
        #main_clip = clip.resized(height=resolution[1]//2, width=resolution[0])
        main_clip = clip.resized(height=840, width=resolution[0]) # height: 840 To make space for subtitles and to not lose too much of the main clip after cropping
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
            logging.debug(f"Trimming brainrot clip to match main clip duration. Start time: {start_time}, Duration: {main_clip.duration}")
            brainrot_clip = brainrot_clip.subclipped(start_time, start_time + main_clip.duration)
        elif duration_diff < 0:
            #brainrot clip is shorter than main clip
            #loop the brainrot clip
            brainrot_clip = brainrot_clip.with_effects([vfx.Loop(duration=main_clip.duration)])

        #Resize the brainrot clip to match the main clip
        orig_w, orig_h = brainrot_clip.size
        target_h = 1080 # A little more than main clip height, because we want the main clip to not be cropped too much
        scale_factor = target_h / orig_h
        scaled_w = int(orig_w * scale_factor)
        x_center = scaled_w / 2
        x1 = x_center - (1080 / 2)

        brainrot_clip = brainrot_clip.resized((scaled_w, target_h)) \
            .cropped(x1=x1, y1=0, width=1080, height=target_h)

        logging.debug(f"Brainrot clip resized successfully. New dimensions: {brainrot_clip.size}")

        #Compose main clip and brainrot clip, with brainrot clip below and main clip on top
        logging.debug(f"Main clip size and position: {main_clip.size}\n Brainrot clip size: {brainrot_clip.size}")
        sleep(1)
        video = CompositeVideoClip([main_clip.with_position("top"), brainrot_clip.with_position("bottom")], size=resolution)
        sleep(1)
        return video
    except Exception as e:
        logging.error(f"An error occurred during rendering: {e}")
        return None

def subtitle_subclip(subclip: VideoFileClip, transcript: list[dict], start: float, end: float, i: int) -> CompositeVideoClip:
    """
    Subtitles a subclip with the given transcript.
    args:
        subclip (VideoFileClip): The subclip to subtitle.
        transcript (list[dict]): The list of dictionaries containing subtitle information.
        start (float): The start time of the subclip.
        end (float): The end time of the subclip.
        i (int): The index of the subclip.
    Returns:
        CompositeVideoClip: The final video clip with subtitles.
    """
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
    logging.debug(f"Transcript for scene {i+1} created: {len(local_transcript)}")
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
    logging.debug(f"Subtitles for scene {i+1} created: {len(subtitle_clips)}")
    #Composite subclip + local subtitles
    logging.debug(f"Compositing scene {i+1} with subtitles...")
    final_video = CompositeVideoClip([subclip] + subtitle_clips)
    return final_video


def prepare_shorts(clip: VideoFileClip, timestamps: list=None,
                              resolution: tuple=(1080,1920), game: str = None,
                              transcript: list = None, base_output_path: str = "output",
                              ) -> list[str]:
    """
    Cuts, renders, adds subtitles, and saves multiple scenes from a video clip.

    Args:
        clip (VideoFileClip): The original video clip.
        timestamps (list): List of timestamps to split the video into scenes.
        transcript (list): List of dictionaries containing subtitle information with keys "start", "end", and "text".
        base_output_path (str): The base directory to save the prepared videos.

    Returns:
        list[str]: List of file paths for each prepared video.
    """
    subclips = []
    try:
        scene_count = len(timestamps) - 1
        for i in range(scene_count):
            start = timestamps[i]
            end = timestamps[i + 1]
            if end-start < 20:
                logging.info(f"Scene {i+1} is too short. Skipping...")
                continue
            if end-start > 180:
                logging.error(f"Scene {i+1} is too long. Skipping...")
                continue
            logging.info(f"Rendering scene {i+1} of {scene_count} from {start} to {end}...")
            scene = clip.subclipped(start, end)

            scene = render(scene, resolution=resolution)
            logging.info(f"Scene {i+1} of {scene_count} rendered successfully. Duration: {scene.duration} seconds. Subtitling...")   
            # Scene Subtitling
            final_video = subtitle_subclip(scene, transcript, start, end, i)
            logging.info(f"Scene {i+1} of {scene_count} subtitled successfully. Saving...")
            #Downloading locally
            output_dir = os.path.join(base_output_path, "scenes")
            if not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
            out_path = f"{output_dir}/scene_{i+1}.mp4"
            final_video.write_videofile(out_path, codec="libx264")
            logging.info(f"Scene {i+1} with subtitles saved to: {out_path}")
            subclips.append(out_path)
            sleep(5) # Rest for 5 seconds
        return subclips
    except Exception as e:
        logging.error(f"An error occurred while preparing shorts: {e}")
    except KeyboardInterrupt:
        logging.error("Process interrupted.")
        return subclips