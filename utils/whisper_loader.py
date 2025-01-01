import whisper
import torch
import os
import sys

# Saving the model to the models directory
def whisper_saver(model_name: str):
    """
    Load the specified Whisper model and save it to the models directory.
    Returns the path of the saved model.
    """
    models = {"tiny", "base", "small", "medium", "large", "turbo"}
    if model_name not in models:
        print(f"Model not found: {model_name}")
        return None
    
    save_dir = "/Users/tulgakagan/Desktop/AI_Lecture_Notes/Software Engineering/Project/utils/models"
    os.makedirs(save_dir, exist_ok=True)  # Create directory if it doesn't exist
    model_path = os.path.join(save_dir, f"whisper_{model_name}.pth")
    if os.path.exists(model_path):
        print(f"Model file already exists: {model_path}")
        return model_path
    
    model = whisper.load_model(model_name)
    # Save the model weights in the specified directory
    torch.save(model.state_dict(), model_path)
    return model_path

if __name__ == "__main__":
    model_name = sys.argv[1] if len(sys.argv) > 1 else "base"
    model_path = whisper_saver(model_name)
    print(f"Model saved at: {model_path}")