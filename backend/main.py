import os
import uuid
import json
import logging
from pathlib import Path
from typing import List

from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from a2wsgi import WSGIMiddleware
from pydantic import BaseModel

from . import dashboard_utils
from vizro import Vizro

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Logger for this module
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Vizro Dashboard Builder",
    description="Create beautiful data visualizations with Vizro and Plotly",
    version="1.0.0"
)

# Configure CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create directories for dashboards
DASHBOARD_FOLDER = dashboard_utils.DASHBOARD_FOLDER

# Set up static files and templates
BASE_DIR = Path(__file__).resolve().parent
static_dir = BASE_DIR / "static"
templates_dir = BASE_DIR / "templates"
assets_dir = BASE_DIR / "assets"

# Create directories if they don't exist
static_dir.mkdir(exist_ok=True)
templates_dir.mkdir(exist_ok=True)
assets_dir.mkdir(exist_ok=True)

# Mount static files and set up templates
app.mount("/static", StaticFiles(directory=static_dir), name="static")
app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
templates = Jinja2Templates(directory=templates_dir)

# Pydantic models for request validation
class ChartConfig(BaseModel):
    type: str

class DashboardRequest(BaseModel):
    charts: List[str]
    layout: str = "grid"
    columns: int = 2
    data: str

def mount_existing_dashboards():
    """Mount all existing dashboards as ASGI apps on startup"""
    try:
        dashboard_folder = Path(DASHBOARD_FOLDER)
        if not dashboard_folder.exists():
            print("Dashboard folder does not exist yet")
            return
            
        for dashboard_dir in dashboard_folder.iterdir():
            if dashboard_dir.is_dir():
                dashboard_id = dashboard_dir.name
                try:
                    # Try to load and mount the dashboard
                    dashboard = dashboard_utils.get_dashboard(dashboard_id)
                    if dashboard:
                        # Reset Vizro's global state and rebuild the ASGI app
                        Vizro()._reset()
                        mount_path = f"/vizro/{dashboard_id}"
                        print(f"Building Vizro app with url_base_pathname: {mount_path + '/'}")
                        vizro_app = Vizro(url_base_pathname=mount_path + "/").build(dashboard)
                        print(f"Vizro app built successfully. Checking attributes...")
                        
                        # Mount at the same path as url_base_pathname for clean URL structure
                        # FastAPI will strip the mount prefix and hand the rest to Dash
                        if hasattr(vizro_app, 'dash'):
                            dash_app = vizro_app.dash
                            # Mount at root-level path for Dash to handle subpath routing
                            mount_point = f"/vizro-{dashboard_id}"
                            print(f"Found dash attribute, mounting at {mount_point}")
                            print(f"Dash app server type: {type(dash_app.server)}")
                            print(f"Dash app config: {getattr(dash_app, 'config', 'No config attr')}")
                            app.mount(mount_point, WSGIMiddleware(dash_app.server), name=f"vizro-{dashboard_id}")
                            print(f"Successfully mounted dashboard at {mount_point}")
                        elif hasattr(vizro_app, 'server'):
                            mount_point = f"/vizro-{dashboard_id}"
                            print(f"Found server attribute, mounting at {mount_point}")
                            print(f"Server type: {type(vizro_app.server)}")
                            app.mount(mount_point, WSGIMiddleware(vizro_app.server), name=f"vizro-{dashboard_id}")
                            print(f"Successfully mounted dashboard at {mount_point}")
                        else:
                            print(f"ERROR: Cannot find server attribute for {dashboard_id}")
                            print(f"Available attributes: {dir(vizro_app)}")
                        
                        print(f"Mounted existing dashboard: {dashboard_id} at {mount_point}")
                    else:
                        print(f"Failed to load dashboard: {dashboard_id}")
                except Exception as e:
                    print(f"Error mounting dashboard {dashboard_id}: {str(e)}")
                    
    except Exception as e:
        print(f"Error mounting existing dashboards: {str(e)}")

@app.on_event("startup")
async def startup_event():
    """Mount existing dashboards on startup"""
    mount_existing_dashboards()

@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the main HTML page"""
    try:
        index_path = os.path.join(static_dir, "index.html")
        if os.path.exists(index_path):
            with open(index_path, "r") as f:
                return HTMLResponse(content=f.read())
        else:
            return HTMLResponse(content="<html><body><h1>Welcome to Vizro AI Dashboard Builder</h1><p>The frontend files are not yet installed. Please check the setup instructions.</p></body></html>")
    except Exception as e:
        return HTMLResponse(content=f"<html><body><h1>Error</h1><p>{str(e)}</p></body></html>")

@app.get("/{filename:path}.map")
async def source_maps(filename: str):
    """Handle source map requests gracefully (browser dev tools)"""
    return JSONResponse(
        status_code=404,
        content={"message": "Source map not available"}
    )

@app.post("/generate")
async def generate(request: Request):
    """Generate a new dashboard from CSV data"""
    print("=== Starting generate endpoint ===")  
    try:
        data = await request.json()
        print(f"Received data with keys: {list(data.keys())}")
        
        # Generate unique dashboard ID
        dashboard_id = uuid.uuid4().hex
        print(f"Generated dashboard ID: {dashboard_id}")
        
        # Create dashboard from the provided configuration
        print("Creating dashboard from config...")
        result = dashboard_utils.create_dashboard_from_config(data, dashboard_id)
        print(f"Dashboard creation result: {result.get('success', False)}")
        
        if not result['success']:
            raise HTTPException(status_code=500, detail=f"Error creating dashboard: {result.get('error')}")
        
        # Save dashboard config to file
        dashboard_path = Path(DASHBOARD_FOLDER) / dashboard_id
        dashboard_path.mkdir(parents=True, exist_ok=True)
        
        config_path = dashboard_path / "config.json"
        with open(config_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        # Save data to CSV file
        data_path = dashboard_path / "data.csv"
        with open(data_path, 'w') as f:
            f.write(data["data"])
        
        print("About to reset Vizro and build app...")
        # Reset Vizro's global state and rebuild the ASGI app
        Vizro()._reset()
        mount_path = f"/vizro/{dashboard_id}"
        print(f"Building Vizro app with url_base_pathname: {mount_path + '/'}")
        vizro_app = Vizro(url_base_pathname=mount_path + "/").build(result["dashboard"])
        print(f"Vizro app built successfully. Checking attributes...")
        
        # Mount at the same path as url_base_pathname for clean URL structure
        # FastAPI will strip the mount prefix and hand the rest to Dash
        if hasattr(vizro_app, 'dash'):
            dash_app = vizro_app.dash
            # Mount at root-level path for Dash to handle subpath routing
            mount_point = f"/vizro-{dashboard_id}"
            print(f"Found dash attribute, mounting at {mount_point}")
            print(f"Dash app server type: {type(dash_app.server)}")
            print(f"Dash app config: {getattr(dash_app, 'config', 'No config attr')}")
            app.mount(mount_point, WSGIMiddleware(dash_app.server), name=f"vizro-{dashboard_id}")
            print(f"Successfully mounted dashboard at {mount_point}")
        elif hasattr(vizro_app, 'server'):
            mount_point = f"/vizro-{dashboard_id}"
            print(f"Found server attribute, mounting at {mount_point}")
            print(f"Server type: {type(vizro_app.server)}")
            app.mount(mount_point, WSGIMiddleware(vizro_app.server), name=f"vizro-{dashboard_id}")
            print(f"Successfully mounted dashboard at {mount_point}")
        else:
            print(f"ERROR: Cannot find server attribute for {dashboard_id}")
            print(f"Available attributes: {dir(vizro_app)}")
        
        print(f"Dashboard {dashboard_id} process completed")
        
        return {"id": dashboard_id, "success": True}
        
    except Exception as e:
        print(f"ERROR in generate endpoint: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/test-mount")
async def test_mount():
    """Test endpoint to verify mounting behavior"""
    return {"message": "Test endpoint working", "mounted_apps": [route.path for route in app.routes if hasattr(route, 'path') and route.path.startswith('/vizro')]}

@app.get("/dashboard/{dashboard_id}", response_class=HTMLResponse)
async def view_dashboard(request: Request, dashboard_id: str):
    """Serve a dashboard by ID using an iframe wrapper around the Vizro Dash app"""
    # Iframe points to the actual dashboard path within the mounted Dash app
    dash_url = f"/vizro-{dashboard_id}/vizro/{dashboard_id}/"
    return templates.TemplateResponse(
        "dashboard_iframe.html",
        {
            "request": request,
            "title": "Interactive Dashboard",
            "dashboard_id": dashboard_id,
            "dash_url": dash_url
        }
    )

@app.get("/api/dashboard/{dashboard_id}/export")
async def dashboard_export(dashboard_id: str):
    """Generate and return an HTML version of the dashboard for download"""
    try:
        # First, get the dashboard data
        dashboard_path = Path(DASHBOARD_FOLDER) / dashboard_id
        config_path = dashboard_path / 'config.json'
        csv_path = dashboard_path / 'data.csv'
        
        if not config_path.exists():
            print(f"Dashboard config not found at {config_path}")
            return JSONResponse(
                status_code=404,
                content={"error": "Dashboard not found"}
            )
        
        # Load dashboard configuration
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            print(f"Successfully loaded config for dashboard {dashboard_id}")
        except json.JSONDecodeError as e:
            print(f"Invalid JSON in config file: {e}")
            return JSONResponse(
                status_code=500,
                content={"error": "Dashboard configuration is corrupted"}
            )
        
        # Load sample data for demonstration
        try:
            df = pd.read_csv(csv_path)
            sample_data = df.head(5).to_html(classes='table table-striped table-sm')
        except Exception as e:
            print(f"Error loading CSV data: {e}")
            sample_data = "<div class='alert alert-warning'>Error loading data sample</div>"
            
        # Get the dashboard from memory
        dashboard = dashboard_utils.get_dashboard(dashboard_id)
        if not dashboard:
            print(f"Dashboard not found in memory: {dashboard_id}")
            return JSONResponse(
                status_code=404,
                content={"error": "Dashboard not available"}
            )
        
        # Extract chart information from the Vizro dashboard
        charts = []
        if dashboard and dashboard.pages and dashboard.pages[0].components:
            for i, component in enumerate(dashboard.pages[0].components):
                # Extract chart information - use component properties directly from Vizro
                chart_title = component.title if hasattr(component, 'title') else f"Chart {i+1}"
                
                # Try to determine the chart type from the figure
                chart_type = "generic"
                if hasattr(component, 'figure'):
                    if hasattr(component.figure, '_name'):
                        chart_type = component.figure._name
                    elif hasattr(component.figure, '_func') and component.figure._func:
                        chart_type = component.figure._func.__name__
                
                charts.append({
                    "title": chart_title, 
                    "type": chart_type.replace('_', ' ').title(),
                    "index": i
                })
        
        # Create a basic HTML representation for export
        # We don't include interactive charts since they would need the Dash server
        template = templates.get_template("dashboard_export.html")
        html_content = template.render(
            title=config.get('title', 'Dashboard'),
            dashboard_id=dashboard_id,
            timestamp=pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S'),
            charts=charts,
            sample_data=sample_data,
            dashboard_url=f"/dashboard/{dashboard_id}"
        )
        
        # Return HTML file for download
        return HTMLResponse(
            content=html_content,
            headers={"Content-Disposition": f"attachment; filename=dashboard-{dashboard_id}.html"}
        )
        
    except Exception as e:
        print(f"Error exporting dashboard {dashboard_id}: {str(e)}")
        print(f"Export exception details:")
        return JSONResponse(
            status_code=500, 
            content={"error": f"Error generating dashboard export: {str(e)}"}
        )

@app.get("/api/dashboard/{dashboard_id}/csv")
async def dashboard_csv(dashboard_id: str):
    """Get the CSV data for a dashboard"""
    try:
        dashboard_path = Path(DASHBOARD_FOLDER) / dashboard_id
        csv_path = dashboard_path / 'data.csv'
        
        if not csv_path.exists():
            print(f"Dashboard CSV not found at {csv_path}")
            return JSONResponse(
                status_code=404,
                content={"error": "Dashboard CSV not found"}
            )
        
        print(f"Serving CSV file for dashboard {dashboard_id}")
        return FileResponse(
            path=str(csv_path),  # FileResponse requires string path
            media_type='text/csv',
            filename=f"dashboard-{dashboard_id}.csv"
        )
    except Exception as e:
        print(f"Error retrieving CSV data for dashboard {dashboard_id}: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Error retrieving CSV data: {str(e)}"}
        )

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8081))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
    print(f" Vizro AI Dashboard Builder running at http://127.0.0.1:{port}")
