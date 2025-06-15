# Embedding Vizro Dashboards in FastAPI

This document walks through the changes needed to mount your Vizro-generated dashboards as ASGI apps under FastAPI, so that your `<iframe>` in `dashboard_iframe.html` actually renders the interactive Plotly/Dash charts.

---

## 1. Install & import dependencies

Make sure you have these in your `requirements.txt` / virtualenv:

```text
fastapi
uvicorn
vizro
pandas
plotly
```

In backend/main.py, add:

```python
from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from vizro import Vizro
# … your existing imports …
```

Initialize your app and templates:

```python
app = FastAPI(...)
templates = Jinja2Templates(directory="templates")
# static & CORS as before…
app.mount("/static", StaticFiles(directory=static_dir), name="static")
```

## 2. Store & mount each dashboard ASGI app

In your POST /generate handler (in main.py), after you build the dashboard object, do:

```python
@app.post("/generate")
async def generate(request: Request):
    data = await request.json()
    dashboard_id = uuid.uuid4().hex
    # … your existing create_dashboard_from_config() call …
    result = create_dashboard_from_config(data, dashboard_id)
    if not result["success"]:
        raise HTTPException(500, result["error"])
    # Reset Vizro's global state and rebuild the ASGI app
    vizro_app = Vizro()._reset().build(result["dashboard"])
    # Mount it under /vizro/{dashboard_id}
    app.mount(f"/vizro/{dashboard_id}", vizro_app.server, name=dashboard_id)
    return {"id": dashboard_id}
```

Vizro()._reset() clears any leftover Plotly model IDs.
app.mount(...) exposes the Dash server at /vizro/{dashboard_id}/.

## 3. Update the "view" endpoint to point the iframe

Replace your existing /dashboard/{dashboard_id} endpoint with:

```python
@app.get("/dashboard/{dashboard_id}", response_class=HTMLResponse)
async def view_dashboard(request: Request, dashboard_id: str):
    dash_url = f"/vizro/{dashboard_id}/"
    return templates.TemplateResponse(
        "dashboard_iframe.html",
        {
            "request": request,
            "title": "Interactive Dashboard",
            "dashboard_id": dashboard_id,
            "dash_url": dash_url
        }
    )
```

This passes the correct dash_url into your Jinja template.

## 4. Adjust dashboard_iframe.html

Ensure your templates/dashboard_iframe.html contains an `<iframe>` keyed off dash_url:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{{ title }}</title>
  <link href="https://cdn.tailwindcss.com" rel="stylesheet">
</head>
<body>
  <header>
    <h1>{{ title }}</h1>
    <p>ID: {{ dashboard_id }}</p>
    <a href="/api/dashboard/{{ dashboard_id }}/data?download=true">Download CSV</a>
  </header>
  <iframe
    src="{{ dash_url }}"
    style="width:100%; height:calc(100vh - 80px); border:none;"
    title="Vizro Dashboard">
  </iframe>
</body>
</html>
```

The src will now hit the real Dash app you mounted.

## 5. Remove legacy launcher (run_server.py)

Since you're now mounting Vizro's ASGI server directly, you can delete any separate run_server.py or subprocess-based code.

## 6. Testing

Start your server

```bash
uvicorn backend.main:app --reload
```

Generate a dashboard

Upload your CSV in /static/index.html → POST /generate → get back { "id": "..." }.

View the iframe

Navigate to /dashboard/{id} → you should see your full interactive dashboard inside the iframe.

## Summary

Generate: build & persist dashboard model + data, then
app.mount("/vizro/{id}", Vizro()._reset().build(...).server)

View: render a Jinja template with `<iframe src="/vizro/{id}/">`.

No more subprocesses—everything runs in the same ASGI process.