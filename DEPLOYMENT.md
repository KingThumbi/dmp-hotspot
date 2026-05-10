# Deployment Notes

## Render Backend Build

The Flask backend serves React admin deep links from `frontend/dist`:

- `/admin-ui`
- `/admin-ui/<path>`
- `/assets/<path>`
- `/logo.png`
- `/vite.svg`

Because `frontend/dist` is intentionally gitignored, the backend Render service must build the frontend during deploy before Gunicorn starts.

Set the backend Render **Build Command** to:

```bash
./scripts/render_build.sh
```

Keep the backend **Start Command** as:

```bash
flask --app wsgi:app db upgrade && gunicorn wsgi:app --bind 0.0.0.0:$PORT
```

Do not build the frontend in the start command. The start command should stay focused on database upgrade and starting the web process.

## Canonical Admin Host

If the backend Render hostname is reachable publicly, enable the browser-admin canonical redirect so admin sessions are created on the public domain instead of the Render service domain.

Set these environment variables on the backend Render service:

```bash
ENABLE_CANONICAL_ADMIN_REDIRECT=true
CANONICAL_ADMIN_HOST=www.dmpolinconnect.co.ke
CANONICAL_ADMIN_REDIRECT_FROM_HOSTS=dmp-hotspot.onrender.com
```

This redirect only applies to browser admin routes (`/admin/*` and `/admin-ui/*`). It does not redirect `/api/*`, `/health`, `/mpesa/*`, or built static assets.
