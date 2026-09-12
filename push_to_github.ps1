# push_to_github.ps1 — commit the 12 Sep build and push it to a remote.
#
# Run: right-click -> Run with PowerShell
#  or: powershell -ExecutionPolicy Bypass -File .\push_to_github.ps1
#
# Nothing here is destructive: it deletes only stale git lock files, never
# force-pushes, and stops with an explanation rather than guessing if the
# remote already has history.

$ErrorActionPreference = 'Stop'
Set-Location -Path $PSScriptRoot

$Remote = 'https://github.com/davidsince75/olympus.git'

function Step($msg) { Write-Host "`n== $msg" -ForegroundColor Cyan }
function Note($msg) { Write-Host "   $msg" -ForegroundColor DarkGray }
function Fail($msg) { Write-Host "`n!! $msg" -ForegroundColor Yellow; exit 1 }

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Fail "git is not on PATH. Install Git for Windows, then run this again."
}
if (-not (Test-Path .git)) {
    Fail "No .git here. Expected to run from the Olympus repo root ($PSScriptRoot)."
}

Step "Clearing stale lock files from the previous session"
foreach ($lock in '.git\HEAD.lock', '.git\index.lock', '.git\objects\maintenance.lock') {
    if (Test-Path $lock) { Remove-Item $lock -Force; Note "removed $lock" }
}
Note "done"

Step "Staging the build"
git add ingest scripts build data/asi dist/ice_surface.html
git status --short

Step "Committing"
git diff --cached --quiet
if ($LASTEXITCODE -eq 0) {
    Note "nothing staged - already committed, moving on"
} else {
    git commit `
        -m "Shared ellipsoidal polar stereographic; ASI AMSR2 6.25 km ingest and surface" `
        -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>" `
        -m "Claude-Session: https://claude.ai/code/session_01E6uxEC648fwdawCsEsMoPN"
    if ($LASTEXITCODE -ne 0) { Fail "git commit failed - see the message above." }
}

Step "Wiring the remote"
$existing = (git remote get-url origin 2>$null)
if ($LASTEXITCODE -ne 0 -or -not $existing) {
    git remote add origin $Remote
    Note "origin -> $Remote"
} elseif ($existing.Trim() -ne $Remote) {
    Note "origin is already $existing"
    Note "leaving it alone. Change it by hand if that is wrong:"
    Note "  git remote set-url origin $Remote"
} else {
    Note "origin already set"
}

Step "Naming the branch"
$branch = (git rev-parse --abbrev-ref HEAD).Trim()
Note "currently on '$branch'"
if ($branch -eq 'master') {
    git branch -M main
    $branch = 'main'
    Note "renamed to 'main' to match GitHub's default"
}

Step "Pushing"
Note "if a browser or credential window opens, sign in there - I never see it"
git push -u origin $branch
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Push refused. The usual cause is that the repo on GitHub was created" -ForegroundColor Yellow
    Write-Host "with a README, so it has a commit yours does not descend from. Fix:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "    git pull origin $branch --allow-unrelated-histories" -ForegroundColor White
    Write-Host "    git push -u origin $branch" -ForegroundColor White
    Write-Host ""
    Write-Host "Do not force-push - that would discard whatever is already there." -ForegroundColor Yellow
    exit 1
}

Step "Done"
Write-Host "   https://github.com/davidsince75/olympus" -ForegroundColor Green
Write-Host "   The register is no longer one deleted folder from a fourth recovery." -ForegroundColor Green
Write-Host ""
Read-Host "Press Enter to close"
