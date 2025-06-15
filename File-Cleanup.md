## 1. `dashboard_export.html`

### What's working
* Uses a clean Bootstrap layout and a Jinja loop over `charts`
* Provides a "Sample Data" table and footer attribution
* Separates concerns via CSS classes (`.dashboard-container`, `.chart-container`, etc.)

### Pain points & cleanup
1. **Missing responsive meta tag** Add `<meta name="viewport" content="width=device-width, initial-scale=1">` so mobile/tablet exports size correctly.
2. **Inconsistent Bootstrap versions** You're loading 5.3.0-alpha1 here but 5.1.3 in `error.html`. Pick one stable version (e.g. 5.2.x) and load it from your own `static/` folder or a single CDN link.
3. **Placeholder‐only charts** Currently you show an SVG "placeholder" rather than the actual chart. If you want true exports, consider:
   * Generating static PNG/SVG via Plotly's `figure.to_image()` in your `/export` endpoint
   * Passing `chart.image_base64` into the template and rendering `<img src="data:image/png;base64,{{ chart.image_base64 }}">`
4. **Nested **`<div>` cleanup You have three nested wrappers just to center the SVG and caption:

```html
<div class="chart-placeholder"> <div> <div class="text-center">…SVG…</div> <div class="mt-2">{{ chart.type }} Chart</div> </div> </div>
```

You can collapse to:

```html
<div class="chart-placeholder text-center"> …SVG… <div class="mt-2">{{ chart.title or chart.type|capitalize }} Chart</div> </div>
```

5. **Print‐specific CSS** You use `page-break-inside: avoid;`, which is great—but if you're not printing/exporting to PDF, it's dead weight. Scope it inside a `@media print { … }` block.
6. **Unnecessary "data-table" heading** If you only need a few rows for context, you might limit the DataFrame preview to 5–10 rows, or omit it altogether in export mode and let clients download the CSV instead.

### Integration sanity check
* Ensure your FastAPI export route actually renders this template:

```python
@app.get("/export/{dashboard_id}") def export_dashboard(dashboard_id: str, request: Request): dashboard = get_dashboard(dashboard_id) charts = [ {"type": c.id, "title": c.figure.layout.title, "image_base64": to_base64(c.figure)} for c in dashboard.pages[0].components ] sample = dashboard_utils.get_sample_table(dashboard_id) return templates.TemplateResponse("dashboard_export.html", { "request": request, "title": dashboard.title, "dashboard_id": dashboard_id, "timestamp": datetime.utcnow().isoformat(), "charts": charts, "sample_data": sample.to_html(classes="table table-sm", index=False) })
```

This ensures you're not stuck with placeholders.

## 2. `error.html`

### What's working
* Clean, centered Bootstrap card
* Shows `{{ error_message }}` and offers a "Go to Homepage" button

### Pain points & cleanup
1. **Missing viewport meta** Again, add `<meta name="viewport" content="width=device-width, initial-scale=1">`.
2. **Duplicate font stacks & CSS** Both templates are loading very similar `body { font-family: … }` rules. You could factor those into a shared `static/css/base.css`.
3. **Mixing Bootstrap versions** Unify to the same version as export template.
4. **Hard-coded "Error" title** If you ever internationalize or want different error severities, you might pass `error_title` as well.
5. **No fallback link** If your root path ever changes (e.g. serves under `/app/`), the hard-coded `<a href="/">` might break. Consider `url_for("index")` in TemplateResponse.

## Summary of Recommendations
1. **Unify & extern**
   * One Bootstrap version
   * Shared base CSS for fonts, margins, utility classes
2. **Actual chart embedding**
   * In your export endpoint, render real Plotly images instead of placeholders.
   * Pass base64 image strings or URLs to the template.
3. **Trim redundant wrappers & CSS**
   * Collapse nested `<div>`s
   * Scope print styles inside `@media print`
4. **Improve responsiveness & maintainability**
   * Add `<meta name="viewport">`
   * Use `url_for` for links
   * Factor shared styles into static files