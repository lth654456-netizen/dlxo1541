import os
import pickle
import cv2
import numpy as np
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
from google.auth.transport.requests import Request
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

def generate_blue_video(output_path, duration=5, fps=30, width=1280, height=720):
    print(f"Generating {duration}-second blue video...")
    blue_frame = np.zeros((height, width, 3), dtype=np.uint8)
    blue_frame[:] = [255, 0, 0] # BGR color format: Blue is [255, 0, 0]
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    for _ in range(duration * fps):
        out.write(blue_frame)
        
    out.release()
    print(f"Video saved to {output_path}")

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
            print("A browser window will open. Please authenticate and authorize the application.")
            flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
                client_secrets_path, SCOPES)
            creds = flow.run_local_server(host='localhost', port=8080)
            
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)
            
    return googleapiclient.discovery.build("youtube", "v3", credentials=creds)

def upload_video(youtube, video_path):
    print("Uploading video to YouTube...")
    body = {
        'snippet': {
            'title': 'Test Blue Screen Video',
            'description': 'A 5-second blue screen video uploaded automatically for testing.',
            'tags': ['test', 'blue screen', 'automated'],
            'categoryId': '22' # People & Blogs
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
    video_filename = 'blue_video.mp4'
    
    # 1. Generate video
    generate_blue_video(video_filename)
    
    # 2. Authenticate
    youtube = get_authenticated_service()
    
    # 3. Upload
    video_id = upload_video(youtube, video_filename)
    print(f"Video uploaded successfully. Watch URL: https://www.youtube.com/watch?v={video_id}")
