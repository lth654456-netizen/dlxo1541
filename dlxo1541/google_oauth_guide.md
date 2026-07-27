# Google OAuth 2.0 및 YouTube API 연동 가이드

이 문서는 YouTube API를 사용한 자동 동영상 업로드 설정 과정에서 겪은 문제들과 해결 방법을 정리한 지식 문서입니다.

---

## 1. Google Cloud Console 클라이언트 설정

### 1.1 클라이언트 유형 (Client Type)
- **권장 유형**: `데스크톱 애플리케이션 (Desktop Application)`
- **특징**: 웹 애플리케이션과 달리 리디렉션 URI 포트 제한이 없으며, 로컬 루프백 주소(`http://localhost:<port>/`)를 통해 간편하게 인증받을 수 있습니다.

### 1.2 승인된 리디렉션 URI (Authorized Redirect URIs)
- 데스크톱 유형의 경우, Google Cloud Console에서 직접 리디렉션 URI를 수동 등록할 필요 없이 `http://localhost:<포트>/` 주소가 자동으로 허용됩니다.
- 단, 개발 코드에서 포트 번호를 고정하는 것이 예측 가능한 인증 환경을 구성하는 데 유리합니다.
  - 예: `flow.run_local_server(host='localhost', port=8080)` 사용 시 브라우저는 `http://localhost:8080/`로 리디렉션됩니다.

---

## 2. 주요 오류 해결법 (Troubleshooting)

### 2.1 오류 403: org_internal
- **증상**: 구글 로그인 후 **"액세스 차단됨: [앱이름]은(는) 조직 내에서만 사용할 수 있습니다"** 경고창이 나타남.
- **원인**: Google Cloud 프로젝트의 OAuth 동의 화면 사용자 유형이 `내부 (Internal)`로 설정되어 있어, 외부 일반 개인 Gmail 계정(`@gmail.com`)의 접근을 차단하기 때문입니다.
- **해결 방법**:
  1. [Google Cloud Console](https://console.cloud.google.com/)의 **Google 인증 플랫폼 > 대상(Audience)** 메뉴로 이동합니다.
  2. **사용자 유형 (User Type)**을 `외부 (External)`로 변경합니다.
  3. 필요시 단계를 `프로덕션 (Production)`으로 전환하거나, 테스트 상태를 유지할 경우 **테스트 사용자 (Test Users)** 목록에 로그인할 이메일 주소를 명시적으로 등록해야 합니다.

### 2.2 Google에서 확인하지 않은 앱 (Unverified App Warning)
- **증상**: 로그인 도중 빨간색 경고 삼각형과 함께 **"Google에서 확인하지 않은 앱"**이라는 화면이 노출됨.
- **원인**: 개인 개발용 또는 테스트용 앱으로서 구글의 공식 검증 심사(Verification)를 거치지 않았기 때문에 발생하는 표준 경고입니다.
- **해결 방법**:
  1. 화면 왼쪽 아래의 작게 적힌 **`고급 (Advanced)`** 텍스트를 클릭합니다.
  2. 펼쳐진 상세 내용 하단의 **`[앱이름](으)로 이동(안전하지 않음)`** 링크를 클릭하여 승인 화면으로 진행합니다.

---

## 3. 구현 파이프라인 개요

[upload_pipeline.py](file:///c:/Users/a0103/OneDrive/Desktop/안티그레비티/dlxo1541/upload_pipeline.py)에 구현된 파이프라인의 구조는 다음과 같습니다:

1. **비디오 생성 (OpenCV)**:
   ```python
   # NumPy와 OpenCV를 활용해 5초 동안 30fps(총 150프레임)의 파란색(BGR: 255, 0, 0) 동영상 생성
   blue_frame = np.zeros((720, 1280, 3), dtype=np.uint8)
   blue_frame[:] = [255, 0, 0]
   out = cv2.VideoWriter('blue_video.mp4', cv2.VideoWriter_fourcc(*'mp4v'), 30, (1280, 720))
   ```
2. **로컬 서버 기반 인증 (google-auth-oauthlib)**:
   - 포트를 `8080`으로 고정하여 일관성 있는 리디렉션을 수신합니다.
   - 획득한 크리덴셜(Credentials)은 `token.pickle` 파일로 로컬에 캐싱하여 다음 실행부터 재로그인 없이 토큰을 자동 갱신(Refresh)합니다.
3. **유튜브 API 업로드**:
   - `google-api-python-client`를 활용하여 동영상 제목, 설명, 카테고리(`22`: 인물/블로그), 공개 상태(`private`) 정보를 메타데이터로 지정해 동영상을 백그라운드 업로드합니다.
