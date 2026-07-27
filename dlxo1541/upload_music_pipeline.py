import os
import time
import subprocess
import pickle
import cv2
import requests
import numpy as np
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
from google.auth.transport.requests import Request
from googleapiclient.http import MediaFileUpload
from playwright.sync_api import sync_playwright

try:
    from moviepy import VideoFileClip, AudioFileClip
except ImportError:
    from moviepy.editor import VideoFileClip, AudioFileClip

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

def copy_edge_profile():
    print("Ensuring Microsoft Edge profile is closed and cloning it...")
    # Kill Edge to release locks
    os.system("taskkill /f /im msedge.exe >nul 2>&1")
    time.sleep(2)
    
    user_profile = os.environ["USERPROFILE"]
    src_dir = os.path.join(user_profile, "AppData", "Local", "Microsoft", "Edge", "User Data", "Default")
    dst_dir = r"C:\Users\a0103\EdgeDebug\Default"
    
    os.makedirs(dst_dir, exist_ok=True)
    
    local_state_src = os.path.join(user_profile, "AppData", "Local", "Microsoft", "Edge", "User Data", "Local State")
    local_state_dst = r"C:\Users\a0103\EdgeDebug\Local State"
    if os.path.exists(local_state_src):
        shutil_copy(local_state_src, local_state_dst)
        
    cookies_src = os.path.join(src_dir, "Network", "Cookies")
    cookies_dst = os.path.join(dst_dir, "Network", "Cookies")
    os.makedirs(os.path.dirname(cookies_dst), exist_ok=True)
    if os.path.exists(cookies_src):
        shutil_copy(cookies_src, cookies_dst)
        
    # Copy Local Storage folder
    ls_src = os.path.join(src_dir, "Local Storage")
    ls_dst = os.path.join(dst_dir, "Local Storage")
    if os.path.exists(ls_src):
        subprocess.run(f'robocopy "{ls_src}" "{ls_dst}" /E /R:0 /W:0 >nul 2>&1', shell=True)
        
    print("Edge profile cloned successfully.")

def shutil_copy(src, dst):
    try:
        import shutil
        shutil.copyfile(src, dst)
    except Exception as e:
        print(f"Warning: Failed to copy {src}: {e}")

def generate_suno_music_headless(output_path, prompt="A bright, upbeat electronic pop background track"):
    copy_edge_profile()
    
    song_urls = []
    
    def handle_response(response):
        # Scan all JSON responses from studio-api domains recursively
        if "studio-api" in response.url:
            try:
                content_type = response.headers.get("content-type", "")
                if "json" in content_type:
                    data = response.json()
                    
                    def find_songs(obj):
                        songs_found = []
                        if isinstance(obj, list):
                            for item in obj:
                                songs_found.extend(find_songs(item))
                        elif isinstance(obj, dict):
                            if "play_url" in obj or "audio_url" in obj:
                                songs_found.append(obj)
                            else:
                                for val in obj.values():
                                    songs_found.extend(find_songs(val))
                        return songs_found
                        
                    found = find_songs(data)
                    for song in found:
                        audio_url = song.get("play_url") or song.get("audio_url")
                        status = song.get("status")
                        song_id = song.get("id")
                        if audio_url and song_id:
                            existing = next((s for s in song_urls if s["id"] == song_id), None)
                            if existing:
                                existing["status"] = status
                                existing["url"] = audio_url
                            else:
                                song_urls.append({
                                    "id": song_id,
                                    "url": audio_url,
                                    "status": status,
                                    "title": song.get("title", "Untitled")
                                })
                                print(f"[Suno API] Intercepted song: '{song.get('title')}' status={status}")
            except Exception:
                pass

    edge_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    edge_debug_dir = r"C:\Users\a0103\EdgeDebug"
    
    print("Launching headless Microsoft Edge via Playwright...")
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=edge_debug_dir,
            executable_path=edge_path,
            headless=True,
            args=["--no-sandbox", "--disable-gpu"]
        )
        
        page = context.new_page()
        page.on("response", handle_response)
        
        print("Navigating to Suno Create page...")
        page.goto("https://suno.com/create")
        
        # Verify prompt textarea is visible (means user is logged in)
        textarea = page.locator("textarea").first
        try:
            textarea.wait_for(state="visible", timeout=20000)
        except Exception:
            context.close()
            raise Exception("Failed to confirm active session: Prompt input is not visible. Please log in to suno.com in Microsoft Edge first.")
            
        print("Suno session validated. Entering prompt...")
        textarea.fill(prompt)
        
        # Click Create
        create_btn = page.locator("button:has-text('Create')").first
        create_btn.click()
        print("Song generation triggered successfully!")
        
        # Wait 5 seconds, then navigate to Library to force feed loading
        time.sleep(5)
        print("Navigating to Library page to capture feed...")
        page.goto("https://suno.com/library")
        
        # Wait for status to complete
        print("Waiting for generation task to complete (usually 1-2 minutes)...")
        completed_song = None
        start_time = time.time()
        last_reload = time.time()
        while time.time() - start_time < 200:
            for song in song_urls:
                if song["status"] == "complete":
                    completed_song = song
                    break
            if completed_song:
                break
            
            # Periodically reload library to refresh the feed if status completes
            if time.time() - last_reload > 15:
                print("Refreshing Library page to update status...")
                try:
                    page.reload()
                except Exception:
                    pass
                last_reload = time.time()
                
            time.sleep(3)
            
        if not completed_song:
            if song_urls:
                completed_song = song_urls[0]
                print("Warning: Completed status not caught. Using newest song in feed.")
            else:
                context.close()
                raise Exception("Music generation timed out or failed to parse feed.")
                
        print(f"Downloading track from: {completed_song['url']}")
        r = requests.get(completed_song['url'])
        if r.status_code != 200:
            context.close()
            raise Exception(f"Download failed with status: {r.status_code}")
            
        with open(output_path, 'wb') as f:
            f.write(r.content)
            
        print(f"Music successfully downloaded and saved to {output_path}")
        context.close()

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
    
    if hasattr(video_clip, "with_audio"):
        video_clip = video_clip.with_audio(audio_clip)
    else:
        video_clip = video_clip.set_audio(audio_clip)
        
    video_clip.write_videofile(output_path, codec="libx264", audio_codec="aac")
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
            'title': 'Test Suno AI Blue Screen Music Video',
            'description': 'A video with background music generated by Suno AI using Playwright cookie injection.',
            'tags': ['test', 'blue screen', 'suno', 'music', 'playwright'],
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
    audio_file = 'suno_music.mp3'
    temp_video_file = 'temp_blue_video.mp4'
    final_video_file = 'final_music_video.mp4'
    
    try:
        # 1. Generate and download music using Playwright Session Injection
        generate_suno_music_headless(audio_file)
        
        # 2. Get audio clip duration to generate matching video length
        temp_audio = AudioFileClip(audio_file)
        audio_duration = temp_audio.duration
        temp_audio.close()
        print(f"Suno audio duration: {audio_duration} seconds")
        
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
