import re
import subprocess
import logging
import sys

def detect_scenes(
    input_video: str,
    threshold: float = 0.8,
    start_sec: float = None,
    end_sec: float = None
) -> list[float]:
    """
    Run ffmpeg scene detection on a given video and return the sorted list of
    timestamps (in seconds) where scene changes occur.
    Args:
        input_video (str): Path to the input video file.
        threshold (float): The threshold for scene change detection. The higher the value, the less sensitive the detection.
        start_sec (float): Start time in seconds for scene detection.
        end_sec (float): End time in seconds for scene detection.
    Returns:
        List[float]: A sorted list of timestamps where scene changes occur.
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

    logging.info(f"Running ffmpeg scene detection for {input_video}...")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        logging.error(f"Error in detect_scenes: {e.stderr}", file=sys.stderr)
        return []
    logging.info("Scene detection complete. Parsing timestamps...")
    # Parse output for lines containing "pts_time:"
    timestamps = []
    for line in (result.stdout + result.stderr).splitlines():
        if "pts_time:" in line:
            match = re.search(r"pts_time:([\d\.]+)", line)
            if match:
                timestamps.append(float(match.group(1)))
    timestamps = sorted(timestamps)

    if timestamps and timestamps[0] > 0.0:
        timestamps.insert(0, 0.0)
    duration = get_video_duration(input_video)

    if not timestamps or abs(timestamps[-1] - duration) > 0.01:
        timestamps.append(duration)
    
    if len(timestamps) == 1:
        logging.info("No scene changes detected. Splitting the video into 60-second clips.")
        timestamps = [0.0, duration]

    timestamps = merge_short_scenes(timestamps, min_scene_length=20.0)
    logging.debug(f"Scene timestamps after merging: {timestamps}")
    timestamps = split_long_scenes(timestamps)
    logging.debug(f"Scene timestamps after splitting: {timestamps}")

    logging.info(f"Scene timestamps created. Total scenes: {len(timestamps)-1}")

    logging.debug(f"First scene starts at {timestamps[0]}s, ends at {timestamps[1]}s.")
    return timestamps

def merge_short_scenes(scene_timestamps: list[float], min_scene_length: float) -> list[float]:
    """
    Merge consecutive scene timestamps so that each final segment
    is at least `min_scene_length` seconds.
    """
    if not scene_timestamps:
        return []

    # ALWAYS include the first timestamp in merged
    merged = [scene_timestamps[0]]
    chunk_start = scene_timestamps[0]

    for i in range(1, len(scene_timestamps)):
        current_ts = scene_timestamps[i]
        length = current_ts - chunk_start

        if length >= min_scene_length:
            # We have a big enough chunk => finalize it by adding the boundary
            merged.append(current_ts)
            chunk_start = current_ts

    # Now handle leftover from the last finalized boundary to the very end
    # If the leftover segment is short, merge it into the previous boundary.
    # Otherwise, treat it as a separate boundary.
    if len(merged) > 0:
        leftover_length = scene_timestamps[-1] - merged[-1]
        if leftover_length < min_scene_length:
            # Merge into previous
            merged[-1] = scene_timestamps[-1]
        else:
            # It's big enough to stand as its own boundary
            merged.append(scene_timestamps[-1])
    else:
        # If merged is still empty, it means no chunk ever reached min_scene_length.
        # We'll just call the entire clip one segment from 0 to last_timestamp.
        merged.append(scene_timestamps[-1])

    return merged

def split_long_scenes(timestamps: list[float]) -> list[float]:
    """
    Takes a list of timestamps where the gap between each timestamp represents a scene.
    Splits scenes longer than 60 seconds into separate scenes.

    Args:
        timestamps (List[float]): A list of timestamps in seconds.

    Returns:
        List[float]: A new list of timestamps with long scenes split into shorter scenes.
    """
    if not timestamps:
        return []

    new_timestamps = [timestamps[0]]  # Start with the first timestamp

    for i in range(1, len(timestamps)):
        start = timestamps[i - 1]
        end = timestamps[i]

        # Check if the scene duration exceeds 60 seconds
        while end - start > 60:
            # Add a new timestamp 60 seconds after the start
            start += 60
            new_timestamps.append(start)

        new_timestamps.append(end)
    logging.debug(f"Split long scenes into {len(new_timestamps)-1} scenes.")
    return new_timestamps

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