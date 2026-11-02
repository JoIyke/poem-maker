import os
import requests
import subprocess

def download_file(url, dest_path):
    """
    Downloads a file from a URL. Rejects it if the server sends an HTML webpage.
    """
    if not url:
        return None
        
    print(f"Downloading {url} to {dest_path}...")
    try:
        # We add a standard User-Agent so cloud providers don't block the request
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, stream=True, timeout=30, headers=headers)
        response.raise_for_status()
        
        # SMART FIX: Check if Google Drive (or others) sent an HTML page instead of a media file
        content_type = response.headers.get('Content-Type', '').lower()
        if 'text/html' in content_type:
            print(f"ERROR: The link {url} returned an HTML webpage instead of a media file!")
            print("Skipping download. (Use direct links like AWS, Imgur, or direct Cloudinary URLs).")
            return None
            
        with open(dest_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                
        return dest_path
    except Exception as e:
        print(f"Failed to download {url}: {e}")
        return None

def create_fallback_image(dest_path, width=1920, height=1080):
    """
    Creates a solid black image using FFmpeg if no image is provided or download fails.
    """
    print(f"Creating fallback black image at {dest_path}")
    cmd = [
        "ffmpeg", "-nostdin", "-y", "-f", "lavfi", "-i", f"color=c=black:s={width}x{height}",
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
        with open(video_path, 'rb') as f:
            files = {'file': (os.path.basename(video_path), f, 'video/mp4')}
            data = {'status': status}
            response = requests.post(webhook_url, files=files, data=data)
            
        print(f"Webhook response: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Failed to send webhook: {e}")
