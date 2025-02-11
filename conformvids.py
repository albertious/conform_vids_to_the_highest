import os
import subprocess
import json

# --------------------
# Configuration
# --------------------
FOLDER_PATH = r"/path/to/your/folder"    # Change to folder containing .mp4 files
OUTPUT_DIR  = os.path.join(FOLDER_PATH, "conformed")  # Where conformed files are saved

# FFmpeg re-encoding parameters (video)
VIDEO_CODEC = "libx264"
CRF_VALUE   = 18            # Lower = better quality (but bigger files). Typically 18-23 is decent.
PRESET      = "medium"      # FFmpeg presets for x264: ultrafast, superfast, veryfast, faster, fast, medium, etc.

# Audio will be copied by default (no re-encoding)
AUDIO_CODEC = "copy"

def main():
    # 1. Gather all MP4 files in the folder
    mp4_files = [f for f in os.listdir(FOLDER_PATH) if f.lower().endswith(".mp4")]
    if not mp4_files:
        print(f"No MP4 files found in {FOLDER_PATH}")
        return
    
    # 2. Find the file with the highest resolution
    #    We'll define "highest resolution" as the largest (width * height).
    max_pixels = 0
    max_res_file = None
    max_width = 0
    max_height = 0

    for filename in mp4_files:
        full_path = os.path.join(FOLDER_PATH, filename)
        # Probe resolution using ffprobe (JSON output)
        width, height = get_video_resolution(full_path)
        if width * height > max_pixels:
            max_pixels = width * height
            max_res_file = filename
            max_width = width
            max_height = height

    if not max_res_file:
        print("Could not determine a max resolution file.")
        return

    print(f"Highest resolution file: {max_res_file} ({max_width}x{max_height} = {max_pixels} pixels)")

    # 3. Create output directory if it doesn't exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 4. For each file, conform to the highest resolution
    for filename in mp4_files:
        full_path = os.path.join(FOLDER_PATH, filename)
        output_path = os.path.join(OUTPUT_DIR, filename)

        # Skip re-encoding if it's the max file itself (optional; you can also re-encode everything).
        if filename == max_res_file:
            print(f"Skipping {filename} because it already has the highest resolution.")
            # Optionally copy the file as-is or do nothing
            # subprocess.run(["cp", full_path, output_path])  # For Unix-like systems
            continue

        print(f"Re-encoding {filename} to match resolution {max_width}x{max_height} ...")

        # FFmpeg command to scale to max_width x max_height
        # -vf scale=W:H -> forcibly scale the input to that resolution
        cmd = [
            "ffmpeg",
            "-y",                 # Overwrite without asking
            "-i", full_path,
            "-vf", f"scale={max_width}:{max_height}",
            "-c:v", VIDEO_CODEC,
            "-preset", PRESET,
            "-crf", str(CRF_VALUE),
            "-c:a", AUDIO_CODEC,
            output_path
        ]
        subprocess.run(cmd)

    print("Done! Conformed files are in:", OUTPUT_DIR)

def get_video_resolution(file_path):
    """
    Returns (width, height) of the first video stream using ffprobe JSON.
    """
    # ffprobe command to get streams in JSON
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "json",
        file_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error running ffprobe on {file_path}: {result.stderr}")
        return (0, 0)

    try:
        data = json.loads(result.stdout)
        width  = data["streams"][0]["width"]
        height = data["streams"][0]["height"]
        return (int(width), int(height))
    except Exception as e:
        print(f"Could not parse resolution for {file_path}: {e}")
        return (0, 0)

if __name__ == "__main__":
    main()
