import os
import requests
import subprocess

def download_file(url, dest_path):
    """
    Downloads a file from a URL to a local path.
    Returns the path if successful, None if it fails.
    """
    if not url:
        return None
        
    print(f"Downloading {url} to {dest_path}...")
    try:
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        with open(dest_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return dest_path
    except Exception as e:
        print(f"Failed to download {url}: {e}")
        return None

def create_fallback_image(dest_path, width=1920, height=1080):
    """
    Creates a solid black image using FFmpeg if no image is provided.
    """
    print(f"Creating fallback black image at {dest_path}")
    cmd = [
        "ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c=black:s={width}x{height}",
        "-vframes", "1", dest_path
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return dest_path

def send_webhook(webhook_url, video_path, status="success"):
    """
    Sends the final video file back to the n8n webhook.
    """
    if not webhook_url:
        print("No webhook URL provided. Skipping delivery.")
        return
        
    print(f"Sending video to n8n webhook: {webhook_url}")
    try:
        # We send it as multipart/form-data so n8n can receive it as a binary file
        with open(video_path, 'rb') as f:
            files = {'file': (os.path.basename(video_path), f, 'video/mp4')}
            data = {'status': status}
            response = requests.post(webhook_url, files=files, data=data)
            
        print(f"Webhook response: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Failed to send webhook: {e}")
