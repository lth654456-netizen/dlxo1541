"""
P-Reinforce Engine — Git Sync
변경사항을 GitHub에 자동으로 커밋하고 푸시합니다.
"""
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent


def run_git(args: list[str], cwd: Path = REPO_ROOT) -> tuple[int, str, str]:
    """git 명령어를 실행하고 (returncode, stdout, stderr) 반환합니다."""
    result = subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def ensure_git_config() -> None:
    """git 사용자 정보가 없으면 기본값으로 설정합니다."""
    code, name, _ = run_git(["config", "user.name"])
    if code != 0 or not name:
        run_git(["config", "user.name", "P-Reinforce Agent"])
        run_git(["config", "user.email", "p-reinforce@wiki.local"])


def stage_all() -> bool:
    """모든 변경사항을 스테이징합니다."""
    code, out, err = run_git(["add", "."])
    if code != 0:
        print(f"❌ git add 실패: {err}")
        return False
    print("✅ git add . 완료")
    return True


def commit(action_summary: str) -> tuple[bool, str]:
    """변경사항을 커밋하고 커밋 해시를 반환합니다."""
    ensure_git_config()
    
    message = f"[P-Reinforce] {action_summary}"
    code, out, err = run_git(["commit", "-m", message])
    
    if code != 0:
        if "nothing to commit" in (out + err):
            print("ℹ️  커밋할 변경사항 없음")
            return True, "no-changes"
        print(f"❌ git commit 실패: {err}")
        return False, ""
    
    # 커밋 해시 추출
    hash_code, commit_hash, _ = run_git(["rev-parse", "--short", "HEAD"])
    commit_hash = commit_hash if hash_code == 0 else "unknown"
    
    print(f"✅ 커밋 완료: {commit_hash} — {message}")
    return True, commit_hash


def push(branch: str = "main") -> bool:
    """원격 저장소로 푸시합니다."""
    code, out, err = run_git(["push", "origin", branch])
    if code != 0:
        # 업스트림 없을 때 자동 설정
        if "no upstream" in err or "has no upstream" in err:
            code, out, err = run_git(["push", "--set-upstream", "origin", branch])
    
    if code != 0:
        print(f"❌ git push 실패: {err}")
        print("💡 팁: GitHub 인증이 필요할 수 있습니다. Personal Access Token을 확인하세요.")
        return False
    
    print(f"✅ GitHub 푸시 완료 → origin/{branch}")
    return True


def sync(action_summary: str, branch: str = "master") -> tuple[bool, str]:
    """add → commit → push를 한번에 실행합니다."""
    print(f"\n🔄 GitHub 동기화 시작: {action_summary}")
    print("-" * 50)
    
    if not stage_all():
        return False, ""
    
    success, commit_hash = commit(action_summary)
    if not success:
        return False, ""
    
    if commit_hash == "no-changes":
        return True, "no-changes"
    
    push_success = push(branch)
    return push_success, commit_hash


def get_status() -> str:
    """현재 git 상태를 반환합니다."""
    _, out, _ = run_git(["status", "--short"])
    return out if out else "clean"


def get_log(n: int = 5) -> str:
    """최근 커밋 로그를 반환합니다."""
    _, out, _ = run_git(["log", f"-{n}", "--oneline", "--decorate"])
    return out


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "수동 동기화"
    ok, hash_ = sync(action)
    sys.exit(0 if ok else 1)
