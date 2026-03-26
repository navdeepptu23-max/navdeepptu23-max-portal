# Fresh Portal (Flask)

Minimal starter portal with:
- User registration
- User login/logout
- Simple authenticated dashboard

## Quick start

1. Create and activate a virtual environment.
2. Install dependencies:
   pip install -r requirements.txt
3. Run:
   python app.py
4. Open:
   http://127.0.0.1:5000

## Deploy on Render (public URL)

1. Push the `fresh_portal` folder to a GitHub repository.
2. In Render, create a new `Web Service` from that repository.
3. Set the root directory to `fresh_portal`.
4. Build command:
   pip install -r requirements.txt
5. Start command:
   gunicorn app:app
6. Add environment variable:
   `SECRET_KEY` = a strong random string
7. Optional but recommended: attach a PostgreSQL database and set `DATABASE_URL`.

Your public URL will look like:
`https://<your-service-name>.onrender.com`

## Deploy on Google Cloud Run (free tier)

Cloud Run has an always-free tier (within monthly limits). You still need a Google Cloud project with billing enabled.

1. Install and login to Google Cloud CLI.
2. Create/select a project and enable APIs:
   gcloud config set project YOUR_PROJECT_ID
   gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com
3. Deploy from this folder:
   gcloud run deploy fresh-portal \
     --source . \
     --region us-central1 \
     --allow-unauthenticated \
     --set-env-vars SECRET_KEY=YOUR_STRONG_SECRET

After deployment, Cloud Run prints your live HTTPS URL.

Notes:
- `Dockerfile` is included, so Cloud Run can build and run this app directly.
- If you need persistent production data, use Cloud SQL PostgreSQL and set `DATABASE_URL`.
- If you stay on SQLite, data may reset when instances restart.

## Notes

- Uses SQLite database file: `portal.db` in this folder.
- Secret key can be overridden with environment variable `SECRET_KEY`.
- `DATABASE_URL` is supported for hosted deployments.
