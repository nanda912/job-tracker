#!/usr/bin/env python3
"""
Executive Job Search — Auto-Update & Publish
Searches for new jobs, updates the dashboard, and pushes to GitHub Pages.
Runs daily via macOS launchd (8 AM + 6 PM CT).
"""

import os
import sys
import json
import re
import subprocess
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime

# === CONFIG ===
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DASHBOARD_PATH = os.path.join(SCRIPT_DIR, "index.html")
DATA_PATH = os.path.join(SCRIPT_DIR, "jobs_data.json")
LOG_PATH = os.path.join(os.path.expanduser("~"), "Desktop", "job_search_log.txt")

# Search queries
SEARCH_QUERIES = [
    "CFO fintech remote",
    "VP Finance fintech remote",
    "VP Finance technology remote",
    "Senior Director Financial Systems remote",
    "Head of Finance fintech remote",
    "Finance Transformation Director remote",
    "Director Finance Technology remote",
    "VP Financial Systems remote",
    "Head Financial Planning Analysis remote",
]

# Target companies to check
TARGET_COMPANIES = [
    "Stripe", "PayPal", "Block", "Brex", "Ramp", "Chime", "Plaid",
    "Marqeta", "Adyen", "Wise", "Snowflake", "Databricks", "ServiceNow",
    "Salesforce", "Workday", "UiPath", "Palantir", "Robinhood", "SoFi",
    "Coinbase", "Intuit", "Instacart", "Affirm"
]

# Keywords for fit scoring
TITLE_KEYWORDS = {
    "vp": 15, "vice president": 15, "head": 14, "senior director": 13,
    "director": 10, "cfo": 18, "cpo": 15, "chief": 16,
    "finance": 12, "financial": 12, "fintech": 10, "technology": 8,
    "systems": 8, "transformation": 10, "strategy": 8, "erp": 10,
    "treasury": 8, "accounting": 6, "planning": 7, "analytics": 7,
    "product": 6, "operations": 6, "risk": 5, "controls": 5,
    "automation": 8, "data": 5, "ai": 8, "digital": 7,
}


def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    try:
        with open(LOG_PATH, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass


def search_indeed_rss(query, limit=25):
    """Search Indeed RSS feed for jobs."""
    results = []
    try:
        encoded = urllib.parse.quote(query)
        url = f"https://www.indeed.com/rss?q={encoded}&l=Remote&sort=date&limit={limit}"
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            xml_data = resp.read().decode("utf-8")
        root = ET.fromstring(xml_data)
        for item in root.findall(".//item"):
            title = item.findtext("title", "").strip()
            link = item.findtext("link", "").strip()
            pub_date = item.findtext("pubDate", "").strip()
            # Extract company from title (usually "Job Title - Company")
            parts = title.rsplit(" - ", 1)
            job_title = parts[0].strip() if parts else title
            company = parts[1].strip() if len(parts) > 1 else "Unknown"
            results.append({
                "title": job_title,
                "company": company,
                "link": link,
                "pubDate": pub_date,
                "source": "indeed",
            })
    except Exception as e:
        log(f"  Search failed for '{query}': {e}")
    return results


def calculate_fit_score(title, company, location=""):
    """Calculate fit score 0-100 based on title/company/location keywords."""
    score = 40  # base
    title_lower = title.lower()
    company_lower = company.lower()
    loc_lower = location.lower()

    for keyword, points in TITLE_KEYWORDS.items():
        if keyword in title_lower:
            score += points

    # Company bonus
    for tc in TARGET_COMPANIES:
        if tc.lower() in company_lower:
            score += 8
            break

    # Remote bonus
    if "remote" in loc_lower or "remote" in title_lower:
        score += 5

    return min(score, 100)


def load_existing_data():
    """Load existing jobs from JSON data file."""
    if os.path.exists(DATA_PATH):
        try:
            with open(DATA_PATH, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def save_data(jobs):
    """Save jobs to JSON data file."""
    with open(DATA_PATH, "w") as f:
        json.dump(jobs, f, indent=2)


def deduplicate_key(title, company):
    """Create a dedup key from title + company."""
    return f"{title.lower().strip()}|{company.lower().strip()}"


def search_all():
    """Run all searches and return new jobs."""
    existing = load_existing_data()
    existing_keys = set()
    for j in existing:
        existing_keys.add(deduplicate_key(j.get("title", ""), j.get("company", "")))

    new_jobs = []
    today = datetime.now().strftime("%m/%d/%Y")
    next_id = max([j.get("id", 0) for j in existing], default=100) + 1

    log(f"Running {len(SEARCH_QUERIES)} search queries...")

    for i, query in enumerate(SEARCH_QUERIES, 1):
        log(f"  [{i}/{len(SEARCH_QUERIES)}] Searching: {query}")
        results = search_indeed_rss(query)
        log(f"    Found {len(results)} results")

        for r in results:
            key = deduplicate_key(r["title"], r["company"])
            if key in existing_keys:
                continue
            existing_keys.add(key)

            score = calculate_fit_score(r["title"], r["company"])
            if score < 70:
                continue

            new_jobs.append({
                "id": next_id,
                "company": r["company"],
                "title": r["title"],
                "location": "Remote",
                "salary": "TBD",
                "remote": "Yes",
                "link": r["link"],
                "score": score,
                "reason": f"Found via Indeed search: '{query}'. Auto-scored based on title/company keywords.",
                "discovered": today,
                "source": "general",
                "isNew": True,
                "status": "not-applied",
                "notes": "",
            })
            next_id += 1

    # Mark old jobs as no longer new (if discovered > 2 days ago)
    for j in existing:
        j["isNew"] = j.get("discovered", "") == today

    all_jobs = existing + new_jobs
    save_data(all_jobs)
    return all_jobs, len(new_jobs)


def rebuild_dashboard(jobs):
    """Rebuild the index.html dashboard with current job data."""
    if not os.path.exists(DASHBOARD_PATH):
        log("ERROR: index.html not found!")
        return False

    with open(DASHBOARD_PATH, "r") as f:
        html = f.read()

    # Replace the JOBS array in the HTML
    jobs_json = json.dumps(jobs, indent=2)

    # Find and replace the JOBS constant
    pattern = r'const JOBS = \[.*?\];'
    replacement = f'const JOBS = {jobs_json};'

    new_html = re.sub(pattern, replacement, html, flags=re.DOTALL)

    if new_html == html:
        log("WARNING: Could not find JOBS array in HTML to update")
        return False

    with open(DASHBOARD_PATH, "w") as f:
        f.write(new_html)

    log("Dashboard HTML updated with latest data")
    return True


def git_push():
    """Commit and push changes to GitHub."""
    try:
        os.chdir(SCRIPT_DIR)
        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        # Check if there are changes
        result = subprocess.run(["git", "status", "--porcelain"],
                                capture_output=True, text=True, cwd=SCRIPT_DIR)
        if not result.stdout.strip():
            log("No changes to commit")
            return True

        subprocess.run(["git", "add", "-A"], cwd=SCRIPT_DIR, check=True)
        subprocess.run(
            ["git", "commit", "-m", f"Auto-update: {now}"],
            cwd=SCRIPT_DIR, check=True
        )
        subprocess.run(["git", "push"], cwd=SCRIPT_DIR, check=True)
        log("Pushed to GitHub — dashboard will auto-deploy via GitHub Pages")
        return True
    except Exception as e:
        log(f"Git push failed: {e}")
        return False


def main():
    log("=" * 60)
    log("  EXECUTIVE JOB SEARCH — Auto-Update & Publish")
    log(f"  {datetime.now().strftime('%A, %B %d, %Y at %I:%M %p')}")
    log("=" * 60)

    # 1. Search for new jobs
    all_jobs, new_count = search_all()
    log(f"Total jobs: {len(all_jobs)} | New today: {new_count}")

    # 2. Rebuild dashboard
    rebuild_dashboard(all_jobs)

    # 3. Push to GitHub
    git_push()

    log("=" * 60)
    log("  DONE")
    log("=" * 60)


if __name__ == "__main__":
    main()
