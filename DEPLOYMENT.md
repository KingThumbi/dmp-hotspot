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
