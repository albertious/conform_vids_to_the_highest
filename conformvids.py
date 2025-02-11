import os
import subprocess
import json

# --------------------
# Configuration
# --------------------
FOLDER_PATH = r"/path/to/your/folder"            # Folder containing .mp4 files
OUTPUT_DIR  = os.path.join(FOLDER_PATH, "output")  # Where output files go

# --------------------
# GPU Settings
# --------------------
USE_GPU = True               # Set to True to use GPU if available, False to use CPU
GPU_ENCODER = "h264_nvenc"   # Example for NVIDIA. Could be "hevc_nvenc", "h264_qsv" (Intel), "h264_amf" (AMD), etc.

# --------------------
# CPU (libx264) Settings
# --------------------
VIDEO_CODEC = "libx264"
CRF_VALUE   = 18       # Lower = higher quality. Typically 18-23 for H.264
PRESET      = "medium" # ultrafast, superfast, veryfast, faster, fast, medium, slow, etc.

# --------------------
# Audio Settings
# --------------------
AUDIO_CODEC = "copy"   # "copy" keeps original audio. Or use "aac", "ac3", etc.

def main():
    # 1. Gather all MP4 files
    mp4_files = [f for f in os.listdir(FOLDER_PATH) if f.lower().endswith(".mp4")]
    if not mp4_files:
        print(f"No MP4 files found in {FOLDER_PATH}")
        return

    # 2. Find the file with the highest resolution
    max_pixels = 0
    max_width, max_height = 0, 0
    max_res_file = None

    for filename in mp4_files:
        full_path = os.path.join(FOLDER_PATH, filename)
        w, h = get_video_resolution(full_path)
        if w * h > max_pixels:
            max_pixels = w * h
            max_width, max_height = w, h
            max_res_file = filename

    if not max_res_file:
        print("Could not determine a file with the highest resolution.")
        return

    print(f"Highest resolution: {max_width}x{max_height} ({max_pixels} pixels), from file: {max_res_file}")

    # 3. Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 4. Process each file
    for filename in mp4_files:
        full_path = os.path.join(FOLDER_PATH, filename)
        output_path = os.path.join(OUTPUT_DIR, filename)

        w, h = get_video_resolution(full_path)

        # If resolution already matches the highest, do pass-through copy
        if w == max_width and h == max_height:
            print(f"File {filename} matches the highest resolution ({w}x{h}). Doing pass-through (copy).")
            cmd = [
                "ffmpeg",
                "-y",
                "-i", full_path,
                "-c", "copy",  # Copy video & audio
                output_path
            ]
            subprocess.run(cmd)
        else:
            # Otherwise, scale to the highest resolution
            print(f"Scaling {filename} from {w}x{h} to {max_width}x{max_height} ...")

            # Choose the appropriate video encoder settings
            if USE_GPU:
                # GPU-based encoder command
                video_encoder_args = [
                    "-c:v", GPU_ENCODER,
                    # Some GPU encoders support special presets, e.g. "-preset", "p5" for NVENC
                    # If you want to specify a preset for NVENC, do something like:
                    # "-preset", "p4",   # or llhq, llhp, etc. (depends on your FFmpeg build)
                ]
                # For NVENC, you might also want to set a bitrate or qp. CRF is not always standard for NVENC.
                # Example: "-b:v", "5M" for 5 Mbps
            else:
                # CPU-based encoder command
                video_encoder_args = [
                    "-c:v", VIDEO_CODEC,
                    "-preset", PRESET,
                    "-crf", str(CRF_VALUE),
                ]

            cmd = [
                "ffmpeg",
                "-y",
                "-i", full_path,
                "-vf", f"scale={max_width}:{max_height}"
            ] + video_encoder_args + [
                "-c:a", AUDIO_CODEC,
                output_path
            ]

            subprocess.run(cmd)

    print("Done! Check the 'output' folder for conformed files.")

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
        print(f"FFprobe error on {file_path}: {result.stderr}")
        return (0, 0)

    try:
        data = json.loads(result.stdout)
        width = data["streams"][0]["width"]
        height = data["streams"][0]["height"]
        return (int(width), int(height))
    except Exception as e:
        print(f"Error parsing resolution for {file_path}: {e}")
        return (0, 0)

if __name__ == "__main__":
    main()
