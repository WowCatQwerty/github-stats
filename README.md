# 📊 GitHub Stats Tracker

Автоматический сборщик статистики GitHub-репозиториев с красивым дашбордом на GitHub Pages.

## Что отслеживается

| Метрика | Описание | Источник |
|---------|----------|----------|
| ⭐ Stars Over Time | Накопительный рост звёздочек | GitHub API |
| 👁 Repo Views | Просмотры страницы репозитория | GitHub Traffic API (14 дней) |
| 📥 Repo Clones | Клонирования репозитория | GitHub Traffic API (14 дней) |
| 🔗 Referring Sites | Источники трафика | GitHub Traffic API (14 дней) |
| 📄 Popular Content | Самые посещаемые страницы | GitHub Traffic API (14 дней) |
| 💻 Code Activity | Добавления/удаления строк | GitHub API |
| 🐛 Issues | Открытые/закрытые issues | GitHub API |

**Важно:** метрики Views, Clones, Referrers и Popular Content хранятся GitHub только 14 дней. Поэтому скрипт собирает их регулярно и сохраняет в SQLite — так данные накапливаются за всё время.

## Быстрый старт

### 1. Создай репозиторий

Создай новый публичный репозиторий на GitHub (например, `github-stats`).

### 2. Скопируй файлы

Скопируй всё содержимое этого репозитория в свой.

### 3. Настрой GitHub Pages

В настройках репозитория → **Pages** → Source: **GitHub Actions**.

### 4. Настрой переменные (опционально)

В настройках репозитория → **Settings → Secrets and variables → Actions → Variables** добавь:

- `REPOS` — список репозиториев через запятую, например: `WowCatQwerty/vps-net-stat,WowCatQwerty/another-repo`

По умолчанию отслеживается `WowCatQwerty/vps-net-stat`.

### 5. Запусти вручную

Перейди в **Actions** → выбери workflow **"Collect GitHub Stats"** → **Run workflow**.

Через пару минут дашборд будет доступен по адресу:
```
https://YOUR_USERNAME.github.io/github-stats/
```

## Как это работает

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  GitHub Actions │────▶│  Python скрипт  │────▶│   SQLite DB     │
│  (раз в 14 дн)  │     │  (collect_stats)│     │  (data/stats.db)│
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                            │
                                                            ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  GitHub Pages   │◀────│  HTML дашборд   │◀────│  generate_      │
│  (ваш сайт)     │     │  (docs/index)   │     │  dashboard.py   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## Структура проекта

```
.
├── .github/workflows/
│   └── collect-stats.yml    # GitHub Actions workflow
├── data/
│   └── stats.db             # SQLite база данных (коммитится)
├── docs/
│   └── index.html           # Генерируемый дашборд
├── collect_stats.py         # Сбор данных
├── generate_dashboard.py    # Генерация HTML
└── README.md
```

## Добавление новых репозиториев

Просто обнови переменную `REPOS` в настройках Actions:
```
REPOS = owner/repo1,owner/repo2,owner/repo3
```

Следующий запуск соберёт данные для всех репозиториев.

## Кастомизация

- **Цвета и стиль** — редактируй `generate_dashboard.py`, секция `<style>`
- **Дополнительные метрики** — добавь в `collect_stats.py` новые API-эндпоинты
- **Периодичность** — измени `cron` в workflow (сейчас раз в 14 дней)

## Лимиты API

- GitHub Actions: 2000 минут/месяц (бесплатно)
- GitHub API: 5000 запросов/час (с `GITHUB_TOKEN`)
- Скрипт делает ~10 запросов на репозиторий за запуск

## Лицензия

MIT
