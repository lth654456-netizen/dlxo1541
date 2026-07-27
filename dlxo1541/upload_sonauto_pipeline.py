import os
import time
import pickle
import cv2
import requests
import numpy as np
from google.auth.transport.requests import Request
from googleapiclient.http import MediaFileUpload
import googleapiclient.discovery
import googleapiclient.errors

try:
    from moviepy import VideoFileClip, AudioFileClip
except ImportError:
    from moviepy.editor import VideoFileClip, AudioFileClip

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
BASE_URL = "https://api.sonauto.ai/v1"

def load_env():
    env_path = '.env'
    if os.path.exists(env_path):
        print("Loading environment variables from .env file...")
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    if '=' in line:
                        key, val = line.split('=', 1)
                        os.environ[key.strip()] = val.strip()

def get_sonauto_headers():
    api_key = os.environ.get("SONAUTO_API_KEY")
    if not api_key:
        raise Exception("Error: SONAUTO_API_KEY is not set in .env file.")
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

def generate_sonauto_music(output_path, prompt="A bright, upbeat electronic pop background track"):
    print("Initiating music generation via Sonauto AI...")
    headers = get_sonauto_headers()
    
    payload = {
        "prompt": prompt,
        "instrumental": True,
        "num_songs": 1
    }
    
    # 1. Post generation request
    res = requests.post(f"{BASE_URL}/generations", headers=headers, json=payload)
    if res.status_code != 200:
        raise Exception(f"Failed to submit generation request: {res.status_code} - {res.text}")
        
    res_data = res.json()
    task_id = res_data.get("id") or res_data.get("task_id")
    if not task_id:
        raise Exception(f"Failed to retrieve task ID from response: {res_data}")
        
    print(f"Generation task started. Task ID: {task_id}")
    
    # 2. Poll for status
    prev_status = None
    while True:
        status_res = requests.get(f"{BASE_URL}/generations/status/{task_id}", headers=headers)
        if status_res.status_code != 200:
            print(f"Warning: Failed to fetch status. Code: {status_res.status_code}")
            time.sleep(5)
            continue
            
        status = status_res.text.strip('"')
        if status != prev_status:
            print(f"Current Status: {status}")
            prev_status = status
            
        if status == "SUCCESS":
            break
        elif status == "FAILURE":
            raise Exception("Sonauto generation task failed on the server.")
            
        time.sleep(5)
        
    # 3. Retrieve final song paths
    result_res = requests.get(f"{BASE_URL}/generations/{task_id}", headers=headers)
    if result_res.status_code != 200:
        raise Exception(f"Failed to fetch final generation results: {result_res.status_code} - {result_res.text}")
        
    result_data = result_res.json()
    song_paths = result_data.get("song_paths", [])
    if not song_paths:
        # Fallback to check other potential result keys
        song_paths = result_data.get("urls") or result_data.get("audio_urls") or []
        if not song_paths and "song_path" in result_data:
            song_paths = [result_data["song_path"]]
            
    if not song_paths:
        raise Exception(f"No audio file paths found in result data: {result_data}")
        
    song_url = song_paths[0]
    print(f"Downloading generated song from: {song_url}")
    
    # 4. Download audio file
    audio_res = requests.get(song_url)
    if audio_res.status_code != 200:
        raise Exception(f"Failed to download audio file: {audio_res.status_code}")
        
    with open(output_path, 'wb') as f:
        f.write(audio_res.content)
        
    print(f"Music successfully downloaded and saved to {output_path}")

def generate_blue_video(output_path, duration, fps=30, width=1280, height=720):
    print(f"Generating {duration}-second blue video...")
    blue_frame = np.zeros((height, width, 3), dtype=np.uint8)
    blue_frame[:] = [255, 0, 0] # BGR color: Blue is [255, 0, 0]
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    num_frames = int(duration * fps)
    for _ in range(num_frames):
        out.write(blue_frame)
        
    out.release()
    print(f"Video saved to {output_path}")

def merge_audio_video(video_path, audio_path, output_path):
    print("Merging video and audio using MoviePy...")
    video_clip = VideoFileClip(video_path)
    audio_clip = AudioFileClip(audio_path)
    
    # Use version-agnostic method to set audio
    if hasattr(video_clip, "with_audio"):
        video_clip = video_clip.with_audio(audio_clip)
    else:
        video_clip = video_clip.set_audio(audio_clip)
        
    video_clip.write_videofile(output_path, codec="libx264", audio_codec="aac")
    
    # Close resources
    video_clip.close()
    audio_clip.close()
    print(f"Final video saved to {output_path}")

def get_authenticated_service():
    creds = None
    token_path = 'token.pickle'
    client_secrets_path = 'client_secrets.json'
    
    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)
            
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing expired credentials...")
            creds.refresh(Request())
        else:
            print("Initiating OAuth2 authentication flow...")
            flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
                client_secrets_path, SCOPES)
            creds = flow.run_local_server(host='localhost', port=8080)
            
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)
            
    return googleapiclient.discovery.build("youtube", "v3", credentials=creds)

def upload_video(youtube, video_path):
    print("Uploading final music video to YouTube...")
    body = {
        'snippet': {
            'title': 'Test Sonauto AI Blue Screen Music Video',
            'description': 'A video with background music generated by Sonauto AI.',
            'tags': ['test', 'blue screen', 'sonauto', 'music'],
            'categoryId': '22'
        },
        'status': {
            'privacyStatus': 'private'
        }
    }
    
    media = MediaFileUpload(
        video_path,
        chunksize=-1,
        resumable=True,
        mimetype='video/mp4'
    )
    
    request = youtube.videos().insert(
        part='snippet,status',
        body=body,
        media_body=media
    )
    
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"Upload Progress: {int(status.progress() * 100)}%")
            
    print(f"Upload complete! Video ID: {response['id']}")
    return response['id']

if __name__ == '__main__':
    load_env()
    
    audio_file = 'sonauto_music.mp3'
    temp_video_file = 'temp_blue_video.mp4'
    final_video_file = 'final_music_video.mp4'
    
    try:
        # 1. Generate music using Sonauto AI
        generate_sonauto_music(audio_file)
        
        # 2. Get audio clip duration to generate matching video length
        temp_audio = AudioFileClip(audio_file)
        audio_duration = temp_audio.duration
        temp_audio.close()
        print(f"Downloaded audio duration: {audio_duration} seconds")
        
        # 3. Generate matching length blue screen video
        generate_blue_video(temp_video_file, duration=audio_duration)
        
        # 4. Merge video and audio
        merge_audio_video(temp_video_file, audio_file, final_video_file)
        
        # 5. Authenticate YouTube
        youtube = get_authenticated_service()
        
        # 6. Upload final video
        video_id = upload_video(youtube, final_video_file)
        print(f"Video uploaded successfully. Watch URL: https://www.youtube.com/watch?v={video_id}")
    except Exception as e:
        print(f"An error occurred: {e}")
