#!/usr/bin/env python3
"""
GitHub Stats Collector
Собирает: Views, Clones, Stars, Referrers
Запускается через GitHub Actions.
"""

import os
import sys
import sqlite3
import requests
from datetime import datetime, timedelta
from pathlib import Path

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
REPOS = os.environ.get("REPOS", "WowCatQwerty/vps-net-stat").split(",")
DB_PATH = Path(os.environ.get("DB_PATH", "data/stats.db"))

def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS traffic_views (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            repo TEXT NOT NULL,
            date TEXT NOT NULL,
            count INTEGER,
            uniques INTEGER,
            UNIQUE(repo, date)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS traffic_clones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            repo TEXT NOT NULL,
            date TEXT NOT NULL,
            count INTEGER,
            uniques INTEGER,
            UNIQUE(repo, date)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS referrers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            repo TEXT NOT NULL,
            date TEXT NOT NULL,
            referrer TEXT NOT NULL,
            count INTEGER,
            uniques INTEGER,
            UNIQUE(repo, date, referrer)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS repo_info (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            repo TEXT NOT NULL,
            date TEXT NOT NULL,
            stars INTEGER,
            forks INTEGER,
            UNIQUE(repo, date)
        )
    """)

    conn.commit()
    conn.close()
    print(f"✓ База инициализирована: {DB_PATH}")

def api_get(url):
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    try:
        resp = requests.get(url, headers=headers, timeout=30)
        if resp.status_code in (403, 404, 202):
            print(f"⚠ {resp.status_code}: {url}")
            return None
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"✗ Ошибка {url}: {e}")
        return None

def collect_repo_info(repo):
    data = api_get(f"https://api.github.com/repos/{repo}")
    if not data:
        return
    today = datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO repo_info (repo, date, stars, forks) VALUES (?, ?, ?, ?)",
              (repo, today, data.get("stargazers_count", 0), data.get("forks_count", 0)))
    conn.commit()
    conn.close()
    print(f"  ✓ Stars: {data['stargazers_count']}, Forks: {data['forks_count']}")

def collect_traffic_views(repo):
    data = api_get(f"https://api.github.com/repos/{repo}/traffic/views")
    if not data or "views" not in data:
        return
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    for day in data["views"]:
        date = day["timestamp"][:10]
        c.execute("INSERT OR REPLACE INTO traffic_views (repo, date, count, uniques) VALUES (?, ?, ?, ?)",
                  (repo, date, day.get("count", 0), day.get("uniques", 0)))
    conn.commit()
    conn.close()
    print(f"  ✓ Views: {len(data['views'])} дней")

def collect_traffic_clones(repo):
    data = api_get(f"https://api.github.com/repos/{repo}/traffic/clones")
    if not data or "clones" not in data:
        return
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    for day in data["clones"]:
        date = day["timestamp"][:10]
        c.execute("INSERT OR REPLACE INTO traffic_clones (repo, date, count, uniques) VALUES (?, ?, ?, ?)",
                  (repo, date, day.get("count", 0), day.get("uniques", 0)))
    conn.commit()
    conn.close()
    print(f"  ✓ Clones: {len(data['clones'])} дней")

def collect_referrers(repo):
    data = api_get(f"https://api.github.com/repos/{repo}/traffic/popular/referrers")
    if not data:
        return
    today = datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    for ref in data:
        c.execute("INSERT OR REPLACE INTO referrers (repo, date, referrer, count, uniques) VALUES (?, ?, ?, ?, ?)",
                  (repo, today, ref.get("referrer", "unknown"), ref.get("count", 0), ref.get("uniques", 0)))
    conn.commit()
    conn.close()
    print(f"  ✓ Referrers: {len(data)} источников")

def main():
    if not GITHUB_TOKEN:
        print("✗ Не задан GITHUB_TOKEN"); sys.exit(1)
    init_db()
    for repo in REPOS:
        repo = repo.strip()
        if not repo: continue
        print(f"\n📊 {repo}...")
        collect_repo_info(repo)
        collect_traffic_views(repo)
        collect_traffic_clones(repo)
        collect_referrers(repo)
    print("\n✅ Готово!")

if __name__ == "__main__":
    main()
