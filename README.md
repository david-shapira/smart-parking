# 🚗 Smart Parking Tracker

![CI/CD](https://github.com/david-shapira/smart-parking/actions/workflows/ci.yml/badge.svg)

מערכת מיקרו-סרביסים לניהול כניסת רכבים לחניון חכם.
מצלמת IoT מפענחת מספר רישוי ושולחת אותו ב-HTTP POST ל-API. לוח הבקרה של השומר מתשאל את ה-API כל 2 שניות ומעדכן את המסך בלי לרענן את העמוד.

## ארכיטקטורה

```
  ┌──────────────┐  POST /api/cars
  │  IoT Camera  │──────────────────┐
  │ (simulator)  │                  │
  └──────────────┘                  ▼
                              ┌───────────┐      ┌─────────────┐
  ┌──────────┐  :8080  ┌─────►│  API      │─────►│  Redis      │
  │ Browser  │────────►│ Nginx│  (Flask)  │      │  AOF + RDB  │
  │ (guard)  │◄────────│  web │  :5000    │      └──────┬──────┘
  └──────────┘  HTML + └──────┴───────────┘             │
                /api/* proxy                    volume: redis-data
```

| שירות   | טכנולוגיה           | תפקיד |
|---------|---------------------|-------|
| `web`   | Nginx 1.27          | מגיש את `index.html` ומעביר (reverse proxy) את `/api/*` לשירות ה-API |
| `api`   | Python 3.12 + Flask + Gunicorn | REST API: קבלת נתונים מהמצלמה ומשיכת נתונים ללוח הבקרה |
| `redis` | Redis 7             | מסד הנתונים. נשמר לדיסק עם AOF ו-RDB ב-named volume |
| `camera`| Python (stdlib)     | סימולטור מצלמה שעולה רק עם `--profile demo` |

כל השירותים רצים על רשת ה-Compose ומוצאים זה את זה לפי שם השירות (DNS פנימי של Docker). רק פורט 8080 של Nginx חשוף למחשב המארח.

## הרצה

```bash
git clone https://github.com/<owner>/<repo>.git
cd <repo>

docker compose up -d --build                  # בלי המצלמה
docker compose --profile demo up -d --build   # עם סימולטור המצלמה
```

לוח הבקרה: **http://localhost:8080**

```bash
docker compose ps                      # סטטוס + healthchecks
docker compose logs -f camera          # לראות את המצלמה שולחת
docker compose --profile demo down     # עצירה (הנתונים נשמרים)
docker compose --profile demo down -v  # עצירה + מחיקת ה-volume
```

## API

| Method | Endpoint | Body | תשובה |
|--------|----------|------|-------|
| `POST` | `/api/cars` | `{"plate": "12-345-67"}` | `201` נוסף · `400` מספר לא תקין · `409` כבר בפנים או שהחניון מלא |
| `POST` | `/api/cars/<plate>/exit` | – | `200` יצא · `404` לא נמצא בחניון |
| `GET`  | `/api/cars` | – | `count`, `capacity`, `total_entries`, `cars[]`, `recent_events[]` |
| `GET`  | `/api/health` | – | `200` אם Redis עונה, אחרת `503` |

מספר רישוי תקין הוא 7 או 8 ספרות. מקפים ורווחים מוסרים לפני הבדיקה.

```bash
curl -X POST http://localhost:8080/api/cars -H "Content-Type: application/json" -d '{"plate":"12-345-67"}'
curl http://localhost:8080/api/cars
```

### מבנה הנתונים ב-Redis

| Key | Type | תוכן |
|-----|------|------|
| `parking:inside` | HASH | מספר רישוי → זמן כניסה (רכבים שנמצאים בחניון כרגע) |
| `parking:log` | LIST | אירועי כניסה ויציאה ב-JSON, החדש ראשון (100 אחרונים) |
| `parking:total_entries` | STRING | מונה כל הכניסות |

כפילויות נמנעות עם `HSETNX`, שהיא פעולה אטומית: היא כותבת רק אם השדה עוד לא קיים.

## Data Persistence

Redis רץ עם `--appendonly yes`, כלומר כל כתיבה נרשמת לקובץ AOF. בנוסף הוא רץ עם `--save 60 1` ושומר snapshot כל דקה. שני הקבצים נשמרים ב-`/data`, שממופה ל-named volume `redis-data`.

בדיקה שהנתונים שורדים נפילה:
```bash
docker compose up -d
curl -X POST localhost:8080/api/cars -H "Content-Type: application/json" -d '{"plate":"7777777"}'
docker compose down          # מוחק את הקונטיינרים
docker compose up -d         # יוצר אותם מחדש
curl localhost:8080/api/cars # 7777777 עדיין שם
```

## CI/CD – GitHub Actions

`.github/workflows/ci.yml`:

1. **build-and-test** רץ על כל push ו-pull request:
   - `docker compose build` לכל האימג'ים
   - `docker compose up` ובדיקת smoke: health, POST, GET, ושמספר לא תקין מחזיר 400
   - הדפסת לוגים אם משהו נכשל, ו-`down -v` בסוף
2. **publish (בונוס)** רץ רק על push ל-`main` ורק אם השלב הקודם עבר. הוא דוחף את שלושת האימג'ים ל-GitHub Container Registry:
   `ghcr.io/<owner>/smart-parking-{api,web,camera}:latest` ו-`:<commit-sha>`

## מבנה הפרויקט

```
.
├── docker-compose.yml
├── api/            # Flask API + Dockerfile
├── web/            # index.html (JS dashboard) + nginx.conf + Dockerfile
├── camera/         # IoT camera simulator + Dockerfile
└── .github/workflows/ci.yml
```

## צוות

| שם | אחריות |
|----|--------|
| David | ContainersEngineer |
| Jonathan Moshe Cohen Ambalu | HTML EXPERT |
