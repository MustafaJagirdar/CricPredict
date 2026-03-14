# Deploying CricPredict to Render

## 1. Push to GitHub

```bash
git init
git branch -M main
git add .
git commit -m "Prepare CricPredict for deployment"
git remote add origin https://github.com/YOUR_USERNAME/cricpredict.git
git push -u origin main
```

## 2. Create the Render deployment

1. Sign in to [Render](https://render.com/).
2. Click `New +`.
3. Choose `Blueprint`.
4. Select your GitHub repository.
5. Render will read [render.yaml](/Users/mustafa/Documents/PAPC/render.yaml).

## 3. Environment variables

Render will generate:

- `DJANGO_SECRET_KEY`
- `DATABASE_URL`

Optional:

- `CRICKETDATA_API_KEY` for live upcoming match data

## 4. Build and start

Render will run:

```bash
./build.sh
gunicorn cricket_project.wsgi:application
```

`build.sh` installs dependencies, collects static files, and runs migrations.

## 5. Important deployment note

Local development uses SQLite, but Render should use PostgreSQL via `DATABASE_URL`. That is already supported in [backend/settings.py](/Users/mustafa/Documents/PAPC/backend/settings.py).
