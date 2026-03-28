---
description: How to deploy the KBSteel ERP to Railway.app
---

# Railway Deployment Workflow

Follow these steps to deploy the application to production on [Railway.app](https://railway.app).

## 1. Prepare GitHub Repository
1. Ensure all changes are committed and pushed to your GitHub repository.
2. The root folder must contain: `Procfile`, `railway.json`, `requirements.txt`, and the `backend_core` and `kumar_frontend` folders.

## 2. Create Railway Project
1. Log in to [Railway.app](https://railway.app).
2. Click **"New Project"**.
3. Select **"Deploy from GitHub repo"** and choose your repository.

## 3. Add Database
1. Inside your Railway project, click **"Add Service"** (or use the `Cmd+K` / `Ctrl+K` menu).
2. Select **"Database"** -> **"Add PostgreSQL"**.
3. Railway will automatically provision a database.

## 4. Configure Environment Variables
Go to the **"Variables"** tab of your **Backend/Web Service** in Railway and add the following:

| Variable | Value / Source |
| :--- | :--- |
| `DATABASE_URL` | Already provided by the Postgres service (Check "Reference variables") |
| `KUMAR_SECRET_KEY` | Generate a random 64-char string (e.g., `python -c "import secrets; print(secrets.token_urlsafe(64))"`) |
| `ENVIRONMENT` | `production` |
| `CORS_ORIGINS` | `https://kumarbrothersbksc.in,https://www.kumarbrothersbksc.in` |
| `TOKEN_EXPIRE_MINUTES` | `1440` |

## 5. Domain Setup
1. Go to the **"Settings"** tab of your Web Service.
2. Scroll to the **"Domains"** section.
3. Click **"Custom Domain"** and enter `kumarbrothersbksc.in`.
4. Follow the CNAME instructions provided by Railway to update your DNS settings (at your domain registrar, e.g., GoDaddy/NameCheap).

## 6. Verify Deployment
1. Once the build finishes, visit `https://kumarbrothersbksc.in`.
2. The initial admin login will use the "Boss" user. (Reset the password if prompted).
