import os
import json
import uuid
import logging
import traceback
from typing import List
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from starlette.middleware.wsgi import WSGIMiddleware
import uvicorn
from pydantic import BaseModel
import pandas as pd
from vizro import Vizro

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Import our custom modules
try:
    from backend import dashboard_utils
except ImportError:
    import dashboard_utils

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
        traceback.print_exc()
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
    """
    Handle the generation of a dashboard from CSV data provided in the request.
    
    This endpoint expects a POST request with JSON data containing a 'data' field,
    which holds the CSV data to be used for dashboard creation. A unique dashboard
    ID is generated for each request, and the dashboard is created synchronously. 
    The function returns a JSON response with the dashboard ID and success status 
    or an error message in case of failure.
    """
    try:
        data = await request.json()
        
        if 'data' not in data or not data['data']:
            return JSONResponse(
                status_code=400,
                content={"error": "No data provided"}
            )
        
        dashboard_id = uuid.uuid4().hex
        result = dashboard_utils.create_dashboard_from_config(data, dashboard_id)
        
        if not result['success']:
            return JSONResponse(
                status_code=500,
                content={"error": f"Error creating dashboard: {result.get('error', 'Unknown error')}"}
            )
        
        return JSONResponse(
            status_code=200,
            content={
                'id': dashboard_id,
                'success': True
            }
        )
        
    except Exception as e:
        logger.error(f"Error generating dashboard: {str(e)}")
        logger.exception("Exception details:")
        return JSONResponse(
            status_code=500,
            content={"error": f"Error generating dashboard: {str(e)}"}
        )

@app.get("/dashboard/{dashboard_id}", response_class=HTMLResponse)
async def view_dashboard(request: Request, dashboard_id: str):
    """Serve a dashboard by ID using an iframe wrapper around the Vizro Dash app"""
    try:
        # Get dashboard from memory
        dashboard = dashboard_utils.get_dashboard(dashboard_id)
        if not dashboard:
            logger.error(f"Dashboard not found in memory: {dashboard_id}")
            return templates.TemplateResponse(
                "error.html", 
                {"request": request, "error_message": f"Dashboard not found: {dashboard_id}"}
            )
        
        # Log successful dashboard retrieval
        logger.info(f"Successfully loaded dashboard {dashboard_id} from memory")
        
        # Check if we've already mounted this dashboard as a WSGI app
        dash_path = f"/dash/{dashboard_id}"
        
        # Check if this dashboard is already mounted
        if not any(route.path == dash_path for route in app.routes):
            try:
                # Build the Vizro Dash app
                # Vizro.build() returns the Dashboard object, not a server
                # We need to use Vizro's _dash_app.server to get the WSGI server
                Vizro.build(dashboard)
                
                # Get the server from Vizro's internal property
                if hasattr(dashboard, '_dash_app') and hasattr(dashboard._dash_app, 'server'):
                    dash_server = dashboard._dash_app.server
                else:
                    # If dashboard doesn't have _dash_app, use the global Vizro instance
                    from vizro import Vizro as VizroGlobal
                    if hasattr(VizroGlobal, '_instance') and hasattr(VizroGlobal._instance, '_dash_app'):
                        dash_server = VizroGlobal._instance._dash_app.server
                    else:
                        raise ValueError("Could not access Dash server from Vizro dashboard")
                
                # Mount the Dash app on a dynamic sub-path
                app.mount(dash_path, WSGIMiddleware(dash_server))
                logger.info(f"Mounted Vizro dashboard at {dash_path}")
            except Exception as e:
                logger.error(f"Error mounting Vizro dashboard: {str(e)}")
                logger.exception("Mounting exception details:")
                return templates.TemplateResponse(
                    "error.html", 
                    {"request": request, "error_message": f"Error mounting dashboard: {str(e)}"}
                )
        
        # Return a simple HTML wrapper with an iframe pointing to our mounted Dash app
        return templates.TemplateResponse(
            "dashboard_iframe.html", 
            {
                "request": request, 
                "dashboard_id": dashboard_id,
                "dash_url": dash_path,
                "title": dashboard.pages[0].title if dashboard and dashboard.pages else "Dashboard"
            }
        )
        
    except Exception as e:
        logger.error(f"Error viewing dashboard {dashboard_id}: {e}")
        return templates.TemplateResponse(
            "error.html", 
            {"request": request, "error_message": f"Error loading dashboard: {str(e)}"}
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
            logger.error(f"Dashboard config not found at {config_path}")
            return JSONResponse(
                status_code=404,
                content={"error": "Dashboard not found"}
            )
        
        # Load dashboard configuration
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            logger.info(f"Successfully loaded config for dashboard {dashboard_id}")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in config file: {e}")
            return JSONResponse(
                status_code=500,
                content={"error": "Dashboard configuration is corrupted"}
            )
        
        # Load sample data for demonstration
        try:
            df = pd.read_csv(csv_path)
            sample_data = df.head(5).to_html(classes='table table-striped table-sm')
        except Exception as e:
            logger.error(f"Error loading CSV data: {e}")
            sample_data = "<div class='alert alert-warning'>Error loading data sample</div>"
            
        # Get the dashboard from memory
        dashboard = dashboard_utils.get_dashboard(dashboard_id)
        if not dashboard:
            logger.error(f"Dashboard not found in memory: {dashboard_id}")
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
        logger.error(f"Error exporting dashboard {dashboard_id}: {str(e)}")
        logger.exception("Export exception details:")
        return JSONResponse(
            status_code=500, 
            content={"error": f"Error generating dashboard export: {str(e)}"}
        )

# The code for individual chart API endpoints has been removed
# All chart rendering is now handled by the Vizro Dash app mounted at /dash/{dashboard_id}

@app.get("/api/dashboard/{dashboard_id}/csv")
async def dashboard_csv(dashboard_id: str):
    """Get the CSV data for a dashboard"""
    try:
        dashboard_path = Path(DASHBOARD_FOLDER) / dashboard_id
        csv_path = dashboard_path / 'data.csv'
        
        if not csv_path.exists():
            logger.error(f"Dashboard CSV not found at {csv_path}")
            return JSONResponse(
                status_code=404,
                content={"error": "Dashboard CSV not found"}
            )
        
        logger.info(f"Serving CSV file for dashboard {dashboard_id}")
        return FileResponse(
            path=str(csv_path),  # FileResponse requires string path
            media_type='text/csv',
            filename=f"dashboard-{dashboard_id}.csv"
        )
    except Exception as e:
        logger.error(f"Error retrieving CSV data for dashboard {dashboard_id}: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Error retrieving CSV data: {str(e)}"}
        )

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8081))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
    logger.info(f"🚀 Vizro AI Dashboard Builder running at http://127.0.0.1:{port}")
