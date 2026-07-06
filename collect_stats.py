#!/usr/bin/env python3
"""
GitHub Stats Collector
Собирает метрики репозитория и сохраняет в SQLite.
Запускается через GitHub Actions раз в 14 дней (или чаще).
"""

import os
import sys
import json
import sqlite3
import requests
from datetime import datetime, timedelta
from pathlib import Path

# ============ КОНФИГУРАЦИЯ ============
# Токен GitHub (с правами на чтение трафика репозитория)
# Для traffic API нужен Personal Access Token (PAT) с правами repo + read:user
# GITHUB_TOKEN от Actions НЕ подходит для traffic API!
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
# Список репозиториев для отслеживания (owner/repo)
REPOS = os.environ.get("REPOS", "WowCatQwerty/vps-net-stat").split(",")
# Путь к базе данных
DB_PATH = Path(os.environ.get("DB_PATH", "data/stats.db"))

# ============ БАЗА ДАННЫХ ============

def init_db():
    """Создаёт таблицы, если их нет."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Основная информация о репозитории (снимок)
    c.execute("""
        CREATE TABLE IF NOT EXISTS repo_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            repo TEXT NOT NULL,
            date TEXT NOT NULL,
            stars INTEGER,
            forks INTEGER,
            watchers INTEGER,
            open_issues INTEGER,
            UNIQUE(repo, date)
        )
    """)

    # Просмотры (traffic views) — только 14 дней от GitHub
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

    # Клонирования (traffic clones) — только 14 дней от GitHub
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

    # Referring sites — 14 дней
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

    # Popular paths — 14 дней
    c.execute("""
        CREATE TABLE IF NOT EXISTS popular_paths (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            repo TEXT NOT NULL,
            date TEXT NOT NULL,
            path TEXT NOT NULL,
            title TEXT,
            count INTEGER,
            uniques INTEGER,
            UNIQUE(repo, date, path)
        )
    """)

    # Stargazers — для графика stars over time
    c.execute("""
        CREATE TABLE IF NOT EXISTS stargazers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            repo TEXT NOT NULL,
            starred_at TEXT NOT NULL,
            user TEXT
        )
    """)

    # Issues activity
    c.execute("""
        CREATE TABLE IF NOT EXISTS issues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            repo TEXT NOT NULL,
            date TEXT NOT NULL,
            open_count INTEGER,
            closed_count INTEGER,
            UNIQUE(repo, date)
        )
    """)

    # Commits activity
    c.execute("""
        CREATE TABLE IF NOT EXISTS commits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            repo TEXT NOT NULL,
            week TEXT NOT NULL,
            total INTEGER,
            additions INTEGER,
            deletions INTEGER,
            UNIQUE(repo, week)
        )
    """)

    conn.commit()
    conn.close()
    print(f"✓ База данных инициализирована: {DB_PATH}")

# ============ API ЗАПРОСЫ ============

def api_get(url, token=GITHUB_TOKEN):
    """Делает GET-запрос к GitHub API."""
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    try:
        resp = requests.get(url, headers=headers, timeout=30)
        if resp.status_code == 403:
            print(f"⚠ Rate limit или нет прав для {url}")
            return None
        if resp.status_code == 404:
            print(f"⚠ Не найдено: {url}")
            return None
        if resp.status_code == 202:
            print(f"⚠ Данные ещё собираются (202): {url}")
            return None
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"✗ Ошибка запроса {url}: {e}")
        return None

def collect_repo_info(repo):
    """Собирает основную информацию о репозитории."""
    data = api_get(f"https://api.github.com/repos/{repo}")
    if not data:
        return

    today = datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT OR REPLACE INTO repo_snapshots 
        (repo, date, stars, forks, watchers, open_issues)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (repo, today, data.get("stargazers_count", 0),
          data.get("forks_count", 0), data.get("watchers_count", 0),
          data.get("open_issues_count", 0)))
    conn.commit()
    conn.close()
    print(f"  ✓ Repo info: {data['stargazers_count']} stars, {data['forks_count']} forks")

def collect_traffic_views(repo):
    """Собирает просмотры (14 дней)."""
    data = api_get(f"https://api.github.com/repos/{repo}/traffic/views")
    if not data or "views" not in data:
        return

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    for day in data["views"]:
        date = day["timestamp"][:10]
        c.execute("""
            INSERT OR REPLACE INTO traffic_views (repo, date, count, uniques)
            VALUES (?, ?, ?, ?)
        """, (repo, date, day.get("count", 0), day.get("uniques", 0)))
    conn.commit()
    conn.close()
    print(f"  ✓ Traffic views: {len(data['views'])} дней")

def collect_traffic_clones(repo):
    """Собирает клонирования (14 дней)."""
    data = api_get(f"https://api.github.com/repos/{repo}/traffic/clones")
    if not data or "clones" not in data:
        return

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    for day in data["clones"]:
        date = day["timestamp"][:10]
        c.execute("""
            INSERT OR REPLACE INTO traffic_clones (repo, date, count, uniques)
            VALUES (?, ?, ?, ?)
        """, (repo, date, day.get("count", 0), day.get("uniques", 0)))
    conn.commit()
    conn.close()
    print(f"  ✓ Traffic clones: {len(data['clones'])} дней")

def collect_referrers(repo):
    """Собирает referring sites (14 дней)."""
    data = api_get(f"https://api.github.com/repos/{repo}/traffic/popular/referrers")
    if not data:
        return

    today = datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    for ref in data:
        c.execute("""
            INSERT OR REPLACE INTO referrers (repo, date, referrer, count, uniques)
            VALUES (?, ?, ?, ?, ?)
        """, (repo, today, ref.get("referrer", "unknown"),
              ref.get("count", 0), ref.get("uniques", 0)))
    conn.commit()
    conn.close()
    print(f"  ✓ Referrers: {len(data)} источников")

def collect_popular_paths(repo):
    """Собирает популярные пути (14 дней)."""
    data = api_get(f"https://api.github.com/repos/{repo}/traffic/popular/paths")
    if not data:
        return

    today = datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    for path in data:
        c.execute("""
            INSERT OR REPLACE INTO popular_paths (repo, date, path, title, count, uniques)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (repo, today, path.get("path", ""), path.get("title", ""),
              path.get("count", 0), path.get("uniques", 0)))
    conn.commit()
    conn.close()
    print(f"  ✓ Popular paths: {len(data)} путей")

def collect_stargazers(repo):
    """Собирает список stargazers для графика stars over time."""
    page = 1
    all_stars = []
    while True:
        data = api_get(f"https://api.github.com/repos/{repo}/stargazers?page={page}&per_page=100")
        if not data or len(data) == 0:
            break
        all_stars.extend(data)
        if len(data) < 100:
            break
        page += 1
        if page > 50:  # Защита от бесконечного цикла
            break

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Очищаем старые данные и записываем заново
    c.execute("DELETE FROM stargazers WHERE repo = ?", (repo,))
    for star in all_stars:
        c.execute("""
            INSERT INTO stargazers (repo, starred_at, user)
            VALUES (?, ?, ?)
        """, (repo, star.get("starred_at", "")[:10], star.get("login", "")))
    conn.commit()
    conn.close()
    print(f"  ✓ Stargazers: {len(all_stars)} звёздочек")

def collect_commits(repo):
    """Собирает статистику коммитов."""
    data = api_get(f"https://api.github.com/repos/{repo}/stats/code_frequency")
    if not data:
        return

    # data — список списков: [timestamp, additions, deletions]
    # Некоторые элементы могут быть пустыми или иметь неправильный формат
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    for week in data:
        if not isinstance(week, list) or len(week) < 3:
            continue
        try:
            week_date = datetime.fromtimestamp(week[0]).strftime("%Y-%m-%d")
            additions = week[1] if len(week) > 1 else 0
            deletions = abs(week[2]) if len(week) > 2 else 0
            c.execute("""
                INSERT OR REPLACE INTO commits (repo, week, total, additions, deletions)
                VALUES (?, ?, ?, ?, ?)
            """, (repo, week_date, additions + deletions, additions, deletions))
        except (IndexError, TypeError, ValueError) as e:
            print(f"  ⚠ Пропускаю некорректную неделю: {week} — {e}")
            continue
    conn.commit()
    conn.close()
    print(f"  ✓ Commits: {len(data)} недель")

def collect_issues(repo):
    """Собирает статистику issues."""
    open_data = api_get(f"https://api.github.com/search/issues?q=repo:{repo}+state:open+type:issue")
    closed_data = api_get(f"https://api.github.com/search/issues?q=repo:{repo}+state:closed+type:issue")

    today = datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT OR REPLACE INTO issues (repo, date, open_count, closed_count)
        VALUES (?, ?, ?, ?)
    """, (repo, today,
          open_data.get("total_count", 0) if open_data else 0,
          closed_data.get("total_count", 0) if closed_data else 0))
    conn.commit()
    conn.close()
    print(f"  ✓ Issues: {open_data.get('total_count', 0) if open_data else 0} open")

# ============ ГЛАВНАЯ ФУНКЦИЯ ============

def main():
    if not GITHUB_TOKEN:
        print("✗ Не задан GITHUB_TOKEN")
        sys.exit(1)

    init_db()

    for repo in REPOS:
        repo = repo.strip()
        if not repo:
            continue
        print(f"\n📊 Собираю данные для {repo}...")
        collect_repo_info(repo)
        collect_traffic_views(repo)
        collect_traffic_clones(repo)
        collect_referrers(repo)
        collect_popular_paths(repo)
        collect_stargazers(repo)
        collect_commits(repo)
        collect_issues(repo)

    print("\n✅ Готово!")

if __name__ == "__main__":
    main()
