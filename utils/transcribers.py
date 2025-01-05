import whisper
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
import logging
from urllib.parse import urlparse, parse_qs
import wave
import json
import vosk
import os
import assemblyai as aai
import ffmpeg
import utils.config as config
# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
assemblyai_key = config.ASSEMBLYAI_API_KEY
def youtube_url_to_id(video_url: str) -> str:
    """
    Extract the video ID from a YouTube URL.
    This is a simple method; you may use regex or urllib for more robust parsing.
    """
    if not video_url:
        logging.warning("No video URL provided.")
        return None
    parsed_url = urlparse(video_url)
    if parsed_url.hostname == 'youtu.be':
        return parsed_url.path[1:]
    elif parsed_url.hostname in ('www.youtube.com', 'youtube.com'):
        return parse_qs(parsed_url.query).get('v', [None])[0]
    else:
        logging.error(f"Invalid YouTube URL: {video_url}")
        return None

def fetch_official_transcript(video_id: str, language_code: str = "en") -> list:
    """
    Fetch the official transcript of a YouTube video.
    """
    if not video_id:
        logging.warning("No video ID provided.")
        return None
    try:
        transcripts = YouTubeTranscriptApi.list_transcripts(video_id)
        # transcripts is a TranscriptList, we can iterate
        for t in transcripts:
            # If we want specifically non-auto-generated in English
            if t.language_code == language_code and not t.is_generated:
                segments = []
                for entry in t.fetch():
                    start = entry['start']
                    duration = entry['duration']
                    text = entry['text']
                    segments.append({
                        "start": start,
                        "end": start + duration,
                        "text": text
                    })
                #transcript = {"segments": segments}
                return segments
        logging.info(f"No official transcript found for video {video_id}")
        return []
    except (TranscriptsDisabled, NoTranscriptFound) as e:
        logging.info(f"No official transcript found for video {video_id}: {e}")
        return []
    except Exception as e:
        logging.error(f"Failed to fetch official transcript: {e}")
        return []

def extract_audio(video_path: str, output_dir: str = "output") -> str:
    """
    Extract audio from a video using ffmpeg. Return the audio file path.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    base_name = os.path.splitext(os.path.basename(video_path))[0]
    audio_path = os.path.join(output_dir, f"{base_name}/{base_name}.wav")

    try:
        (
            ffmpeg
            .input(video_path)
            .output(audio_path, acodec="pcm_s16le", ac=1, ar="16k")
            .overwrite_output()
            .run(quiet=True)
        )
        logging.info(f"Audio extracted successfully: {audio_path}")
        return audio_path
    except ffmpeg.Error as e:
        logging.error(f"FFmpeg failed to extract audio: {e.stderr.decode()}")
        # Raise error and interrupt the process.
        raise ValueError(f"FFmpeg failed to extract audio. {e.stderr.decode()}")

def transcribe_audio_whisper(audio_path: str, model_name: str = None) -> list:
    """
    Transcribe audio using Whisper and return subtitle-ready segments.
    """
    if model_name is None:
        model_name = "small"
        logging.info(f"No Whisper model specified. Using default model instead.")
    logging.info(f"Loading Whisper model: {model_name}")
    model = whisper.load_model(model_name)
    logging.info(f"Starting Whisper transcription for {audio_path} with model {model_name}")
    try:
        result = model.transcribe(audio_path, word_timestamps=False)
        logging.info(f"Whisper transcription completed.")
        segments = []
        for segment in result["segments"]:
            segments.append({
            "start": segment["start"],
            "end": segment["end"],
            "text": segment["text"]
        })
        return segments
    except Exception as e:
        logging.error(f"Whisper transcription failed: {e}")
        return []

def transcribe_audio_vosk(audio_path: str, model_name: str = None) -> list[dict]:
    """
    Transcribe audio using Vosk and return subtitle-ready segments.
    """
    # Load model and open WAV file
    if model_name is None:
        model_name = "vosk-model-small-en-us-0.15"
        logging.info(f"No Vosk model specified. Using default model instead.")
        
    logging.info(f"Starting Vosk transcription for {audio_path} with model {model_name}")
    model_path = os.path.join(config.VOSK_DIRECTORY, model_name)
    model = vosk.Model(model_path)

    wf = wave.open(audio_path, "rb")

    # Validate WAV file format
    if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getframerate() not in (8000, 16000, 32000, 44100, 48000):
        logging.error("Audio file must be WAV mono PCM (16-bit) with a supported sample rate.")
        raise ValueError("Audio file must be WAV mono PCM (16-bit) with a supported sample rate.")

    # Initialize recognizer
    rec = vosk.KaldiRecognizer(model, wf.getframerate())
    rec.SetWords(True)

    segments = []

    # Process audio frames
    while True:
        data = wf.readframes(4000)
        if len(data) == 0:
            break
        if rec.AcceptWaveform(data):
            result = json.loads(rec.Result())
            if "result" in result:
                for word in result["result"]:
                    segments.append({
                        "start": word["start"],
                        "end": word["end"],
                        "text": word["word"]
                    })

    # Process remaining buffer
    final_result = json.loads(rec.FinalResult())
    if "result" in final_result and final_result["result"]:  # Check for 'result' key and ensure it's not empty
        for word in final_result["result"]:
            segments.append({
                "start": word["start"],
                "end": word["end"],
                "text": word["word"]
            })

    wf.close()
    logging.info(f"Vosk transcription completed for {audio_path}")
    return segments

def transcribe_audio_assemblyai(audio_path: str) -> list[dict]:
    """
    Transcribe audio using AssemblyAI API.
    """
    try:
        # Set the API key from the environment
        aai.settings.api_key = assemblyai_key

        config = aai.TranscriptionConfig(speech_model=aai.SpeechModel.nano)

        transcriber = aai.Transcriber(config=config)
        transcript = transcriber.transcribe(audio_path)
        if transcript.status == aai.TranscriptStatus.error:
            logging.error(f"AssemblyAI transcription failed: {transcript.error}")
            return []
        segments = []
        for word in transcript.words:
            segments.append({
                    "start": word.start / 1000,
                    "end": word.end / 1000,
                    "text": word.text
                })
        return segments
    except Exception as e:
        logging.error(f"AssemblyAI transcription failed: {e}")
        return []
def get_transcript(downloaded_path: str, video_url: str = None, transcriber: str = "vosk", model: str = None) -> list[dict]:
    """
    Get the transcript of a video using
    - Official YouTube transcript (if available)
    - Vosk (default)
    - Whisper
    - AssemblyAI
    Args:
        downloaded_path: str: Path to the downloaded video file.
        video_url: str: URL of the video to transcribe.
    
    Returns:
        list[dict]: A list of subtitle-ready segments with start, end, and text
    """
    # Check if video_url contains a valid YouTube URL
    if "youtube.com" not in video_url:
        #logging.warning("Input is not a YouTube link. Skipping official transcript check.")
        video_url = None
    # Check if the video has an official transcript
    video_id = youtube_url_to_id(video_url)
    transcript = fetch_official_transcript(video_id)
    if transcript:
        logging.info("Using official YouTube transcript.")
    else:
        if transcriber not in ["whisper", "vosk", "assemblyai"]:
            logging.error("Invalid transcriber specified. Exiting.")
            return
        
        # Extracting Audio
        logging.info("Extracting audio from video...")
        audio_path = extract_audio(downloaded_path)
        if not audio_path:
            logging.error("Could not extract audio. Exiting.")
            return
        
        # Transcribing Audio

        if transcriber == "assemblyai":
            logging.info("Transcribing audio with AssemblyAI...")
            transcript = transcribe_audio_assemblyai(audio_path)
        elif transcriber == "vosk":
            transcript = transcribe_audio_vosk(audio_path, model_name=model)
            return transcript
        else:
            logging.info("Transcribing audio with Whisper...")
            transcript = transcribe_audio_whisper(audio_path, model_name=model)
    
    return transcript