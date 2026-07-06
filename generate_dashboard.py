#!/usr/bin/env python3
import os
import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(os.environ.get("DB_PATH", "data/stats.db"))
OUTPUT_PATH = Path(os.environ.get("OUTPUT_PATH", "docs/index.html"))
REPO = os.environ.get("REPOS", "WowCatQwerty/vps-net-stat").split(",")[0].strip()

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{repo} — Stats</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
    <style>
        :root {
            --bg: #0d1117;
            --bg-card: #161b22;
            --border: #30363d;
            --text: #c9d1d9;
            --text-muted: #8b949e;
            --accent: #58a6ff;
            --accent-green: #3fb950;
            --font-mono: 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, monospace;
            --font-sans: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background: var(--bg);
            color: var(--text);
            font-family: var(--font-sans);
            line-height: 1.6;
            min-height: 100vh;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 40px 20px;
        }
        header {
            text-align: center;
            margin-bottom: 40px;
            padding-bottom: 30px;
            border-bottom: 1px solid var(--border);
        }
        header h1 {
            font-family: var(--font-mono);
            font-size: 1.8rem;
            color: var(--text);
            margin-bottom: 8px;
        }
        header .repo-link {
            color: var(--accent);
            text-decoration: none;
            font-family: var(--font-mono);
            font-size: 0.85rem;
        }
        .stars-block {
            text-align: center;
            margin-bottom: 40px;
            padding: 30px;
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
        }
        .stars-block .stars-value {
            font-family: var(--font-mono);
            font-size: 4rem;
            font-weight: 700;
            color: var(--accent);
        }
        .stars-block .stars-label {
            color: var(--text-muted);
            font-size: 1rem;
            margin-top: 8px;
        }
        .stars-block .forks-value {
            font-family: var(--font-mono);
            font-size: 1.2rem;
            color: var(--accent-green);
            margin-top: 12px;
        }
        .chart-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 24px;
        }
        .chart-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            flex-wrap: wrap;
            gap: 12px;
        }
        .chart-header h2 {
            font-family: var(--font-mono);
            font-size: 1rem;
            color: var(--text);
        }
        .period-tabs {
            display: flex;
            gap: 4px;
            background: var(--bg);
            padding: 4px;
            border-radius: 8px;
            border: 1px solid var(--border);
        }
        .period-tabs button {
            background: transparent;
            border: none;
            color: var(--text-muted);
            font-family: var(--font-mono);
            font-size: 0.8rem;
            padding: 6px 14px;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.2s;
        }
        .period-tabs button:hover {
            color: var(--text);
        }
        .period-tabs button.active {
            background: var(--border);
            color: var(--text);
        }
        .chart-wrapper {
            position: relative;
            height: 280px;
        }
        .referrer-chart-wrapper {
            position: relative;
            height: 320px;
        }
        footer {
            text-align: center;
            padding: 30px;
            color: var(--text-muted);
            font-size: 0.8rem;
            border-top: 1px solid var(--border);
            margin-top: 20px;
            font-family: var(--font-mono);
        }
        @media (max-width: 600px) {
            .stars-block .stars-value { font-size: 2.5rem; }
            .chart-header { flex-direction: column; align-items: flex-start; }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>{repo}</h1>
            <a href="https://github.com/{repo}" class="repo-link" target="_blank">github.com/{repo}</a>
        </header>
        
        <div class="stars-block">
            <div class="stars-value">⭐ {stars}</div>
            <div class="stars-label">stars total</div>
            <div class="forks-value">🍴 {forks} forks</div>
        </div>
        
        <div class="chart-card">
            <div class="chart-header">
                <h2>👁 Views</h2>
                <div class="period-tabs" data-chart="views">
                    <button class="active" onclick="switchPeriod('views', 'month')">Month</button>
                    <button onclick="switchPeriod('views', 'year')">Year</button>
                    <button onclick="switchPeriod('views', 'all')">All</button>
                </div>
            </div>
            <div class="chart-wrapper">
                <canvas id="viewsChart"></canvas>
            </div>
        </div>
        
        <div class="chart-card">
            <div class="chart-header">
                <h2>📥 Clones</h2>
                <div class="period-tabs" data-chart="clones">
                    <button class="active" onclick="switchPeriod('clones', 'month')">Month</button>
                    <button onclick="switchPeriod('clones', 'year')">Year</button>
                    <button onclick="switchPeriod('clones', 'all')">All</button>
                </div>
            </div>
            <div class="chart-wrapper">
                <canvas id="clonesChart"></canvas>
            </div>
        </div>
        
        <div class="chart-card">
            <div class="chart-header">
                <h2>🔗 Referring Sites</h2>
                <div class="period-tabs" data-chart="referrers">
                    <button class="active" onclick="switchPeriod('referrers', 'month')">Month</button>
                    <button onclick="switchPeriod('referrers', 'year')">Year</button>
                    <button onclick="switchPeriod('referrers', 'all')">All</button>
                </div>
            </div>
            <div class="referrer-chart-wrapper">
                <canvas id="referrersChart"></canvas>
            </div>
        </div>
        
        <footer>
            Updated: {update_time} · Auto-collect every 7 days
        </footer>
    </div>
    
    <script>
        Chart.defaults.color = '#8b949e';
        Chart.defaults.borderColor = '#21262d';
        Chart.defaults.font.family = "'SF Mono', Monaco, monospace";
        
        const viewsData = {views_json};
        const clonesData = {clones_json};
        const referrersRaw = {referrers_json};
        
        const charts = {};
        
        function createLineChart(canvasId, data, label, color) {
            const ctx = document.getElementById(canvasId).getContext('2d');
            return new Chart(ctx, {
                type: 'line',
                data: {
                    labels: data.map(d => d.date),
                    datasets: [
                        {
                            label: 'Total',
                            data: data.map(d => d.count),
                            borderColor: color,
                            backgroundColor: color + '15',
                            fill: true,
                            tension: 0.3,
                            pointRadius: 2,
                            pointHoverRadius: 5,
                            borderWidth: 2
                        },
                        {
                            label: 'Unique',
                            data: data.map(d => d.uniques),
                            borderColor: '#8b949e',
                            backgroundColor: 'transparent',
                            fill: false,
                            tension: 0.3,
                            pointRadius: 2,
                            pointHoverRadius: 5,
                            borderWidth: 1.5,
                            borderDash: [5, 5]
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: { mode: 'index', intersect: false },
                    plugins: {
                        legend: {
                            labels: { color: '#c9d1d9', usePointStyle: true, boxWidth: 8 }
                        }
                    },
                    scales: {
                        x: {
                            grid: { color: '#21262d' },
                            ticks: { color: '#8b949e', maxRotation: 45, maxTicksLimit: 8 }
                        },
                        y: {
                            grid: { color: '#21262d' },
                            ticks: { color: '#8b949e' },
                            beginAtZero: true
                        }
                    }
                }
            });
        }
        
        function aggregateReferrers(period) {
            const today = new Date();
            let cutoff = new Date(0);
            if (period === 'month') cutoff = new Date(today - 30 * 86400000);
            if (period === 'year') cutoff = new Date(today - 365 * 86400000);
            
            const filtered = referrersRaw.filter(r => new Date(r.date) >= cutoff);
            const grouped = {};
            filtered.forEach(r => {
                if (!grouped[r.referrer]) grouped[r.referrer] = { count: 0, uniques: 0 };
                grouped[r.referrer].count += r.count;
                grouped[r.referrer].uniques += r.uniques;
            });
            
            const sorted = Object.entries(grouped)
                .map(([name, vals]) => ({ name, ...vals }))
                .sort((a, b) => b.count - a.count)
                .slice(0, 8);
            
            return sorted;
        }
        
        function createReferrersChart(period) {
            const data = aggregateReferrers(period);
            const colors = ['#58a6ff', '#3fb950', '#a371f7', '#f0883e', '#f85149', '#79c0ff', '#56d364', '#d2a8ff'];
            
            const ctx = document.getElementById('referrersChart').getContext('2d');
            
            if (charts.referrers) charts.referrers.destroy();
            
            charts.referrers = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: data.map(d => d.name),
                    datasets: [{
                        label: 'Views',
                        data: data.map(d => d.count),
                        borderColor: '#58a6ff',
                        backgroundColor: 'rgba(88, 166, 255, 0.08)',
                        fill: true,
                        tension: 0.4,
                        pointRadius: 4,
                        pointHoverRadius: 8,
                        pointBackgroundColor: colors,
                        pointBorderColor: colors,
                        borderWidth: 2.5
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            callbacks: {
                                label: function(ctx) {
                                    const d = data[ctx.dataIndex];
                                    return d.count + ' views · ' + d.uniques + ' unique';
                                }
                            }
                        }
                    },
                    scales: {
                        x: {
                            grid: { display: false },
                            ticks: { color: '#c9d1d9', font: { size: 11 } }
                        },
                        y: {
                            grid: { color: '#21262d' },
                            ticks: { color: '#8b949e' },
                            beginAtZero: true
                        }
                    }
                }
            });
        }
        
        function switchPeriod(chartName, period) {
            document.querySelectorAll('.period-tabs[data-chart="' + chartName + '"] button').forEach(btn => {
                btn.classList.toggle('active', btn.textContent.toLowerCase().includes(period === 'all' ? 'all' : period === 'month' ? 'month' : 'year'));
            });
            
            if (chartName === 'views') {
                const data = viewsData[period];
                charts.views.data.labels = data.map(d => d.date);
                charts.views.data.datasets[0].data = data.map(d => d.count);
                charts.views.data.datasets[1].data = data.map(d => d.uniques);
                charts.views.update();
            } else if (chartName === 'clones') {
                const data = clonesData[period];
                charts.clones.data.labels = data.map(d => d.date);
                charts.clones.data.datasets[0].data = data.map(d => d.count);
                charts.clones.data.datasets[1].data = data.map(d => d.uniques);
                charts.clones.update();
            } else if (chartName === 'referrers') {
                createReferrersChart(period);
            }
        }
        
        charts.views = createLineChart('viewsChart', viewsData.month, 'Views', '#58a6ff');
        charts.clones = createLineChart('clonesChart', clonesData.month, 'Clones', '#3fb950');
        createReferrersChart('month');
    </script>
</body>
</html>
"""

def get_db_data():
    if not DB_PATH.exists():
        return {}
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    data = {}
    c.execute("SELECT * FROM traffic_views WHERE repo = ? ORDER BY date", (REPO,))
    data["views"] = [dict(r) for r in c.fetchall()]
    c.execute("SELECT * FROM traffic_clones WHERE repo = ? ORDER BY date", (REPO,))
    data["clones"] = [dict(r) for r in c.fetchall()]
    c.execute("SELECT * FROM referrers WHERE repo = ? ORDER BY date", (REPO,))
    data["referrers"] = [dict(r) for r in c.fetchall()]
    c.execute("SELECT stars, forks FROM repo_info WHERE repo = ? ORDER BY date DESC LIMIT 1", (REPO,))
    row = c.fetchone()
    data["stars"] = row["stars"] if row else 0
    data["forks"] = row["forks"] if row else 0
    conn.close()
    return data

def filter_by_period(rows, period):
    if not rows:
        return rows
    today = datetime.now()
    if period == "month":
        cutoff = today - timedelta(days=30)
    elif period == "year":
        cutoff = today - timedelta(days=365)
    else:
        return rows
    return [r for r in rows if datetime.strptime(r["date"], "%Y-%m-%d") >= cutoff]

def main():
    print("Generating dashboard...")
    data = get_db_data()
    
    views_month = filter_by_period(data.get("views", []), "month")
    views_year = filter_by_period(data.get("views", []), "year")
    views_all = data.get("views", [])
    
    clones_month = filter_by_period(data.get("clones", []), "month")
    clones_year = filter_by_period(data.get("clones", []), "year")
    clones_all = data.get("clones", [])
    
    referrers_raw = data.get("referrers", [])
    
    views_json = json.dumps({
        "month": [{"date": r["date"], "count": r["count"], "uniques": r["uniques"]} for r in views_month],
        "year": [{"date": r["date"], "count": r["count"], "uniques": r["uniques"]} for r in views_year],
        "all": [{"date": r["date"], "count": r["count"], "uniques": r["uniques"]} for r in views_all]
    })
    
    clones_json = json.dumps({
        "month": [{"date": r["date"], "count": r["count"], "uniques": r["uniques"]} for r in clones_month],
        "year": [{"date": r["date"], "count": r["count"], "uniques": r["uniques"]} for r in clones_year],
        "all": [{"date": r["date"], "count": r["count"], "uniques": r["uniques"]} for r in clones_all]
    })
    
    referrers_json = json.dumps(referrers_raw)
    
    html = HTML_TEMPLATE.format(
        repo=REPO,
        stars=data.get("stars", 0),
        forks=data.get("forks", 0),
        update_time=datetime.now().strftime("%Y-%m-%d %H:%M"),
        views_json=views_json,
        clones_json=clones_json,
        referrers_json=referrers_json
    )
    
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Saved: {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
