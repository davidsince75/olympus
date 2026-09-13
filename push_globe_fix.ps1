# push_globe_fix.ps1 — commit the 13 Sep globe-surface fix and push it.
#
# Run: right-click -> Run with PowerShell
#  or: powershell -ExecutionPolicy Bypass -File .\push_globe_fix.ps1
#
# Non-destructive: it deletes only stale git lock files, never force-pushes,
# and stops with an explanation rather than guessing.

$ErrorActionPreference = 'Stop'
Set-Location -Path $PSScriptRoot

function Step($m) { Write-Host "`n== $m" -ForegroundColor Cyan }
function Note($m) { Write-Host "   $m" -ForegroundColor DarkGray }
function Fail($m) { Write-Host "`n!! $m" -ForegroundColor Yellow; exit 1 }

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Fail "git is not on PATH. Install Git for Windows, then run this again."
}
if (-not (Test-Path .git)) {
    Fail "No .git here. Expected to run from the Olympus repo root ($PSScriptRoot)."
}

Step "Clearing stale lock files"
foreach ($lock in '.git\HEAD.lock', '.git\index.lock', '.git\objects\maintenance.lock') {
    if (Test-Path $lock) { Remove-Item $lock -Force; Note "removed $lock" }
}
Note "done"

Step "Staging the globe-surface fix"
$paths = @(
    'src/deck.html',
    'dist/deck.html',
    'build/patch_globe_surface.py',
    'build/patch_deck_imagery.py',
    'ingest/fetch_global.py',
    'scripts/probe_layers.cjs',
    'data/imagery/relief_G.jpg',
    'data/imagery/today_G.jpg',
    'data/imagery/manifest_global.json'
)
foreach ($p in $paths) {
    if (-not (Test-Path $p)) { Fail "missing: $p — nothing was staged." }
}
git add -- $paths
git status --short -- $paths

Step "Committing"
git diff --cached --quiet -- $paths
if ($LASTEXITCODE -eq 0) {
    Note "nothing staged - already committed, moving on"
} else {
    git commit `
        -m "Globe draws its own surface: imagery, aurora, drift and SAR footprints" `
        -m "drawGlobe had no equivalent of drawDeckBase and never called drawDeckLive, so five controls that stayed on screen in GLOBE did nothing when pressed: Relief, Today, the auroral oval, the ice-drift field with its x1/x5/x15 bar, and the SAR footprints. The globe cannot use either baked polar square - they stop at r = rmax, latitude 33 N and 26 S, which on a sphere is a bare band across the tropics - so it gets its own global plate carree sheet per layer, from the same GIBS layer, resampled per screen cell: coarse while the camera moves, fine once it stops, both keyed on the camera the ice shell's lookup table was built for so the two can never be registered to different views." `
        -m "Also fixed: the station network answered to the Deep-limbs switch, because drawSitesGlobe owned both; the imagery date readout and the GIBS feed row read L.day, which is not a field a layer has (it is time), so Today always reported itself as a static composite with no date; preloadImagery's onload called a function named paint that does not exist; and drawSchematicLayers held a SAR block switched on st.lay.sar, unreachable since the real footprints landed as sar1." `
        -m "Verified with scripts/probe_layers.cjs, which toggles every layer in every view mode and diffs the canvas against a noise floor. Dragging the globe costs 4.3 ms against a 2.7 ms baseline; dist/deck.html is 12.56 MB, under the 16 MB ceiling." `
        -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>" `
        -m "Claude-Session: https://claude.ai/code/session_01DpLqji2bEzYUHC6dbkCEfF"
    if ($LASTEXITCODE -ne 0) { Fail "git commit failed - see the message above." }
}

Step "Pushing"
$branch = (git rev-parse --abbrev-ref HEAD).Trim()
Note "on '$branch'"
Note "if a browser or credential window opens, sign in there - I never see it"
git push origin $branch
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Push refused. If the remote has commits yours does not descend from:" -ForegroundColor Yellow
    Write-Host "    git pull --rebase origin $branch" -ForegroundColor White
    Write-Host "    git push origin $branch" -ForegroundColor White
    Write-Host "Do not force-push." -ForegroundColor Yellow
    exit 1
}

Step "Done"
Write-Host "   https://github.com/davidsince75/olympus" -ForegroundColor Green
Read-Host "Press Enter to close"
