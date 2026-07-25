"""
P-Reinforce Engine ??Git Sync
ë³€ê²½ì‚¬??„ GitHub???ë™?¼ë¡œ ì»¤ë°‹?˜ê³  ?¸ì‹œ?©ë‹ˆ??
"""
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent


def run_git(args: list[str], cwd: Path = REPO_ROOT) -> tuple[int, str, str]:
    """git ëª…ë ¹?´ë? ?¤í–‰?˜ê³  (returncode, stdout, stderr) ë°˜í™˜?©ë‹ˆ??"""
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
    """git ?¬ìš©???•ë³´ê°€ ?†ìœ¼ë©?ê¸°ë³¸ê°’ìœ¼ë¡??¤ì •?©ë‹ˆ??"""
    code, name, _ = run_git(["config", "user.name"])
    if code != 0 or not name:
        run_git(["config", "user.name", "P-Reinforce Agent"])
        run_git(["config", "user.email", "p-reinforce@wiki.local"])


def stage_all() -> bool:
    """ëª¨ë“  ë³€ê²½ì‚¬??„ ?¤í…Œ?´ì§•?©ë‹ˆ??"""
    code, out, err = run_git(["add", "."])
    if code != 0:
        print(f"??git add ?¤íŒ¨: {err}")
        return False
    print("??git add . ?„ë£Œ")
    return True


def commit(action_summary: str) -> tuple[bool, str]:
    """ë³€ê²½ì‚¬??„ ì»¤ë°‹?˜ê³  ì»¤ë°‹ ?´ì‹œë¥?ë°˜í™˜?©ë‹ˆ??"""
    ensure_git_config()
    
    message = f"[P-Reinforce] {action_summary}"
    code, out, err = run_git(["commit", "-m", message])
    
    if code != 0:
        if "nothing to commit" in (out + err):
            print("?¹ï¸  ì»¤ë°‹??ë³€ê²½ì‚¬???†ìŒ")
            return True, "no-changes"
        print(f"??git commit ?¤íŒ¨: {err}")
        return False, ""
    
    # ì»¤ë°‹ ?´ì‹œ ì¶”ì¶œ
    hash_code, commit_hash, _ = run_git(["rev-parse", "--short", "HEAD"])
    commit_hash = commit_hash if hash_code == 0 else "unknown"
    
    print(f"??ì»¤ë°‹ ?„ë£Œ: {commit_hash} ??{message}")
    return True, commit_hash


def push(branch: str = "main") -> bool:
    """?ê²© ?€?¥ì†Œë¡??¸ì‹œ?©ë‹ˆ??"""
    code, out, err = run_git(["push", "origin", branch])
    if code != 0:
        # ?…ìŠ¤?¸ë¦¼ ?†ì„ ???ë™ ?¤ì •
        if "no upstream" in err or "has no upstream" in err:
            code, out, err = run_git(["push", "--set-upstream", "origin", branch])
    
    if code != 0:
        print(f"??git push ?¤íŒ¨: {err}")
        print("?’¡ ?? GitHub ?¸ì¦???„ìš”?????ˆìŠµ?ˆë‹¤. Personal Access Token???•ì¸?˜ì„¸??")
        return False
    
    print(f"??GitHub ?¸ì‹œ ?„ë£Œ ??origin/{branch}")
    return True


def sync(action_summary: str, branch: str = "main") -> tuple[bool, str]:
    """add ??commit ??pushë¥??œë²ˆ???¤í–‰?©ë‹ˆ??"""
    print(f"\n?”„ GitHub ?™ê¸°???œì‘: {action_summary}")
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
    """?„ì¬ git ?íƒœë¥?ë°˜í™˜?©ë‹ˆ??"""
    _, out, _ = run_git(["status", "--short"])
    return out if out else "clean"


def get_log(n: int = 5) -> str:
    """ìµœê·¼ ì»¤ë°‹ ë¡œê·¸ë¥?ë°˜í™˜?©ë‹ˆ??"""
    _, out, _ = run_git(["log", f"-{n}", "--oneline", "--decorate"])
    return out


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "?˜ë™ ?™ê¸°??
    ok, hash_ = sync(action)
    sys.exit(0 if ok else 1)
