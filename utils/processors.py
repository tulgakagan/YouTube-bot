import re
import subprocess
import logging
import sys
from datetime import datetime
import os
#import ffmpeg
from moviepy import TextClip, CompositeVideoClip, VideoFileClip, ColorClip, concatenate_videoclips
from transcribers import get_transcript
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def cut_and_subtitle(
    input_video: str,
    transcript: str = None,  
    threshold: float = 0.6,
    start_time: str = None,
    end_time: str = None,
    output_dir: str = "scenes"
) -> list[str]:
    """
    Detect scenes in the input_video using ffmpeg, then cut the video into subclips.
    If transcript is provided, implement subtitles too.

    Returns:
        A list of file paths corresponding to the newly created scene subclips with subtitles.
    """

    try:
        # Convert start_time and end_time to seconds
        start_sec = time_to_seconds(start_time) if start_time else None
        end_sec   = time_to_seconds(end_time)   if end_time   else None
        
        # Detect the scene timestamps
        scene_timestamps = detect_scenes(
            input_video=input_video,
            threshold=threshold,
            start_sec=start_sec,
            end_sec=end_sec
        )

        # Merge short scenes
        if scene_timestamps and scene_timestamps[0] > 0.0:
            scene_timestamps.insert(0, 0.0)
        duration = get_video_duration(input_video)

        if not scene_timestamps or abs(scene_timestamps[-1] - duration) > 0.01:
            scene_timestamps.append(duration)

        scene_timestamps = merge_short_scenes(scene_timestamps, min_scene_length=5.0)

        # Add subtitles to the video
        subtitled_video = add_subtitles_from_transcript(input_video, transcript)

        if not subtitled_video:
            raise Exception("Failed to add subtitles to the video.")

        # Cut the video into subclips
        output_files = cut_video(
            input_video=subtitled_video,
            scene_timestamps=scene_timestamps,
            output_dir=output_dir
        )

        return output_files

    except Exception as e:
        logging.error(f"Error in cut_and_subtitle: {e}")
        return []


def detect_scenes(
    input_video: str,
    threshold: float = 0.6,
    start_sec: float = None,
    end_sec: float = None
) -> list[float]:
    """
    Run ffmpeg scene detection on a given video and return the sorted list of
    timestamps (in seconds) where scene changes occur.
    """

    # Build ffmpeg filter expression
    if start_sec is not None and end_sec is not None:
        scene_filter = (
            f"[0:v]select='between(t,{start_sec},{end_sec})',"
            f"select='gt(scene,{threshold})',metadata=print:file=-"
        )
    else:
        scene_filter = f"select='gt(scene,{threshold})',metadata=print:file=-"

    cmd = [
        "ffmpeg", "-hide_banner", "-i", input_video,
        "-filter_complex", scene_filter,
        "-f", "null", "-"
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        logging.error(f"Error in detect_scenes: {e.stderr}", file=sys.stderr)
        return []

    # Parse output for lines containing "pts_time:"
    timestamps = []
    for line in (result.stdout + result.stderr).splitlines():
        if "pts_time:" in line:
            match = re.search(r"pts_time:([\d\.]+)", line)
            if match:
                timestamps.append(float(match.group(1)))

    # Return sorted list of timestamps
    return sorted(timestamps)


def cut_video(
    input_video: str,
    scene_timestamps: list[float],
    output_dir: str = None
) -> list[str]:
    """
    Given a list of scene timestamps (in seconds) and an input file,
    use ffmpeg to create subclips. Returns a list of output file paths.
    """

    output_files = []
    if not scene_timestamps:
        print("No scene timestamps found. Skipping scene cutting.")
        return output_files

    if output_dir is None:
        # Default to a directory named "scenes" under current working directory.
        output_dir = os.path.join(os.getcwd(), "scenes")

    os.makedirs(output_dir, exist_ok=True)

    # Ensure 0 is at the start
    if scene_timestamps[0] > 0.01:
        scene_timestamps.insert(0, 0.0)

    # Get final duration
    duration = get_video_duration(input_video)
    if not scene_timestamps or abs(scene_timestamps[-1] - duration) > 0.01:
        scene_timestamps.append(duration)

    # We'll create subclips from each consecutive pair of timestamps
    for i in range(len(scene_timestamps) - 1):
        start = scene_timestamps[i]
        end = scene_timestamps[i + 1]
        clip_duration = end - start

        if clip_duration < 0.05:  # skip extremely short segments
            continue

        # Create output filename
        base_name = os.path.splitext(os.path.basename(input_video))[0]
        output_name = f"{base_name}-[{seconds_to_timestr(start).replace(':','-')}]-[{seconds_to_timestr(end).replace(':','-')}].mp4"
        output_path = os.path.join(output_dir, output_name)

        # ffmpeg command
        ffmpeg_path = "/opt/homebrew/Cellar/ffmpeg/7.1_4/bin/ffmpeg"
        # cmd = [
        #     ffmpeg_path, "-nostdin", "-hide_banner", "-y",
        #     #"ffmpeg", "-nostdin", "-hide_banner", "-y",
        #     "-ss", str(start),
        #     "-i", input_video,
        #     "-t", str(clip_duration),
        #     #"-vf", "scale=-1:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
        #     "-c:a", "aac",
        #     #"-c:v", "libx264", "-profile:v", "high",
        #     "-c:v", "mpeg4", "-profile:v", "high",
        #     "-pix_fmt", "yuv420p",
        #     "-movflags", "+faststart",
        #     output_path
        # ]
        cmd = [
        ffmpeg_path, "-nostdin", "-hide_banner", "-y",
        "-ss", str(start),
        "-i", input_video,
        "-t", str(clip_duration),
        "-c:a", "copy",
        "-c:v", "libx264", # Instead of libx264
        output_path
        ]

        logging.info(f"Cutting clip {i+1}/{len(scene_timestamps)-1}: {output_path}")
        try:
            subprocess.run(cmd, check=True)
            output_files.append(output_path)
        except subprocess.CalledProcessError as e:
            print(f"Error cutting segment {i}: {e.stderr}", file=sys.stderr)

    return output_files


def merge_short_scenes(scene_timestamps: list[float], min_scene_length: float) -> list[float]:
    """
    Merge consecutive scene timestamps so that each final segment
    is at least `min_scene_length` seconds.

    Example:
        scene_timestamps = [0.0, 2.0, 5.0, 11.0, 14.0, 20.0]
        min_scene_length = 6.0
        result -> [0.0, 11.0, 20.0]
           Segments: [0..11] (11s) and [11..20] (9s)
    """
    # If nothing to merge, just return
    if not scene_timestamps:
        return []

    # We'll build a new list of merged timestamps
    # Always keep scene_timestamps[0] as the beginning (often 0.0)
    merged = []
    chunk_start = scene_timestamps[0]

    # Loop from the second timestamp onward
    for i in range(1, len(scene_timestamps)):
        current_ts = scene_timestamps[i]
        length = current_ts - chunk_start

        # If we've reached or exceeded the min length, finalize this chunk
        if length >= min_scene_length:
            merged.append(current_ts)
            chunk_start = current_ts  # Start a new segment from here

    # Now handle leftover:
    # The last 'chunk_start' -> scene_timestamps[-1] might still be short.
    # If leftover is below min_scene_length, merge it with the previous segment (if any).
    # That ensures no final piece is too short.
    if merged:
        leftover_length = scene_timestamps[-1] - merged[-1]
        if leftover_length < min_scene_length:
            # Merge with the previous chunk
            merged[-1] = scene_timestamps[-1]
        else:
            # It's a big enough leftover to stand on its own
            merged.append(scene_timestamps[-1])
    else:
        # If merged is empty, that means we never hit min_scene_length inside the loop
        # So the entire video is just one segment from 0..last_timestamp
        merged.append(scene_timestamps[-1])

    return merged



def get_video_duration(input_file: str) -> float:
    """Use ffprobe to get total video duration in seconds."""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        input_file
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    except (subprocess.CalledProcessError, ValueError) as e:
        print(f"Error in get_video_duration: {e}", file=sys.stderr)
        return 0.0


def time_to_seconds(timestr: str) -> float:
    """Convert a string HH:MM:SS or MM:SS or SS to float seconds."""
    if not timestr:
        return 0.0
    parts = timestr.split(":")
    if len(parts) == 3:
        h, m, s = parts
        return float(h) * 3600 + float(m) * 60 + float(s)
    elif len(parts) == 2:
        m, s = parts
        return float(m) * 60 + float(s)
    else:
        return float(parts[0])


def seconds_to_timestr(seconds: float) -> str:
    """Convert float seconds to HH:MM:SS.xxx string."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    # Keep 3 decimal places for partial seconds
    return f"{hours:02}:{minutes:02}:{secs:06.3f}"


def add_subtitles_from_transcript(input_video, transcript):
    """
    Adds subtitles to a video directly from a transcript and saves the output video.

    Parameters:
    - input_video (str): Path to the input video file.
    - transcript (list of dict): List of subtitle entries, where each entry is a dictionary with keys 'start', 'end', and 'text'.
    - output_video (str): Path to save the output video with burned-in subtitles.

    Returns:
    - str: Path to the output video if successful.
    - None: If the process fails.
    """
    try:
        # Load the input video
        video = VideoFileClip(input_video)

        # Generate TextClips for each subtitle
        subtitle_clips = []
        for entry in transcript:
            text_clip = (TextClip(
                text=entry["text"],
                font="Arial", 
                color="white",
                font_size=40,
                stroke_color="black",
                stroke_width=2
            )
            .with_start(entry["start"])  # Set the start time
            .with_end(entry["end"])   # Set the end time
            .with_position(("center", "bottom")))  # Position the subtitle at the bottom center
            subtitle_clips.append(text_clip)
        logging.info(f"Generated {len(subtitle_clips)} subtitle clips.")
        # Combine the video with the subtitle clips
        final_video = CompositeVideoClip([video] + subtitle_clips)

        # Write the final video with subtitles
        input_video_dir = os.path.dirname(input_video)
        input_video_name, input_video_ext = os.path.splitext(os.path.basename(input_video))
        output_path = os.path.join(input_video_dir, f"{input_video_name}_subtitled{input_video_ext}")
        final_video.write_videofile(output_path, codec="libx264", audio_codec="aac")

        return output_path
    except Exception as e:
        logging.error(f"Failed to add subtitles to video: {e}")
        return None
    

def add_periodic_flash_effect(clip: VideoFileClip, interval: int=5, flash_duration:float=0.5, flash_factor:float=1.3):
    """
    Adds a brightness 'flash' every `interval` seconds for `flash_duration` seconds.
    `flash_factor` is how much we brighten (1.0 = no change, 1.3 = 30% brighter).
    """
    duration = clip.duration
    segments = []
    current_start = 0.0
    
    while current_start < duration:
        # Next flash start time:
        next_flash_start = current_start + interval
        # Clip from current_start to next_flash_start (if in range)
        normal_end = min(next_flash_start, duration)
        
        # Normal segment (no effect)
        if normal_end > current_start:
            normal_part = clip.subclipped(current_start, normal_end)
            segments.append(normal_part)
        
        # Now do the flash effect segment
        flash_end = min(next_flash_start + flash_duration, duration)
        if flash_end > normal_end:
            flash_part = clip.subclipped(normal_end, flash_end)

            # Replace the old .fx(...) / .fl_image(...) call with .image_transform(...)
            flash_part = flash_part.image_transform(
                lambda frame: (frame * flash_factor).clip(0, 255)
            )
            segments.append(flash_part)
        current_start = flash_end
    
    return concatenate_videoclips(segments)

def convert_to_vertical_9x16(clip, final_width=1080, final_height=1920):
    """
    Takes a wide clip and outputs a 9:16 vertical clip by cropping the center
    and resizing if needed.
    """
    # Get aspect ratio
    original_ratio = clip.w / clip.h
    vertical_ratio = final_width / final_height  # 1080/1920 = 0.5625

    if original_ratio > vertical_ratio:
        # means the video is 'wider' than 9:16, so we crop the sides
        new_width = int(vertical_ratio * clip.h)
        x_center = (clip.w - new_width) // 2
        # Crop to new_width x clip.h
        cropped = clip.cropped(x1=x_center, y1=0, width=new_width, height=clip.h)
        # then resize if needed
        result = cropped.resized((final_width, final_height))
    else:
        # If original is narrower, we might letterbox or something else.
        # But typically 16:9 -> 9:16 is the main use-case.
        # Let's do a top/bottom crop if needed. Or letterbox.
        # Example: we can fill top/bottom
        new_height = int(clip.w / vertical_ratio)
        y_center = (clip.h - new_height) // 2
        cropped = clip.cropped(x1=0, y1=y_center, width=clip.w, height=new_height)
        result = cropped.resized((final_width, final_height))
    
    return result

# Usage:


# Usage example:
if __name__ == "__main__":
    clip = VideoFileClip("/Users/tulgakagan/Desktop/AI_Lecture_Notes/Software_Engineering/Project/scenes/Impractical_Jokers_-_Top_Presentation_Moments_Mashup_truTV-[00-00-00.000]-[00-02-42.896].mp4")
    clip_with_effect = add_periodic_flash_effect(clip, interval=5, flash_duration=0.4, flash_factor=1.25)
    clip_with_effect.write_videofile("output_with_flash.mp4", codec="mpeg4")
    vertical_clip = convert_to_vertical_9x16(clip)
    vertical_clip.write_videofile("vertical.mp4", codec="libx264")


# def add_animated_text(
#     video_path: str,
#     output_path: str,
#     text: str,
#     font_size: int = 70,
#     duration: float = 5
# ) -> None:
#     """
#     Overlay animated text on top of the video for the given duration.
#     """
#     clip = VideoFileClip(video_path)
#     txt_clip = (TextClip(text, fontsize=font_size, color='white', font='Amiri-Bold')
#                 .set_duration(duration)
#                 .fadein(1)   # 1-second fade-in
#                 .fadeout(1)  # 1-second fade-out
#                 .set_position(('center', 'bottom')))

#     final_clip = CompositeVideoClip([clip, txt_clip])
#     final_clip.write_videofile(output_path, codec='libx264', fps=24, audio_codec='aac')
