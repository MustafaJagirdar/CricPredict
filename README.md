# CricPredict

CricPredict is a Django-based cricket analytics web app that shows:

- Top 15 predicted batters
- Top 15 predicted bowlers
- Upcoming match insights
- Recommended players for the next match

## Local Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000)

## Optional API

To fetch a live upcoming fixture instead of using the built-in fallback, set:

```bash
export CRICKETDATA_API_KEY=your_api_key
```

## GitHub Upload

This folder is not a Git repository yet, so initialize it first:

```bash
git init
git branch -M main
git add .
git commit -m "Initial CricPredict commit"
```

Then create an empty GitHub repository and connect it:

```bash
git remote add origin https://github.com/YOUR_USERNAME/cricpredict.git
git push -u origin main
```

## Render Deployment

This repo already includes:

- [render.yaml](/Users/mustafa/Documents/PAPC/render.yaml)
- [build.sh](/Users/mustafa/Documents/PAPC/build.sh)

### Recommended setup

1. Push the project to GitHub.
2. Open [Render](https://render.com/).
3. Click `New +`.
4. Choose `Blueprint` for `render.yaml` based deployment.
5. Connect your GitHub repository.
6. Render will create:
   - a web service
   - a PostgreSQL database
7. In the web service environment variables, add:
   - `CRICKETDATA_API_KEY` if you want live fixture data
8. Deploy.

### What Render uses

- Build command: `./build.sh`
- Start command: `gunicorn cricket_project.wsgi:application`
- Database: PostgreSQL through `DATABASE_URL`

## Notes

- Local development uses SQLite by default.
- Render should use PostgreSQL automatically through `DATABASE_URL`.
- Existing local `db.sqlite3` is ignored in Git through [.gitignore](/Users/mustafa/Documents/PAPC/.gitignore).
