# Backend Refactoring Guide

## Eliminate `run_dashboard.py` & subprocess logic
- Remove all references to launching dashboards in a separate process.
- Collapse your `/generate` handler so it simply constructs and stores a `vm.Dashboard` object in memory.

## Return dashboard metadata, not a URL
- Have `POST /generate` return `{ id, success: true }` only.
- Frontend will then navigate to `/dashboard/{id}`.

## Build the Vizro (Dash) app in-process
- In your `/dashboard/{id}` endpoint, retrieve the `vm.Dashboard` from memory.
- Call `app = Vizro().build(dashboard)` to get the underlying Dash/Flask app instance.

## Mount the Dash app on a dynamic sub-path
- Use Starlette's `WSGIMiddleware` (from `starlette.middleware.wsgi`) to mount the Dash app at `/dash/{id}`:

```python
from starlette.middleware.wsgi import WSGIMiddleware
app.mount(f"/dash/{dashboard_id}", WSGIMiddleware(app.server))
```

- This avoids port conflicts and runs entirely under your FastAPI/Uvicorn process.

## Serve a simple wrapper page
- In `GET /dashboard/{id}`, render a minimal HTML template (e.g. Jinja2) that embeds the Dash app via an `<iframe src="/dash/{id}">`.
- No custom Plotly-JS or manual fetch-and-plot code needed.

## Clean up your JS
- Point your front-end's "View Dashboard" link to `/dashboard/{id}`.
- Drop any `fetch('/api/.../chart')` logic—Dash will handle all rendering.

## Ensure static assets are served
- Make sure your FastAPI `StaticFiles` mount includes any assets Dash needs (e.g. `/assets/`, `/static/`).