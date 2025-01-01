import math
import os
import logging
from moviepy import VideoFileClip, TextClip, CompositeVideoClip
from moviepy.video.tools.subtitles import SubtitlesClip
import pysrt
from typing import Optional
from termcolor import colored


logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def create_srt_from_transcript(transcript, output_dir=None):
    """
    Creates an SRT file from the given transcript.
    Returns the path to the generated SRT file.
    """
    if output_dir is None:
        output_dir = os.getenv("OUTPUT_DIR", "./output")

    os.makedirs(output_dir, exist_ok=True)
    srt_filename = os.path.join(output_dir, "subtitles.srt")

    if os.getenv("TRANSCRIBER") == "assemblyai":
        # AssemblyAI transcripts are already in SRT format
        srt_content = transcript.export_subtitles_srt(chars_per_caption=32)
        # Write the content to the file
        with open(srt_filename, "w", encoding="utf-8") as file:
            file.write(srt_content)
        logging.info(f"SRT file created: {srt_filename}")
        return srt_filename
    

    segments = transcript.get("segments", [])
    def format_srt_timestamp(seconds):
        """
        Converts float seconds into SRT-compatible timestamp: HH:MM:SS,mmm
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds - math.floor(seconds)) * 1000)
        return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"

    try:
        #with open(srt_filename, 'w', encoding='utf-8') as file:
        with open(srt_filename, 'w') as file:
            for i, seg in enumerate(segments, start=1):
                start_time = format_srt_timestamp(seg["start"])
                end_time = format_srt_timestamp(seg["end"])

                file.write(str(i) + "\n")
                file.write(f"{start_time} --> {end_time}\n")
                file.write(seg["text"] + "\n\n")
    except (IOError, KeyError) as e:
        logging.error(f"Error occurred while writing SRT file: {e}")
        raise
    logging.info(colored(f"SRT file created: {srt_filename}", "green"))
    return srt_filename

def burn_subtitles(subtitles_path=None, input_path=None, combined_video_path=None, text_color="white"):
    
    subtitles = SubtitlesClip(subtitles_path, encoding="utf-8")
    result = CompositeVideoClip([
        VideoFileClip(input_path),
        subtitles
        .with_position(('center', 'bottom'))
    ])
    result.write_videofile(combined_video_path, codec="libx264", audio_codec="aac")
    logging.info(f"Subtitled video created: {combined_video_path}")
    # with open(subtitles_path, 'r', encoding='utf-8') as f:
    #     subtitles = SubtitlesClip(f, generator)
    #     result = CompositeVideoClip([
    #     VideoFileClip(input_path),
    #     subtitles.set_position(('center', 'bottom'))
    #     ])
    result.write_videofile(combined_video_path, codec="libx264", audio_codec="aac")
    logging.info(f"Subtitled video created: {combined_video_path}")
    return combined_video_path

def generate_subtitles(input_video, transcript, output_dir="/Users/tulgakagan/Desktop/AI_Lecture_Notes/Software_Engineering/Project/output"):
    """
    Generate subtitles for the given video using Vosk.
    Returns the path to the generated SRT file.
    """
    srt_file = create_srt_from_transcript(transcript, output_dir)
    input_video_dir = os.path.dirname(input_video)
    input_video_name, input_video_ext = os.path.splitext(os.path.basename(input_video))
    output_path = os.path.join(input_video_dir, f"{input_video_name}_subtitled{input_video_ext}")
    burn_subtitles(srt_file, input_video, output_path)
    return output_path

def burn_subtitles_moviepy(input_video, srt_file, output_video):
    """
    Burns subtitles from an SRT file into the input video using MoviePy, creating a new output video.

    Parameters:
    - input_video (str): Path to the input video file.
    - srt_file (str): Path to the SRT file containing subtitles.
    - output_video (str): Path to save the output video with burned-in subtitles.

    Returns:
    - str: Path to the output video if successful.
    - None: If the process fails.
    """

    # Ensure paths exist
    if not os.path.exists(input_video):
        logging.error(f"Input video not found: {input_video}")
        return None
    if not os.path.exists(srt_file):
        logging.error(f"SRT file not found: {srt_file}")
        return None

    try:
        # Load the input video
        video = VideoFileClip(input_video)

        # Create a subtitle generator from the SRT file
        logging.info(f"Doing generator now")
        generator = lambda txt: TextClip(
        txt,
        #font="/Users/tulgakagan/Desktop/AI_Lecture_Notes/Software_Engineering/Project/fonts/Arial.ttf",
        fontsize=100,
        color="white",
        stroke_color="black",
        stroke_width=5,
    )
        logging.info(f"Generator done")
        #generator = lambda txt: TextClip(txt, font="Arial", fontsize=24, color="white", stroke_color="black", stroke_width=2)
        subtitles = SubtitlesClip(srt_file, font="/Users/tulgakagan/Desktop/AI_Lecture_Notes/Software_Engineering/Project/fonts/Times New Roman Bold.ttf")
        logging.info(f"Subtitles done")

        # Overlay subtitles on the video
        video_with_subtitles = CompositeVideoClip([video, subtitles.set_position(('center', 'bottom'))])
        logging.info(f"Composite done")

        # Write the output video with subtitles
        logging.info(f"Writing subtitled video to: {output_video}")
        video_with_subtitles.write_videofile(output_video, codec="libx264", audio_codec="aac")

        # Log success
        logging.info(f"Subtitled video successfully created: {output_video}")
        return output_video

    except Exception as e:
        #Log unexpected errors
        logging.error(f"An unexpected error occurred: {e}")
        return None

    

if __name__ == "__main__":
    # Example usage:
    example_input = "/Users/tulgakagan/Desktop/AI_Lecture_Notes/Software_Engineering/Project/output/Mr._Robot_-_Linux_Desktop_Environment_Wars/Mr._Robot_-_Linux_Desktop_Environment_Wars.mp4"
    #srt_file = "/Users/tulgakagan/Desktop/subtitles.srt"
    srt_file = "/Users/tulgakagan/Desktop/AI_Lecture_Notes/Software_Engineering/Project/output/Mr._Robot_-_Linux_Desktop_Environment_Wars/subtitles.srt"
    example_output = "/Users/tulgakagan/Desktop/AI_Lecture_Notes/Software_Engineering/Project/output/Mr._Robot_-_Linux_Desktop_Environment_Wars/Mr._Robot_-_Linux_Desktop_Environment_Wars_subtitled.mp4"
    burn_subtitles_moviepy(example_input, srt_file, example_output)