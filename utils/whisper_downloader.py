from whisper import _download, _MODELS
import os

# models = ["tiny.en", "tiny", "base.en", "base", "small.en", "small", "medium.en", "medium", "large"]

# for model in models:
#     model_path = os.path.join("/Users/tulgakagan/Desktop/AI_Lecture_Notes/Software Engineering/Project/utils/models", model)
#     if not os.path.exists(model_path):
#         _download(_MODELS[model], "/Users/tulgakagan/Desktop/AI_Lecture_Notes/Software Engineering/Project/utils/models", False)
#     else:
#         print(f"Model {model} already exists at {model_path}")

from whisper import _download, _MODELS
import whisper

models = whisper.available_models()

for model in models:
    _download(_MODELS[model], "~/.cache/whisper", False)
