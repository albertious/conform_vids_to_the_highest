import os
import subprocess
import json

# --------------------
# Configuration
# --------------------
FOLDER_PATH = r"/path/to/your/folder"    # Folder containing .mp4 files
OUTPUT_DIR  = os.path.join(FOLDER_PATH, "conformed")  # Output folder

# Default fallback encoders if we detect a certain codec name in the highest-res file
CODEC_MAP = {
    "h264": "libx264",
    "hevc": "libx265",
    "vp9":  "libvpx-vp9",
    # Add more if needed
}

# If the detected codec isn’t in CODEC_MAP, we’ll use this fallback
DEFAULT_VIDEO_ENCODER = "libx264"

# For video re-encoding quality
CRF_VALUE   = 18       # Lower = higher quality (larger file). Common range is 18–23 for x264/x265
PRESET      = "medium" # FFmpeg presets: ultrafast, superfast, veryfast, faster, fast, medium, slow, etc.

# Audio: either copy original or re-encode
AUDIO_CODEC = "copy"   # or "aac", "libopus", etc.

def main():
    # 1. Gather MP4 files
    mp4_files = [f for f in os.listdir(FOLDER_PATH) if f.lower().endswith(".mp4")]
    if not mp4_files:
        print(f"No MP4 files found in {FOLDER_PATH}")
        return

    # 2. Find the file with highest resolution
    max_pixels = 0
    max_res_file = None
    max_width, max_height = 0, 0

    for filename in mp4_files:
        full_path = os.path.join(FOLDER_PATH, filename)
        w, h = get_video_resolution(full_path)
        if w * h > max_pixels:
            max_pixels = w * h
            max_res_file = filename
            max_width, max_height = w, h

    if not max_res_file:
        print("Could not determine a file with the highest resolution.")
        return

    # 3. Detect the highest-res file’s video codec name
    highest_codec = detect_video_codec(os.path.join(FOLDER_PATH, max_res_file))
    print(f"Highest resolution file: {max_res_file} ({max_width}x{max_height} => {max_pixels} px)")
    print(f"Detected codec: {highest_codec}")

    # Map the detected codec to an FFmpeg encoder, or use default
    video_encoder = CODEC_MAP.get(highest_codec, DEFAULT_VIDEO_ENCODER)
    print(f"Using video encoder: {video_encoder}")

    # 4. Make output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 5. Re-encode each file to match resolution and (roughly) the same codec family
    for filename in mp4_files:
        full_path = os.path.join(FOLDER_PATH, filename)
        output_path = os.path.join(OUTPUT_DIR, filename)

        # Skip re-encoding for the max file if you wish
        if filename == max_res_file:
            print(f"Skipping re-encoding of {filename} (already highest resolution).")
            # Either copy the file directly to OUTPUT_DIR or do nothing:
            # shutil.copy2(full_path, output_path)
            continue

        print(f"Re-encoding {filename} to {max_width}x{max_height} using {video_encoder}...")

        cmd = [
            "ffmpeg",
            "-y",
            "-i", full_path,
            # Scale filter
            "-vf", f"scale={max_width}:{max_height}",
            # Video encoding
            "-c:v", video_encoder,
            "-preset", PRESET,
            "-crf", str(CRF_VALUE),
            # Audio settings
            "-c:a", AUDIO_CODEC,
            output_path
        ]
        subprocess.run(cmd)

    print("Done! Check the 'conformed' folder for results.")

def get_video_resolution(file_path):
    """Return (width, height) of the first video stream using ffprobe JSON."""
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
        return (0, 0)
    try:
        data = json.loads(result.stdout)
        width  = data["streams"][0]["width"]
        height = data["streams"][0]["height"]
        return (int(width), int(height))
    except:
        return (0, 0)

def detect_video_codec(file_path):
    """Return the codec_name (e.g. 'h264', 'hevc', 'mpeg4', 'vp9') of the first video stream."""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=codec_name",
        "-of", "json",
        file_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return None
    try:
        data = json.loads(result.stdout)
        return data["streams"][0]["codec_name"]
    except:
        return None

if __name__ == "__main__":
    main()
