#!/bin/bash
# ============================================================
# Executive Job Search Dashboard — One-Time Setup
# Run this once: bash ~/Desktop/job-tracker/SETUP.sh
# ============================================================

set -e
echo ""
echo "=========================================="
echo "  Job Search Dashboard — Setup"
echo "  GitHub: nanda912"
echo "=========================================="
echo ""

REPO_DIR="$HOME/Desktop/job-tracker"
REPO_NAME="job-tracker"
GITHUB_USER="nanda912"

# --- Step 1: Check prerequisites ---
echo "[1/7] Checking prerequisites..."
if ! command -v git &> /dev/null; then
    echo "ERROR: git is not installed. Install with: xcode-select --install"
    exit 1
fi
echo "  ✓ git found"

# Install gh if needed
if ! command -v gh &> /dev/null; then
    echo "  GitHub CLI (gh) not found. Installing..."
    if command -v brew &> /dev/null; then
        brew install gh
    else
        echo ""
        echo "  Homebrew not found. Installing Homebrew first..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        brew install gh
    fi
fi
echo "  ✓ gh found"

# --- Step 2: Authenticate with GitHub ---
echo ""
echo "[2/7] Checking GitHub authentication..."
if ! gh auth status &> /dev/null 2>&1; then
    echo "  Opening browser to log in to GitHub..."
    gh auth login --web --git-protocol https
fi
echo "  ✓ Authenticated as $(gh api user -q .login)"

# --- Step 3: Configure git ---
echo ""
echo "[3/7] Configuring git..."
cd "$REPO_DIR"

# Set git config for this repo
git config user.name "Nanda Dudala" 2>/dev/null || true
git config user.email "nanda.dudala9@gmail.com" 2>/dev/null || true

if [ ! -d ".git" ]; then
    git init
    git branch -M main
    echo "  ✓ Initialized git repo"
else
    echo "  ✓ Git repo already initialized"
fi

# --- Step 4: Create GitHub repo ---
echo ""
echo "[4/7] Creating GitHub repo..."
if gh repo view "$GITHUB_USER/$REPO_NAME" &> /dev/null 2>&1; then
    echo "  ✓ Repo already exists on GitHub"
    # Make sure remote is set
    git remote set-url origin "https://github.com/$GITHUB_USER/$REPO_NAME.git" 2>/dev/null || \
    git remote add origin "https://github.com/$GITHUB_USER/$REPO_NAME.git" 2>/dev/null || true
else
    gh repo create "$REPO_NAME" \
        --public \
        --description "Executive Job Search Dashboard — Auto-updated daily" \
        --source=. \
        --remote=origin \
        --push
    echo "  ✓ Created github.com/$GITHUB_USER/$REPO_NAME"
fi

# --- Step 5: Initial commit and push ---
echo ""
echo "[5/7] Pushing to GitHub..."
git add -A
git commit -m "Initial setup: Executive Job Search Dashboard

Auto-updating job tracker with 27 executive finance & technology roles.
Deploys to GitHub Pages automatically." 2>/dev/null || echo "  (No new changes to commit)"
git push -u origin main 2>/dev/null || git push --set-upstream origin main
echo "  ✓ Code pushed to GitHub"

# --- Step 6: Enable GitHub Pages ---
echo ""
echo "[6/7] Enabling GitHub Pages..."
# Enable Pages via GitHub Actions workflow
gh api repos/$GITHUB_USER/$REPO_NAME/pages \
    -X POST \
    -f "build_type=workflow" \
    2>/dev/null || echo "  (Pages may already be enabled)"

sleep 2

# Trigger the deploy workflow if it exists
gh workflow run deploy.yml 2>/dev/null || echo "  (Workflow will trigger on next push)"
echo "  ✓ GitHub Pages enabled"

# --- Step 7: Set up daily schedule (macOS launchd) ---
echo ""
echo "[7/7] Setting up daily auto-search..."

PLIST_DIR="$HOME/Library/LaunchAgents"
mkdir -p "$PLIST_DIR"

# Morning search (8 AM)
cat > "$PLIST_DIR/com.nanda.jobsearch.morning.plist" << PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.nanda.jobsearch.morning</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>$REPO_DIR/update_and_publish.py</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>8</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>$HOME/Desktop/job_search_log.txt</string>
    <key>StandardErrorPath</key>
    <string>$HOME/Desktop/job_search_log.txt</string>
    <key>WorkingDirectory</key>
    <string>$REPO_DIR</string>
</dict>
</plist>
PLIST

# Evening search (6 PM)
cat > "$PLIST_DIR/com.nanda.jobsearch.evening.plist" << PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.nanda.jobsearch.evening</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>$REPO_DIR/update_and_publish.py</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>18</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>$HOME/Desktop/job_search_log.txt</string>
    <key>StandardErrorPath</key>
    <string>$HOME/Desktop/job_search_log.txt</string>
    <key>WorkingDirectory</key>
    <string>$REPO_DIR</string>
</dict>
</plist>
PLIST

launchctl unload "$PLIST_DIR/com.nanda.jobsearch.morning.plist" 2>/dev/null || true
launchctl unload "$PLIST_DIR/com.nanda.jobsearch.evening.plist" 2>/dev/null || true
launchctl load "$PLIST_DIR/com.nanda.jobsearch.morning.plist"
launchctl load "$PLIST_DIR/com.nanda.jobsearch.evening.plist"
echo "  ✓ Daily schedule active (8 AM + 6 PM)"

# --- Done! ---
DASHBOARD_URL="https://nanda912.github.io/job-tracker/"

echo ""
echo "=========================================="
echo "  ✅ SETUP COMPLETE!"
echo "=========================================="
echo ""
echo "  🌐 Your LIVE dashboard:"
echo "  $DASHBOARD_URL"
echo ""
echo "  (Give it 1-2 min for first deploy)"
echo ""
echo "  📅 Auto-search: 8 AM + 6 PM daily"
echo "  📊 27 jobs tracked across 20+ companies"
echo ""
echo "  Manual run:  python3 ~/Desktop/job-tracker/update_and_publish.py"
echo "  View logs:   cat ~/Desktop/job_search_log.txt"
echo ""
echo "=========================================="
echo ""
echo "  Opening your dashboard in 5 seconds..."
sleep 5
open "$DASHBOARD_URL"
