# ANN Feed — Complete Setup & Deployment Guide
> For a total beginner. Follow every step in order.

---

## PART 1 — Clean Up Your Repo (Fix the Mess)

### Step 1.1 — Delete all junk files from your LOCAL folder

Open your project folder (e.g. `Desktop/ANN-Global`).
**Delete everything EXCEPT:**
- `index.html` ← replace with the new one from this build
- `agent.py`   ← replace with the new one from this build
- `news.json`  ← keep (or it will be regenerated)
- `README.md`  ← keep or replace
- The hidden `.git` folder ← **DO NOT DELETE THIS**

Files to delete if they exist:
```
index.md          ← DELETE
indexV1.html      ← DELETE
indexV2.html      ← DELETE
index copy.html   ← DELETE
start_news.py     ← DELETE (replaced by agent.py)
_config.yml       ← DELETE (causes conflicts with GitHub Pages)
desktop.ini       ← DELETE (Windows junk)
*.lnk files       ← DELETE (Windows shortcuts)
```

---

### Step 1.2 — Force-sync your local repo with GitHub (terminal commands)

Open a terminal in VS Code (`Terminal → New Terminal`) and paste these commands **one by one**:

```bash
# Navigate to your project folder — change this path to yours
cd ~/Desktop/ANN-Global

# See what Git thinks is going on
git status

# Remove any cached junk files Git is tracking
git rm --cached index.md 2>/dev/null || true
git rm --cached indexV1.html 2>/dev/null || true
git rm --cached _config.yml 2>/dev/null || true
git rm --cached "desktop.ini" 2>/dev/null || true

# Stage ONLY the files you want
git add index.html agent.py news.json README.md

# Commit
git commit -m "Clean rebuild — remove hardcoded content"

# Push to GitHub
git push origin main
```

> ⚠ If you get "error: rejected — non-fast-forward", it means GitHub has commits
> your local copy doesn't have. Fix it with:
> ```bash
> git pull origin main --rebase
> git push origin main
> ```

---

## PART 2 — Fix the GitHub Pages Branch Issue

### The "None/Main" problem explained
GitHub Pages needs to know which branch to serve from.
If it says "None" it means it has never been configured.
If it says "Main" but shows 404, the files might not be in the repo root.

### Step 2.1 — Make sure your branch is called "main"

In your terminal:
```bash
# Check what your branch is called
git branch

# If it says "master" instead of "main", rename it:
git branch -m master main
git push -u origin main
```

### Step 2.2 — Configure GitHub Pages in the web interface

1. Go to `https://github.com/YOUR_USERNAME/YOUR_REPO`
2. Click **Settings** (top menu)
3. Click **Pages** (left sidebar)
4. Under **Source**, select:
   - **Deploy from a branch**
   - Branch: **main**
   - Folder: **/ (root)**
5. Click **Save**
6. Wait 2 minutes, then visit `https://YOUR_USERNAME.github.io/YOUR_REPO`

> ✅ You should see the ANN Feed site. If you see a 404, make sure `index.html`
> is in the ROOT of the repo (not inside a subfolder).

---

## PART 3 — Fix Your OVH Domain (annfeed.com → GitHub Pages)

### The core problem: Two hosts fighting each other
You have OVH Web Hosting AND GitHub Pages both trying to serve annfeed.com.
**Solution: Use GitHub Pages for hosting. Point DNS from OVH to GitHub.**
You do NOT need OVH web hosting for this — only the DNS management.

### Step 3.1 — Create a CNAME file in your repo

Create a file called exactly `CNAME` (no extension) in your repo root.
Put ONE line in it:
```
annfeed.com
```

Add and push it:
```bash
echo "annfeed.com" > CNAME
git add CNAME
git commit -m "Add CNAME for custom domain"
git push origin main
```

### Step 3.2 — Configure GitHub Pages custom domain

1. Go to your repo → **Settings → Pages**
2. Under **Custom domain**, type: `annfeed.com`
3. Click **Save**
4. Enable **Enforce HTTPS** (wait a few minutes for the checkbox to become active)

### Step 3.3 — Configure your OVH DNS

1. Log in to your OVH account at `https://www.ovhcloud.com`
2. Go to **Web Cloud → Domains → annfeed.com → DNS Zone**
3. **Delete any existing A records** pointing to OVH servers
4. **Add these 4 A records** (GitHub Pages IPs):

| Type | Name       | Value           | TTL  |
|------|------------|-----------------|------|
| A    | @          | 185.199.108.153 | 3600 |
| A    | @          | 185.199.109.153 | 3600 |
| A    | @          | 185.199.110.153 | 3600 |
| A    | @          | 185.199.111.153 | 3600 |

5. **Add a CNAME record** for www:

| Type  | Name | Value                          | TTL  |
|-------|------|--------------------------------|------|
| CNAME | www  | YOUR_USERNAME.github.io        | 3600 |

> Replace `YOUR_USERNAME` with your actual GitHub username.

6. **Delete or disable any OVH web hosting** redirect rules that point to their servers.
   - In OVH: **Web Hosting → your hosting plan → Multisite** — remove annfeed.com from there.
   - This is the #1 cause of 404/500 errors: OVH hosting is intercepting your domain.

### Step 3.4 — Wait for DNS propagation

DNS changes take **10 minutes to 24 hours** to fully propagate.
You can check progress at: `https://dnschecker.org/#A/annfeed.com`
Once it shows GitHub's IPs (185.199.x.x), your domain is live.

---

## PART 4 — Run the Agent & Update the Site

### One-time setup
```bash
# Install dependencies
pip install feedparser requests schedule

# Set your Groq API key (free at https://console.groq.com)
# Windows:
setx GROQ_API_KEY "gsk_your_key_here"

# Mac/Linux (add to ~/.zshrc or ~/.bashrc to make permanent):
export GROQ_API_KEY="gsk_your_key_here"
```

Open `agent.py` and set line 32:
```python
REPO_PATH = r"C:\Users\YourName\Desktop\ANN-Global"   # Windows
# or
REPO_PATH = "/home/yourname/projects/ANN-Global"       # Mac/Linux
```

### Daily commands

```bash
# Run once and push to GitHub (most common):
python agent.py --push

# Run every 90 minutes, auto-push (keep terminal open):
python agent.py --schedule --push

# Just run without pushing (test mode):
python agent.py
```

### What happens after you push

1. GitHub receives `news.json`
2. GitHub Pages rebuilds (takes ~60 seconds)
3. Visitor opens annfeed.com — browser fetches `news.json?t=TIMESTAMP`
4. The `?t=TIMESTAMP` cache-buster forces a fresh download every time
5. Site renders the latest articles — no stale content

---

## PART 5 — Troubleshooting

| Problem | Cause | Fix |
|---|---|---|
| Site shows "Could not load news.json" | news.json not pushed, or GitHub Pages still rebuilding | Run `python agent.py --push`, wait 60 s, hard-refresh (Ctrl+Shift+R) |
| Site still shows old content after push | Browser cache | Hard-refresh: **Ctrl+Shift+R** (Win) / **Cmd+Shift+R** (Mac) |
| annfeed.com shows OVH page | OVH hosting still active | Remove annfeed.com from OVH Multisite (Web Hosting section) |
| annfeed.com shows GitHub 404 | CNAME file wrong or Pages not configured | Check CNAME file has exactly `annfeed.com`, check Pages settings |
| Git push rejected | GitHub has newer commits | `git pull origin main --rebase` then push again. Never use `--force` |
| Groq API error 401 | Wrong API key | Check key with: `echo $GROQ_API_KEY` (Mac/Linux) or `echo %GROQ_API_KEY%` (Windows) |
| Some RSS feeds return 0 entries | Feed URL changed or site down | Normal — agent skips failed feeds automatically |

---

## PART 6 — Your Final File Structure

After setup, your repo should contain ONLY these files:
```
ANN-Global/
├── index.html   ← The website (reads news.json dynamically)
├── agent.py     ← Run this to update news
├── news.json    ← Generated by agent.py — commit this to update site
├── CNAME        ← Contains: annfeed.com
└── README.md    ← This file
```

No `_config.yml`. No `index.md`. No duplicate HTML files. Nothing else.

---

## Quick Reference

```bash
# Full update in one command:
python agent.py --push

# Check your site:
# https://annfeed.com  (after DNS propagates)
# https://YOUR_USERNAME.github.io/ANN-Global  (works immediately)

# If something breaks, reset to last working state:
git log --oneline          # see recent commits
git revert HEAD            # undo last commit safely
git push origin main
```
