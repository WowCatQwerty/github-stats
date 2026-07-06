# 📊 GitHub Stats Tracker

Автоматический сборщик статистики GitHub-репозиториев с дашбордом на GitHub Pages.

## Что отслеживается

| Метрика | Описание | Источник |
|---------|----------|----------|
| ⭐ Stars | Всего звёздочек | GitHub API |
| 🍴 Forks | Всего форков | GitHub API |
| 👁 Views | Просмотры страницы репозитория | GitHub Traffic API (14 дней) |
| 📥 Clones | Клонирования репозитория | GitHub Traffic API (14 дней) |
| 🔗 Referring Sites | Источники трафика | GitHub Traffic API (14 дней) |

**Важно:** Views, Clones и Referrers GitHub хранит только 14 дней. Скрипт собирает их каждые 7 дней и сохраняет в SQLite — так данные накапливаются за всё время.

## Дашборд

- **Stars** — просто цифра "всего"
- **Views и Clones** — графики с переключателем Month / Year / All + сумма за период
- **Referring Sites** — линейный график с переключателем периода

## Настройка

### 1. Создай репозиторий

Новый публичный репозиторий на GitHub (например, `github-stats`).

### 2. Скопируй файлы

Загрузи в репозиторий:
- `collect_stats.py`
- `generate_dashboard.py`
- `.github/workflows/collect-stats.yml`
- Создай папки `data/` и `docs/` (через создание файла `.gitkeep` внутри)

### 3. Создай PAT (Personal Access Token)

Для сбора трафика нужен токен с правами `repo`:

1. GitHub → **Settings** → **Developer settings** → **Personal access tokens** → **Tokens (classic)**
2. **Generate new token**
3. Имя: `github-stats`
4. Scopes: **`repo`** (вся секция) + **`read:user`**
5. **Generate** → скопируй токен

### 4. Добавь токен в Secrets

В репозитории `github-stats`:
- **Settings** → **Secrets and variables** → **Actions** → **New repository secret**
- Name: `GH_PAT`
- Secret: вставь скопированный токен

### 5. Настрой GitHub Pages

- **Settings** → **Pages**
- Source: **Deploy from a branch**
- Branch: **`gh-pages`** → **`/(root)`**
- Save

### 6. Запусти

**Actions** → **Collect GitHub Stats** → **Run workflow**

Через пару минут дашборд будет доступен по адресу:
```
https://YOUR_USERNAME.github.io/github-stats/
```

## Как это работает

```
GitHub Actions (раз в 7 дн)
        │
        ▼
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│ collect_stats │────▶│   SQLite DB   │────▶│   generate_   │
│   .py         │     │  data/stats.db│     │  dashboard.py │
└───────────────┘     └───────────────┘     └───────────────┘
                                                    │
                                                    ▼
                                            ┌───────────────┐
                                            │ docs/index.html│
                                            └───────────────┘
                                                    │
                                                    ▼
                                            ┌───────────────┐
                                            │  gh-pages     │
                                            │  (GitHub Pages)│
                                            └───────────────┘
```

## Структура

```
.
├── .github/workflows/
│   └── collect-stats.yml    # Workflow (раз в 7 дней)
├── data/
│   └── stats.db             # SQLite база (коммитится)
├── docs/
│   └── index.html           # Дашборд (генерируется)
├── collect_stats.py         # Сбор данных
├── generate_dashboard.py    # Генерация HTML
└── README.md
```

## Добавление репозиториев

В настройках Actions переменная `REPOS`:
```
REPOS = owner/repo1,owner/repo2
```

По умолчанию: `WowCatQwerty/vps-net-stat`

## Периодичность

Раз в 7 дней (воскресенье в 3:00 UTC). Можно изменить в workflow:
```yaml
schedule:
  - cron: '0 3 * * 0'   # Каждое воскресенье
```
