#!/usr/bin/env pwsh
# P-Reinforce 편의 실행 스크립트
# 사용법: .\reinforce.ps1 [명령어] [인자...]

param(
    [Parameter(Position=0)]
    [string]$Command = "help",
    
    [Parameter(Position=1)]
    [string]$Arg1 = "",
    
    [Parameter(Position=2)]
    [string]$Arg2 = ""
)

$ROOT = $PSScriptRoot
$ENGINE = Join-Path $ROOT "engine\p_reinforce.py"

function Show-Help {
    Write-Host ""
    Write-Host "🧠 P-Reinforce — 자율 지식 정원사" -ForegroundColor Cyan
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "사용법:" -ForegroundColor Yellow
    Write-Host "  .\reinforce.ps1 add <파일경로>      # Raw 파일 처리 & 위키 변환"
    Write-Host "  .\reinforce.ps1 scan                 # 00_Raw/ 폴더 전체 스캔"
    Write-Host "  .\reinforce.ps1 status               # 현재 위키 현황 출력"
    Write-Host "  .\reinforce.ps1 new <날짜> <내용>    # 새 Raw 노트 빠르게 생성"
    Write-Host "  .\reinforce.ps1 praise <문서명>      # 분류 칭찬 피드백"
    Write-Host "  .\reinforce.ps1 move <문서명> <카테고리>  # 이동 피드백"
    Write-Host "  .\reinforce.ps1 sync                 # GitHub 수동 동기화"
    Write-Host "  .\reinforce.ps1 log                  # 최근 Git 커밋 로그"
    Write-Host ""
}

function Ensure-RawDate {
    param([string]$Date)
    $rawPath = Join-Path $ROOT "00_Raw\$Date"
    if (-not (Test-Path $rawPath)) {
        New-Item -ItemType Directory -Path $rawPath -Force | Out-Null
    }
    return $rawPath
}

switch ($Command.ToLower()) {
    "add" {
        if (-not $Arg1) { Write-Host "❌ 파일 경로를 지정하세요." -ForegroundColor Red; exit 1 }
        python $ENGINE $Arg1
    }
    
    "scan" {
        python $ENGINE --scan
    }
    
    "status" {
        python $ENGINE --status
    }
    
    "new" {
        # .\reinforce.ps1 new "제목" "내용..."
        $date = (Get-Date -Format "yyyy-MM-dd")
        $rawDir = Ensure-RawDate $date
        
        $title = if ($Arg1) { $Arg1 } else { "note_$(Get-Date -Format 'HHmmss')" }
        $content = if ($Arg2) { $Arg2 } else { "" }
        
        $filename = "$title.md"
        $filepath = Join-Path $rawDir $filename
        
        $noteContent = @"
# $title

$content

---
*생성: $(Get-Date -Format 'yyyy-MM-dd HH:mm')*
"@
        $noteContent | Out-File -FilePath $filepath -Encoding utf8
        Write-Host "✅ Raw 노트 생성: $filepath" -ForegroundColor Green
        Write-Host ""
        Write-Host "위키로 변환하려면:" -ForegroundColor Yellow
        Write-Host "  .\reinforce.ps1 add `"$filepath`""
    }
    
    "praise" {
        if (-not $Arg1) { Write-Host "❌ 문서명을 지정하세요." -ForegroundColor Red; exit 1 }
        python $ENGINE --feedback $Arg1 "칭찬"
    }
    
    "move" {
        if (-not $Arg1 -or -not $Arg2) { 
            Write-Host "❌ 문서명과 카테고리를 지정하세요." -ForegroundColor Red
            exit 1 
        }
        python $ENGINE --feedback $Arg1 "이동:$Arg2"
    }
    
    "sync" {
        python -c "
import sys; sys.path.insert(0, 'engine')
from git_sync import sync
ok, h = sync('수동 동기화')
print('✅ 완료' if ok else '❌ 실패')
"
    }
    
    "log" {
        python -c "
import sys; sys.path.insert(0, 'engine')
from git_sync import get_log
print(get_log(10))
"
    }
    
    default {
        Show-Help
    }
}
