#!/usr/bin/env python3
"""
Генератор HTML-дашборда из SQLite базы.
Создаёт интерактивную страницу с графиками в стиле vps-net-stat.
"""

import os
import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(os.environ.get("DB_PATH", "data/stats.db"))
OUTPUT_PATH = Path(os.environ.get("OUTPUT_PATH", "docs/index.html"))
REPO = os.environ.get("REPOS", "WowCatQwerty/vps-net-stat").split(",")[0].strip()

def get_db_data():
    """Извлекает все данные из базы."""
    if not DB_PATH.exists():
        return {}

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    data = {}

    # Repo snapshots
    c.execute("SELECT * FROM repo_snapshots WHERE repo = ? ORDER BY date", (REPO,))
    data["snapshots"] = [dict(r) for r in c.fetchall()]

    # Traffic views
    c.execute("SELECT * FROM traffic_views WHERE repo = ? ORDER BY date", (REPO,))
    data["views"] = [dict(r) for r in c.fetchall()]

    # Traffic clones
    c.execute("SELECT * FROM traffic_clones WHERE repo = ? ORDER BY date", (REPO,))
    data["clones"] = [dict(r) for r in c.fetchall()]

    # Referrers (последние)
    c.execute("""
        SELECT referrer, SUM(count) as total_count, SUM(uniques) as total_uniques
        FROM referrers WHERE repo = ?
        GROUP BY referrer ORDER BY total_count DESC LIMIT 10
    """, (REPO,))
    data["referrers"] = [dict(r) for r in c.fetchall()]

    # Popular paths (последние)
    c.execute("""
        SELECT path, title, SUM(count) as total_count, SUM(uniques) as total_uniques
        FROM popular_paths WHERE repo = ?
        GROUP BY path ORDER BY total_count DESC LIMIT 10
    """, (REPO,))
    data["paths"] = [dict(r) for r in c.fetchall()]

    # Stargazers
    c.execute("""
        SELECT starred_at, COUNT(*) as count 
        FROM stargazers WHERE repo = ?
        GROUP BY starred_at ORDER BY starred_at
    """, (REPO,))
    data["stargazers"] = [dict(r) for r in c.fetchall()]

    # Commits
    c.execute("SELECT * FROM commits WHERE repo = ? ORDER BY week", (REPO,))
    data["commits"] = [dict(r) for r in c.fetchall()]

    # Issues
    c.execute("SELECT * FROM issues WHERE repo = ? ORDER BY date", (REPO,))
    data["issues"] = [dict(r) for r in c.fetchall()]

    conn.close()
    return data

def generate_html(data):
    """Генерирует HTML-дашборд."""

    # Подготовка данных для графиков
    views_dates = [r["date"] for r in data.get("views", [])]
    views_total = [r["count"] for r in data.get("views", [])]
    views_unique = [r["uniques"] for r in data.get("views", [])]

    clones_dates = [r["date"] for r in data.get("clones", [])]
    clones_total = [r["count"] for r in data.get("clones", [])]
    clones_unique = [r["uniques"] for r in data.get("clones", [])]

    # Stars over time (cumulative)
    stars_dates = []
    stars_cumulative = []
    cumsum = 0
    for r in data.get("stargazers", []):
        stars_dates.append(r["starred_at"])
        cumsum += r["count"]
        stars_cumulative.append(cumsum)

    # Если нет данных по stargazers, используем snapshots
    if not stars_cumulative and data.get("snapshots"):
        stars_dates = [r["date"] for r in data["snapshots"]]
        stars_cumulative = [r["stars"] for r in data["snapshots"]]

    # Referrers
    ref_labels = [r["referrer"] for r in data.get("referrers", [])]
    ref_values = [r["total_count"] for r in data.get("referrers", [])]

    # Popular paths
    path_labels = [r["path"] for r in data.get("paths", [])]
    path_values = [r["total_count"] for r in data.get("paths", [])]

    # Commits
    commit_weeks = [r["week"] for r in data.get("commits", [])]
    commit_additions = [r["additions"] for r in data.get("commits", [])]
    commit_deletions = [r["deletions"] for r in data.get("commits", [])]

    # Issues
    issues_dates = [r["date"] for r in data.get("issues", [])]
    issues_open = [r["open_count"] for r in data.get("issues", [])]
    issues_closed = [r["closed_count"] for r in data.get("issues", [])]

    # Последние значения
    latest = data.get("snapshots", [{}])[-1] if data.get("snapshots") else {}
    total_stars = latest.get("stars", 0)
    total_forks = latest.get("forks", 0)
    total_views = sum(views_total) if views_total else 0
    total_clones = sum(clones_total) if clones_total else 0

    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{REPO} — Stats Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
    <style>
        :root {{
            --bg: #0d1117;
            --bg-card: #161b22;
            --bg-card-hover: #1c2128;
            --border: #30363d;
            --text: #c9d1d9;
            --text-muted: #8b949e;
            --accent: #58a6ff;
            --accent-green: #3fb950;
            --accent-orange: #f0883e;
            --accent-red: #f85149;
            --accent-purple: #a371f7;
            --font-mono: 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, monospace;
            --font-sans: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }}

        * {{ margin: 0; padding: 0; box-sizing: border-box; }}

        body {{
            background: var(--bg);
            color: var(--text);
            font-family: var(--font-sans);
            line-height: 1.6;
            min-height: 100vh;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 40px 20px;
        }}

        header {{
            text-align: center;
            margin-bottom: 40px;
            padding-bottom: 30px;
            border-bottom: 1px solid var(--border);
        }}

        header h1 {{
            font-family: var(--font-mono);
            font-size: 2rem;
            color: var(--accent);
            margin-bottom: 8px;
        }}

        header h1::before {{
            content: "📊 ";
        }}

        header .subtitle {{
            color: var(--text-muted);
            font-size: 0.95rem;
        }}

        header .repo-link {{
            display: inline-block;
            margin-top: 12px;
            color: var(--accent);
            text-decoration: none;
            font-family: var(--font-mono);
            font-size: 0.9rem;
            padding: 6px 14px;
            border: 1px solid var(--border);
            border-radius: 6px;
            transition: all 0.2s;
        }}

        header .repo-link:hover {{
            background: var(--bg-card);
            border-color: var(--accent);
        }}

        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 16px;
            margin-bottom: 30px;
        }}

        .stat-card {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 20px;
            transition: transform 0.2s, border-color 0.2s;
        }}

        .stat-card:hover {{
            transform: translateY(-2px);
            border-color: var(--accent);
        }}

        .stat-card .label {{
            color: var(--text-muted);
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
        }}

        .stat-card .value {{
            font-family: var(--font-mono);
            font-size: 1.8rem;
            font-weight: 600;
        }}

        .stat-card.stars .value {{ color: var(--accent); }}
        .stat-card.forks .value {{ color: var(--accent-green); }}
        .stat-card.views .value {{ color: var(--accent-orange); }}
        .stat-card.clones .value {{ color: var(--accent-purple); }}

        .chart-card {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 20px;
        }}

        .chart-card h2 {{
            font-family: var(--font-mono);
            font-size: 1.1rem;
            margin-bottom: 4px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        .chart-card .desc {{
            color: var(--text-muted);
            font-size: 0.85rem;
            margin-bottom: 20px;
        }}

        .chart-wrapper {{
            position: relative;
            height: 300px;
        }}

        .chart-wrapper.small {{
            height: 250px;
        }}

        .two-col {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(450px, 1fr));
            gap: 20px;
        }}

        .referrer-list, .path-list {{
            list-style: none;
        }}

        .referrer-list li, .path-list li {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 0;
            border-bottom: 1px solid var(--border);
            font-family: var(--font-mono);
            font-size: 0.9rem;
        }}

        .referrer-list li:last-child, .path-list li:last-child {{
            border-bottom: none;
        }}

        .referrer-list .name, .path-list .name {{
            color: var(--accent);
        }}

        .referrer-list .count, .path-list .count {{
            color: var(--text-muted);
            font-size: 0.85rem;
        }}

        .empty-state {{
            text-align: center;
            padding: 60px 20px;
            color: var(--text-muted);
        }}

        .empty-state .icon {{
            font-size: 3rem;
            margin-bottom: 16px;
            opacity: 0.5;
        }}

        footer {{
            text-align: center;
            padding: 30px;
            color: var(--text-muted);
            font-size: 0.85rem;
            border-top: 1px solid var(--border);
            margin-top: 20px;
        }}

        footer .update-time {{
            font-family: var(--font-mono);
        }}

        @media (max-width: 600px) {{
            .two-col {{ grid-template-columns: 1fr; }}
            .stats-grid {{ grid-template-columns: repeat(2, 1fr); }}
            header h1 {{ font-size: 1.4rem; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>{REPO}</h1>
            <p class="subtitle">Статистика репозитория за всё время</p>
            <a href="https://github.com/{REPO}" class="repo-link" target="_blank">
                github.com/{REPO} ↗
            </a>
        </header>

        <div class="stats-grid">
            <div class="stat-card stars">
                <div class="label">⭐ Stars</div>
                <div class="value">{total_stars:,}</div>
            </div>
            <div class="stat-card forks">
                <div class="label">🍴 Forks</div>
                <div class="value">{total_forks:,}</div>
            </div>
            <div class="stat-card views">
                <div class="label">👁 Views (14d)</div>
                <div class="value">{total_views:,}</div>
            </div>
            <div class="stat-card clones">
                <div class="label">📥 Clones (14d)</div>
                <div class="value">{total_clones:,}</div>
            </div>
        </div>
"""

    # Stars Over Time
    if stars_cumulative:
        html += f"""
        <div class="chart-card">
            <h2>⭐ Stars Over Time</h2>
            <p class="desc">Накопительный рост звёздочек</p>
            <div class="chart-wrapper">
                <canvas id="starsChart"></canvas>
            </div>
        </div>
"""

    # Views + Clones
    if views_dates or clones_dates:
        html += """
        <div class="two-col">
"""
        if views_dates:
            html += """
            <div class="chart-card">
                <h2>👁 Repo Views</h2>
                <p class="desc">Просмотры страницы репозитория</p>
                <div class="chart-wrapper small">
                    <canvas id="viewsChart"></canvas>
                </div>
            </div>
"""
        if clones_dates:
            html += """
            <div class="chart-card">
                <h2>📥 Repo Clones</h2>
                <p class="desc">Клонирования репозитория</p>
                <div class="chart-wrapper small">
                    <canvas id="clonesChart"></canvas>
                </div>
            </div>
"""
        html += """
        </div>
"""

    # Referrers + Popular Paths
    if ref_labels or path_labels:
        html += """
        <div class="two-col">
"""
        if ref_labels:
            html += """
            <div class="chart-card">
                <h2>🔗 Referring Sites</h2>
                <p class="desc">Источники трафика</p>
                <ul class="referrer-list">
"""
            for ref in data.get("referrers", []):
                html += f"""
                    <li>
                        <span class="name">{ref["referrer"]}</span>
                        <span class="count">{ref["total_count"]:,} views · {ref["total_uniques"]:,} unique</span>
                    </li>
"""
            html += """
                </ul>
            </div>
"""
        if path_labels:
            html += """
            <div class="chart-card">
                <h2>📄 Popular Content</h2>
                <p class="desc">Самые посещаемые страницы</p>
                <ul class="path-list">
"""
            for path in data.get("paths", []):
                display_path = path["path"][:40] + "..." if len(path["path"]) > 40 else path["path"]
                html += f"""
                    <li>
                        <span class="name">{display_path}</span>
                        <span class="count">{path["total_count"]:,} views</span>
                    </li>
"""
            html += """
                </ul>
            </div>
"""
        html += """
        </div>
"""

    # Commits
    if commit_weeks:
        html += """
        <div class="chart-card">
            <h2>💻 Code Activity</h2>
            <p class="desc">Добавления и удаления строк кода по неделям</p>
            <div class="chart-wrapper">
                <canvas id="commitsChart"></canvas>
            </div>
        </div>
"""

    # Issues
    if issues_dates:
        html += """
        <div class="chart-card">
            <h2>🐛 Issues</h2>
            <p class="desc">Открытые и закрытые issues</p>
            <div class="chart-wrapper small">
                <canvas id="issuesChart"></canvas>
            </div>
        </div>
"""

    # Если совсем нет данных
    if not any([stars_cumulative, views_dates, clones_dates, ref_labels, path_labels, commit_weeks, issues_dates]):
        html += """
        <div class="empty-state">
            <div class="icon">📭</div>
            <p>Пока нет данных. Запустите сбор статистики — данные появятся здесь.</p>
        </div>
"""

    html += f"""
        <footer>
            <p>Автоматически обновляется раз в 14 дней</p>
            <p class="update-time">Последнее обновление: {datetime.now().strftime("%Y-%m-%d %H:%M")}</p>
        </footer>
    </div>

    <script>
        Chart.defaults.color = '#8b949e';
        Chart.defaults.borderColor = '#30363d';
        Chart.defaults.font.family = "'SF Mono', Monaco, monospace";

        const commonOptions = {{
            responsive: true,
            maintainAspectRatio: false,
            interaction: {{
                mode: 'index',
                intersect: false,
            }},
            plugins: {{
                legend: {{
                    labels: {{ color: '#c9d1d9' }}
                }}
            }},
            scales: {{
                x: {{
                    grid: {{ color: '#21262d' }},
                    ticks: {{ color: '#8b949e', maxRotation: 45 }}
                }},
                y: {{
                    grid: {{ color: '#21262d' }},
                    ticks: {{ color: '#8b949e' }}
                }}
            }}
        }};
"""

    # Stars chart
    if stars_cumulative:
        html += f"""
        new Chart(document.getElementById('starsChart'), {{
            type: 'line',
            data: {{
                labels: {json.dumps(stars_dates)},
                datasets: [{{
                    label: 'Stars (cumulative)',
                    data: {json.dumps(stars_cumulative)},
                    borderColor: '#58a6ff',
                    backgroundColor: 'rgba(88, 166, 255, 0.1)',
                    fill: true,
                    tension: 0.3,
                    pointRadius: 2,
                    pointHoverRadius: 6
                }}]
            }},
            options: {{
                ...commonOptions,
                plugins: {{
                    legend: {{ display: false }}
                }}
            }}
        }});
"""

    # Views chart
    if views_dates:
        html += f"""
        new Chart(document.getElementById('viewsChart'), {{
            type: 'line',
            data: {{
                labels: {json.dumps(views_dates)},
                datasets: [
                    {{
                        label: 'Unique',
                        data: {json.dumps(views_unique)},
                        borderColor: '#58a6ff',
                        backgroundColor: 'rgba(88, 166, 255, 0.1)',
                        fill: true,
                        tension: 0.3,
                        pointRadius: 2
                    }},
                    {{
                        label: 'Total',
                        data: {json.dumps(views_total)},
                        borderColor: '#3fb950',
                        backgroundColor: 'rgba(63, 185, 80, 0.05)',
                        fill: true,
                        tension: 0.3,
                        pointRadius: 2
                    }}
                ]
            }},
            options: commonOptions
        }});
"""

    # Clones chart
    if clones_dates:
        html += f"""
        new Chart(document.getElementById('clonesChart'), {{
            type: 'line',
            data: {{
                labels: {json.dumps(clones_dates)},
                datasets: [
                    {{
                        label: 'Unique',
                        data: {json.dumps(clones_unique)},
                        borderColor: '#58a6ff',
                        backgroundColor: 'rgba(88, 166, 255, 0.1)',
                        fill: true,
                        tension: 0.3,
                        pointRadius: 2
                    }},
                    {{
                        label: 'Total',
                        data: {json.dumps(clones_total)},
                        borderColor: '#a371f7',
                        backgroundColor: 'rgba(163, 113, 247, 0.05)',
                        fill: true,
                        tension: 0.3,
                        pointRadius: 2
                    }}
                ]
            }},
            options: commonOptions
        }});
"""

    # Commits chart
    if commit_weeks:
        html += f"""
        new Chart(document.getElementById('commitsChart'), {{
            type: 'bar',
            data: {{
                labels: {json.dumps(commit_weeks)},
                datasets: [
                    {{
                        label: 'Additions',
                        data: {json.dumps(commit_additions)},
                        backgroundColor: '#3fb950',
                        borderRadius: 3
                    }},
                    {{
                        label: 'Deletions',
                        data: {json.dumps([-(d) for d in commit_deletions])},
                        backgroundColor: '#f85149',
                        borderRadius: 3
                    }}
                ]
            }},
            options: {{
                ...commonOptions,
                scales: {{
                    x: {{
                        stacked: true,
                        grid: {{ color: '#21262d' }},
                        ticks: {{ color: '#8b949e', maxRotation: 45 }}
                    }},
                    y: {{
                        stacked: true,
                        grid: {{ color: '#21262d' }},
                        ticks: {{ color: '#8b949e' }}
                    }}
                }}
            }}
        }});
"""

    # Issues chart
    if issues_dates:
        html += f"""
        new Chart(document.getElementById('issuesChart'), {{
            type: 'line',
            data: {{
                labels: {json.dumps(issues_dates)},
                datasets: [
                    {{
                        label: 'Open',
                        data: {json.dumps(issues_open)},
                        borderColor: '#f0883e',
                        backgroundColor: 'rgba(240, 136, 62, 0.1)',
                        fill: true,
                        tension: 0.3,
                        pointRadius: 3
                    }},
                    {{
                        label: 'Closed',
                        data: {json.dumps(issues_closed)},
                        borderColor: '#3fb950',
                        backgroundColor: 'rgba(63, 185, 80, 0.1)',
                        fill: true,
                        tension: 0.3,
                        pointRadius: 3
                    }}
                ]
            }},
            options: commonOptions
        }});
"""

    html += """
    </script>
</body>
</html>
"""

    return html

def main():
    print("📊 Генерирую дашборд...")
    data = get_db_data()
    html = generate_html(data)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"✓ Дашборд сохранён: {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
