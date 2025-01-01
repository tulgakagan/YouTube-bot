import re
import subprocess
import logging
import os
import sys
from datetime import datetime
from transcribers import transcribe_audio_whisper, extract_audio
from processors import add_subtitles_from_transcript

def cut_into_scenes(
    input_video: str,
    transcript: str = None,  
    threshold: float = 0.3,
    start_time: str = None,
    end_time: str = None,
    output_dir: str = "scenes"
) -> list[str]:
    """
    Detect scenes in the input_video using ffmpeg, then cut the video into subclips.
    If transcript is provided, you could incorporate logic to also split or overlay
    transcripts for each clip.

    Returns:
        A list of file paths corresponding to the newly created scene subclips.
    """

    # 1) Convert start_time and end_time to seconds
    start_sec = time_to_seconds(start_time) if start_time else None
    end_sec   = time_to_seconds(end_time)   if end_time   else None
    
    # 2) Detect the scene timestamps
    scene_timestamps = detect_scenes(
        input_video=input_video,
        threshold=threshold,
        start_sec=start_sec,
        end_sec=end_sec
    )

    # 3) Merge short scenes
    if scene_timestamps and scene_timestamps[0] > 0.0:
        scene_timestamps.insert(0, 0.0)
    duration = get_video_duration(input_video)

    if not scene_timestamps or abs(scene_timestamps[-1] - duration) > 0.01:
        scene_timestamps.append(duration)

    scene_timestamps_merged = merge_short_scenes(scene_timestamps, min_scene_length=5.0)

    
    # 4) Cut the video into subclips
    output_files = cut_video(
        input_video=input_video,
        scene_timestamps=scene_timestamps_merged,
        output_dir=output_dir
    )

    # 4) (Optional) If transcript is provided, do extra logic here
    #    e.g., splitting transcripts by scene timestamps, overlaying subtitles, etc.

    return output_files


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
        print(f"Error in detect_scenes: {e.stderr}", file=sys.stderr)
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
        # cmd = [
        #     "ffmpeg", "-nostdin", "-hide_banner", "-y",
        #     "-ss", str(start),
        #     "-i", input_video,
        #     "-t", str(clip_duration),
        #     "-c:a", "aac",
        #     "-c:v", "libx264", "-profile:v", "high",
        #     "-pix_fmt", "yuv420p",
        #     "-movflags", "+faststart",
        #     output_path
        # ]
        cmd = [
        "ffmpeg", "-nostdin", "-hide_banner", "-y",
        "-ss", str(start),
        "-i", input_video,
        "-t", str(clip_duration),
        "-c:v", "copy",  # Instead of libx264
        "-c:a", "copy",
        output_path
        ]


        print(f"Cutting clip {i+1}/{len(scene_timestamps)-1}: {output_path}")
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

if __name__ == "__main__":
    # Example usage
    input_video = "/Users/tulgakagan/Desktop/AI_Lecture_Notes/Software_Engineering/Project/output/Mr._Robot_-_Linux_Desktop_Environment_Wars/Mr._Robot_-_Linux_Desktop_Environment_Wars.mp4"
    input = "/Users/tulgakagan/Desktop/AI_Lecture_Notes/Software_Engineering/Project/output/Impractical_Jokers_-_Top_Presentation_Moments_Mashup_truTV/Impractical_Jokers_-_Top_Presentation_Moments_Mashup_truTV.mp4"
    cut_into_scenes(input, threshold=0.8, output_dir="scenes")

# if __name__ == "__main__":
#     # Example usage
#     input_video = "/Users/tulgakagan/Desktop/AI_Lecture_Notes/Software_Engineering/Project/output/Mr._Robot_-_Linux_Desktop_Environment_Wars/Mr._Robot_-_Linux_Desktop_Environment_Wars.mp4"
#     input = "/Users/tulgakagan/Desktop/AI_Lecture_Notes/Software_Engineering/Project/output/Why_we_all_need_subtitles_now/Why_we_all_need_subtitles_now.mp4"
#     scenes = cut_into_scenes(input_video, threshold=0.8, output_dir="scenes")
#     i = 0
#     for scene in scenes:
#         audio = extract_audio(scene)
#         transcript = transcribe_audio_whisper(audio)
#         add_subtitles_from_transcript(scene, transcript)
#         logging.info(f"Subtitled video successfully created for scene {i} of {len(scenes)}")
#         i += 1






# def detect_scenes(input_video, threshold=0.4):
#     """
#     Detects scene change timestamps using FFmpeg's scene detection filter.
#     Returns a sorted list of scene change timestamps in seconds.
#     """
#     logging.basicConfig(level=logging.INFO)
#     logger = logging.getLogger(__name__)

#     cmd = [
#         "ffmpeg",
#         "-i", input_video,
#         "-vf", f"select='gt(scene,{threshold})',showinfo",
#         "-f", "null",
#         "-"
#     ]

#     try:
#         process = subprocess.Popen(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
#         timestamps = [0.0]  # Start at 0 seconds
#         scene_regex = r"pts_time:([\d\.]+)"

#         for line in process.stderr:
#             match = re.search(scene_regex, line)
#             if match:
#                 timestamps.append(float(match.group(1)))

#         process.wait()
#         if process.returncode != 0:
#             logger.error(f"FFmpeg process failed with return code {process.returncode}")
#             return []

#         return sorted(list(set(timestamps)))

#     except FileNotFoundError:
#         logger.error("FFmpeg executable not found. Please ensure FFmpeg is installed and in your PATH.")
#         return []
#     except Exception as e:
#         logger.error(f"An error occurred: {e}")
#         return []
