"""
gen_token.py — YouTube readonly 스코프 토큰 발급 전용 스크립트
터미널에서 직접 실행하세요.
"""
import os, pickle
import google_auth_oauthlib.flow

SCOPES = ["https://www.googleapis.com/auth/youtube.readonly"]
CLIENT_SECRETS_PATH = "client_secrets.json"
TOKEN_PATH = "token.pickle"

print("🔑 YouTube readonly 토큰 발급 시작...")
flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
    CLIENT_SECRETS_PATH, SCOPES
)
# port=0 → 임의 포트 사용 (redirect_uris 제한 우회)
creds = flow.run_local_server(port=0)

with open(TOKEN_PATH, "wb") as f:
    pickle.dump(creds, f)

print(f"✅ 토큰 저장 완료: {TOKEN_PATH}")
print(f"   스코프: {creds.scopes}")
