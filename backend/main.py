import os
import json
import uuid
import logging
import traceback
from io import StringIO
from typing import List, Optional
from pathlib import Path

from fastapi import FastAPI, File, Form, UploadFile, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
import uvicorn
from pydantic import BaseModel
import pandas as pd
from vizro import Vizro
import vizro.models as vm
import vizro.plotly.express as px

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

# Create directories if they don't exist
static_dir.mkdir(exist_ok=True)
templates_dir.mkdir(exist_ok=True)

# Mount static files and set up templates
app.mount("/static", StaticFiles(directory=static_dir), name="static")
templates = Jinja2Templates(directory=templates_dir)

# Pydantic models for request validation
class ChartConfig(BaseModel):
    type: str

class DashboardRequest(BaseModel):
    charts: List[str]
    layout: str = "grid"
    columns: int = 2
    data: str

# Dictionary to store active dashboard apps
dashboard_apps = {}

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

@app.post("/generate")
async def generate(request: Request):
    """Generate a dashboard from CSV data"""
    try:
        # Extract request data
        data = await request.json()
        
        # Validate request data
        if 'data' not in data or not data['data']:
            return JSONResponse(
                status_code=400,
                content={"error": "No data provided"}
            )
        
        # Generate a unique ID for this dashboard
        dashboard_id = uuid.uuid4().hex
        
        # Create the dashboard synchronously to ensure it's available when the user clicks the link
        result = dashboard_utils.create_dashboard_from_config(data, dashboard_id)
        
        if not result['success']:
            return JSONResponse(
                status_code=500,
                content={"error": f"Error creating dashboard: {result.get('error', 'Unknown error')}"}
            )
        
        # Store the dashboard in the active dashboards dictionary
        dashboard_utils.active_dashboards[dashboard_id] = result['dashboard']
        
        # Return the dashboard URL as JSONResponse with proper content-type headers
        return JSONResponse(
            status_code=200,
            content={
                'id': dashboard_id,
                'url': f"/dashboard/{dashboard_id}"
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
    """Serve a dashboard by ID"""
    try:
        # Check if dashboard folder exists
        dashboard_path = os.path.join(DASHBOARD_FOLDER, dashboard_id)
        if not os.path.exists(dashboard_path):
            logger.error(f"Dashboard directory not found: {dashboard_path}")
            return templates.TemplateResponse(
                "error.html", 
                {"request": request, "error_message": f"Dashboard not found: {dashboard_id}"}
            )
            
        # Get dashboard data
        dashboard = dashboard_utils.get_dashboard(dashboard_id)
        if not dashboard:
            logger.error(f"Failed to load dashboard {dashboard_id} from storage")
            return templates.TemplateResponse(
                "error.html", 
                {"request": request, "error_message": f"Dashboard not found: {dashboard_id}"}
            )
        
        logger.info(f"Successfully loaded dashboard {dashboard_id}")
        
        # Return the dashboard using the template
        return templates.TemplateResponse(
            "dashboard_view.html", 
            {
                "request": request, 
                "dashboard_id": dashboard_id,
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
            
        # Get the dashboard data from memory or storage
        dashboard = dashboard_utils.get_dashboard(dashboard_id)
        
        # Prepare chart data for the template
        charts = []
        if dashboard and dashboard.pages and dashboard.pages[0].components:
            for i, component in enumerate(dashboard.pages[0].components):
                # Extract chart information
                chart_type = "generic"
                
                # Try to determine the chart type
                if hasattr(component.figure, '_name'):
                    chart_type = component.figure._name
                elif hasattr(component.figure, '_func') and component.figure._func:
                    chart_type = component.figure._func.__name__
                elif hasattr(component, 'figure_constructor'):
                    chart_type = component.figure_constructor.__name__
                
                charts.append({
                    "title": component.title or f"Chart {i+1}", 
                    "type": chart_type.replace('_', ' ').title(),
                    "index": i
                })
        
        # Render the HTML template
        from jinja2 import Template
        template = templates.get_template("dashboard_export.html")
        html_content = template.render(
            title=config.get('title', 'Dashboard'),
            dashboard_id=dashboard_id,
            timestamp=pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S'),
            charts=charts,
            sample_data=sample_data
        )
        
        # Return HTML file for download
        return HTMLResponse(
            content=html_content,
            headers={"Content-Disposition": f"attachment; filename=dashboard-{dashboard_id}.html"}
        )
        
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/dashboard/{dashboard_id}/data")
async def dashboard_data(dashboard_id: str, request: Request, download: bool = False):
    """Get dashboard metadata or download CSV data"""
    try:
        dashboard_path = Path(DASHBOARD_FOLDER) / dashboard_id
        config_path = dashboard_path / 'config.json'
        csv_path = dashboard_path / 'data.csv'
        
        # Check if files exist
        if not config_path.exists():
            logger.error(f"Dashboard config not found at {config_path}")
            return JSONResponse(
                status_code=404,
                content={"error": "Dashboard not found"}
            )
            
        # If download parameter is true or we're using content negotiation, return the CSV file
        if download or 'text/csv' in request.headers.get('accept', ''):
            if not csv_path.exists():
                logger.error(f"CSV data not found at {csv_path}")
                return JSONResponse(
                    status_code=404,
                    content={"error": "CSV data not found"}
                )
                
            return FileResponse(
                path=str(csv_path),  # FileResponse requires string path
                filename=f"dashboard-{dashboard_id}.csv",
                media_type="text/csv"
            )
        
        # Otherwise return the dashboard metadata as JSON
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in config file: {e}")
            return JSONResponse(
                status_code=500, 
                content={"error": "Dashboard configuration is corrupted"})
        except Exception as e:
            logger.error(f"Error reading config file: {e}")
            return JSONResponse(
                status_code=500,
                content={"error": f"Could not read dashboard configuration: {str(e)}"})
            
        
        # Return properly formatted JSON with content-type header
        return JSONResponse(
            status_code=200,
            content={
                "title": config.get("title", "Interactive Dashboard"),
                "charts": config.get("charts", [])
            }
        )
    except Exception as e:
        logger.error(f"Error retrieving dashboard data: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Error retrieving dashboard data: {str(e)}"}
        )

@app.get("/api/dashboard/{dashboard_id}/chart/{chart_index}")
async def dashboard_chart(dashboard_id: str, chart_index: int):
    """Get a specific chart from a dashboard"""
    try:
        # Check if dashboard exists
        dashboard = dashboard_utils.get_dashboard(dashboard_id)
        if not dashboard:
            logger.error(f"Dashboard not found: {dashboard_id}")
            return JSONResponse(
                status_code=404,
                content={"error": "Dashboard not found"}
            )
        
        # Get the specific chart
        page = dashboard.pages[0]
        if chart_index >= len(page.components):
            logger.error(f"Chart index out of range: {chart_index}, max: {len(page.components)-1}")
            return JSONResponse(
                status_code=404,
                content={"error": f"Chart index {chart_index} not found"}
            )
        
        # Extract the chart figure
        chart = page.components[chart_index]
        logger.debug(f"Found chart: {chart.id}, type: {type(chart.figure)}")
        
        # Validate chart has necessary attributes
        if not hasattr(chart, 'figure'):
            logger.error(f"Chart has no figure attribute: {chart.id}")
            return JSONResponse(
                status_code=500, 
                content={"error": "Chart rendering failed: Invalid chart structure"}
            )
        
        if chart.figure is None:
            logger.error(f"Chart figure is None for chart: {chart.id}")
            return JSONResponse(
                status_code=500,
                content={"error": "Chart rendering failed: No visualization data"}
            )
        
        # Extract chart type from chart ID or figure
        chart_id = chart.id
        logger.debug(f"Processing chart with ID: {chart_id}")
        
        # Extract chart type from the chart ID which contains type information
        chart_type = 'scatter'  # Default fallback
        if '_bar_' in chart_id:
            chart_type = 'bar'
        elif '_line_' in chart_id:
            chart_type = 'line'
        elif '_pie_' in chart_id:
            chart_type = 'pie'
        elif '_scatter_' in chart_id:
            chart_type = 'scatter'
        elif '_histogram_' in chart_id:
            chart_type = 'histogram'
            
        # Also check function if available
        if hasattr(chart.figure, '_func'):
            func_name = chart.figure._func.__name__
            if func_name in ['bar', 'line', 'pie', 'scatter', 'histogram']:
                chart_type = func_name
                
        logger.info(f"Serving chart {chart_index} of type {chart_type}")

        
        # Handle different types of figure objects
        try:
            # If it has a to_dict method, use it (standard Plotly figure)
            if hasattr(chart.figure, 'to_dict'):
                figure_dict = chart.figure.to_dict()
            # If it's already a dict, use it directly (pre-processed)
            elif isinstance(chart.figure, dict):
                figure_dict = chart.figure
            # If it's a plotly figure or similar object with data/layout attributes
            elif hasattr(chart.figure, 'data') and hasattr(chart.figure, 'layout'):
                # Handle cases where data contains trace objects
                if hasattr(chart.figure.data, '__iter__'):
                    traces = []
                    for trace in chart.figure.data:
                        if hasattr(trace, '__dict__'):
                            trace_dict = trace.__dict__
                        elif isinstance(trace, dict):
                            trace_dict = trace
                        else:
                            # Extract key plotly trace properties if possible
                            trace_dict = {}
                            for attr in ['type', 'x', 'y', 'z', 'text', 'mode', 'name', 'marker', 'line']:
                                if hasattr(trace, attr):
                                    trace_dict[attr] = getattr(trace, attr)
                        
                        # Set the correct chart type in the trace
                        if 'type' not in trace_dict or trace_dict.get('type') != chart_type:
                            trace_dict['type'] = chart_type
                            
                        traces.append(trace_dict)
                    
                    # Handle the layout similarly
                    layout = {}
                    if hasattr(chart.figure.layout, '__dict__'):
                        layout = chart.figure.layout.__dict__
                    elif isinstance(chart.figure.layout, dict):
                        layout = chart.figure.layout
                    else:
                        # Extract key layout properties
                        for attr in ['title', 'width', 'height', 'xaxis', 'yaxis', 'margin']:
                            if hasattr(chart.figure.layout, attr):
                                layout[attr] = getattr(chart.figure.layout, attr)
                    
                    figure_dict = {
                        'data': traces,
                        'layout': layout
                    }
                else:
                    # Fallback if the figure data is not iterable
                    figure_dict = {
                        'data': [{'type': chart_type, 'mode': 'lines+markers' if chart_type in ['scatter', 'line'] else None}],
                        'layout': {'title': {'text': 'Chart Preview'}}
                    }
                    logger.warning(f"Failed to extract figure data from chart {chart_index}, using fallback")
            # For CapturedCallable and other special cases from Vizro
            elif hasattr(chart.figure, '_func') and callable(chart.figure._func):
                try:
                    logger.info(f"Processing CapturedCallable for chart index {chart_index}")
                    
                    # Try to get the chart type from ID
                    chart_type = 'scatter'  # Default fallback
                    if hasattr(chart, 'id'):
                        chart_id = chart.id
                        if '_bar_' in chart_id:
                            chart_type = 'bar'
                        elif '_line_' in chart_id:
                            chart_type = 'line'
                        elif '_pie_' in chart_id:
                            chart_type = 'pie'
                        elif '_scatter_' in chart_id:
                            chart_type = 'scatter'
                    logger.debug(f"Detected chart type from ID: {chart_type}")
                    
                    
                    # Try to get the dataframe
                    import pandas as pd
                    df = None
                    
                    # Try to get dataframe from chart or dashboard
                    if hasattr(chart.figure, '_dataframe') and isinstance(chart.figure._dataframe, pd.DataFrame):
                        df = chart.figure._dataframe
                        logger.debug(f"Found dataframe for chart: {df.shape}")
                    else:
                        # Try to get data from dashboard
                        dashboard = dashboard_utils.get_dashboard(dashboard_id)
                        if dashboard and hasattr(dashboard, 'data') and isinstance(dashboard.data, pd.DataFrame):
                            df = dashboard.data
                            logger.debug(f"Using dashboard data for chart: {df.shape}")
                        else:
                            logger.warning(f"No dataframe found for chart {chart_index}")
                    
                    
                    # Generate appropriate chart based on type and available data
                    if df is not None and not df.empty:
                        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
                        categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
                        
                        if chart_type == 'bar' and numeric_cols and categorical_cols:
                            figure_dict = {
                                'data': [{
                                    'type': 'bar',
                                    'x': df[categorical_cols[0]].tolist(),
                                    'y': df[numeric_cols[0]].tolist(),
                                    'name': f"{categorical_cols[0]} vs {numeric_cols[0]}"
                                }],
                                'layout': {
                                    'title': f"Bar Chart - {categorical_cols[0]} vs {numeric_cols[0]}",
                                    'xaxis': {'title': categorical_cols[0]},
                                    'yaxis': {'title': numeric_cols[0]}
                                }
                            }
                        elif chart_type == 'pie' and numeric_cols and categorical_cols:
                            figure_dict = {
                                'data': [{
                                    'type': 'pie',
                                    'labels': df[categorical_cols[0]].tolist(),
                                    'values': df[numeric_cols[0]].tolist(),
                                    'name': f"{categorical_cols[0]} distribution"
                                }],
                                'layout': {'title': f"Pie Chart - {numeric_cols[0]} by {categorical_cols[0]}"}
                            }
                        elif chart_type == 'line' and len(numeric_cols) >= 2:
                            figure_dict = {
                                'data': [{
                                    'type': 'line',
                                    'x': df[numeric_cols[0]].tolist(),
                                    'y': df[numeric_cols[1]].tolist(),
                                    'mode': 'lines+markers',
                                    'name': f"{numeric_cols[1]} vs {numeric_cols[0]}"
                                }],
                                'layout': {
                                    'title': f"Line Chart - {numeric_cols[1]} vs {numeric_cols[0]}",
                                    'xaxis': {'title': numeric_cols[0]},
                                    'yaxis': {'title': numeric_cols[1]}
                                }
                            }
                        else:  # Default to scatter
                            if len(numeric_cols) >= 2:
                                logger.debug(f"Creating scatter plot with columns {numeric_cols[0]} and {numeric_cols[1]}")
                                try:
                                    figure_dict = {
                                        'data': [{
                                            'type': 'scatter',
                                            'x': df[numeric_cols[0]].tolist(),
                                            'y': df[numeric_cols[1]].tolist(),
                                            'mode': 'markers',
                                            'name': f"{numeric_cols[1]} vs {numeric_cols[0]}"
                                        }],
                                        'layout': {
                                            'title': f"Scatter Plot - {numeric_cols[1]} vs {numeric_cols[0]}",
                                            'xaxis': {'title': numeric_cols[0]},
                                            'yaxis': {'title': numeric_cols[1]}
                                        }
                                    }
                                except Exception as scatter_error:
                                    logger.error(f"Error creating scatter plot: {scatter_error}")
                                    raise
                            else:
                                # Fallback for insufficient data
                                figure_dict = {
                                    'data': [{'type': 'scatter', 'x': [1,2,3,4,5], 'y': [5,4,3,2,1], 'mode': 'markers'}],
                                    'layout': {'title': f"Chart {chart_index} (Sample Data)"}
                                }
                    else:
                        # No dataframe available
                        logger.warning(f"No dataframe available for chart {chart_index}, using sample data")
                        figure_dict = {
                            'data': [{'type': chart_type, 'x': [1,2,3,4,5], 'y': [5,4,3,2,1], 'mode': 'lines+markers'}],
                            'layout': {
                                'title': f"Chart {chart_index} (Sample Data)", 
                                'showlegend': True,
                                'annotations': [{
                                    'text': "No data available",
                                    'showarrow': False,
                                    'font': {'color': 'red'},
                                    'xref': 'paper',
                                    'yref': 'paper',
                                    'x': 0.5,
                                    'y': 0.5
                                }]
                            }
                        }
                except Exception as eval_error:
                    logger.error(f"Error evaluating chart {chart_index}: {eval_error}")
                    # Create a sample chart as fallback
                    figure_dict = {
                        'data': [{'type': 'scatter', 'x': [1, 2, 3, 4, 5], 'y': [3, 1, 5, 2, 4], 'mode': 'lines+markers', 'name': 'Sample Data'}],
                        'layout': {
                            'title': f"Chart {chart_index} (Error)", 
                            'showlegend': True,
                            'annotations': [{
                                'text': f"Error: {str(eval_error)[:50]}...",
                                'showarrow': False,
                                'font': {'color': 'red'},
                                'xref': 'paper',
                                'yref': 'paper',
                                'x': 0.5,
                                'y': 0.5
                            }]
                        }
                    }
            # For other cases, try to create a basic structure
            else:
                logger.warning(f"Unknown figure type: {type(chart.figure)}, attempting generic serialization")
                # Try to access key attributes that might be useful for Plotly
                try:
                    # Try to extract data attributes safely
                    if hasattr(chart.figure, 'data'):
                        chart_data = chart.figure.data
                    else:
                        chart_data = [{'type': 'scatter', 'x': [1, 2, 3, 4, 5], 'y': [5, 4, 3, 2, 1], 'mode': 'lines+markers', 'name': 'Sample'}]
                    
                    # Try to extract layout attributes safely
                    if hasattr(chart.figure, 'layout'):
                        chart_layout = chart.figure.layout
                    else:
                        chart_layout = {'title': f"Chart {chart_index}"}
                        
                    figure_dict = {
                        'data': chart_data,
                        'layout': chart_layout
                    }
                    logger.debug(f"Created fallback figure dictionary for unknown chart type")
                except Exception as extract_error:
                    logger.error(f"Error extracting figure attributes: {extract_error}")
                    figure_dict = {
                        'data': [{'type': 'scatter', 'x': [1, 2, 3, 4, 5], 'y': [5, 4, 3, 2, 1], 'mode': 'lines+markers', 'name': 'Sample'}],
                        'layout': {'title': f"Chart {chart_index} (Serialization Error)"}
                    }
            
            # Validate and ensure figure_dict has the minimum required structure
            try:
                # Check for data key and ensure it's a valid list
                if 'data' not in figure_dict or not isinstance(figure_dict['data'], list) or not figure_dict['data']:
                    logger.warning(f"Chart {chart_index} missing data, using default data")
                    figure_dict['data'] = [{'type': 'scatter', 'x': [0, 1], 'y': [0, 1], 'mode': 'lines', 'name': 'Default Data'}]
                
                # Check for layout key and ensure it's a dictionary
                if 'layout' not in figure_dict or not isinstance(figure_dict['layout'], dict):
                    logger.warning(f"Chart {chart_index} missing layout, using default layout")
                    figure_dict['layout'] = {'title': f"Chart {chart_index}"}
                
                # Ensure layout has a title
                if 'title' not in figure_dict['layout'] or not figure_dict['layout']['title']:
                    figure_dict['layout']['title'] = f"Chart {chart_index}"
                    
                logger.debug(f"Figure dictionary validated for chart {chart_index}")
            except Exception as validation_error:
                logger.error(f"Error validating figure dictionary: {validation_error}")
                # Reset to a guaranteed valid structure
                figure_dict = {
                    'data': [{'type': 'scatter', 'x': [0, 1], 'y': [0, 1], 'mode': 'lines', 'name': 'Error Recovery Data'}],
                    'layout': {'title': f"Chart {chart_index} (Validation Error)"}
                }
                
            # Return the chart with its figure dictionary using JSONResponse to set proper content-type
            return JSONResponse(
                content={"id": chart.id, "figure": figure_dict},
                status_code=200
            )
            
        except Exception as figure_error:
            logger.error(f"Critical error processing chart {chart_index} for dashboard {dashboard_id}: {figure_error}")
            
            # Create a meaningful chart ID if the original is not available
            chart_id = getattr(chart, 'id', f"error-chart-{chart_index}")
            
            # Return fallback error figure with improved error display using JSONResponse
            return JSONResponse(
                status_code=200,
                content={
                    "id": chart_id,
                    "figure": {
                        "data": [{
                            "type": "scatter",
                            "x": [1, 2, 3, 4, 5],
                            "y": [1, 1, 1, 1, 1],
                            "mode": "lines+markers",
                            "name": "Error Data",
                            "marker": {"color": "red"}
                        }],
                        "layout": {
                            "title": f"Chart {chart_index} (Error)",
                            "annotations": [{
                                "text": f"Error: {str(figure_error)[:100]}",
                                "showarrow": False,
                                "font": {"color": "red", "size": 14},
                                "xref": "paper",
                                "yref": "paper",
                                "x": 0.5,
                                "y": 0.5
                            }, {
                                "text": "A problem occurred while generating this chart.",
                                "showarrow": False,
                                "font": {"color": "#555", "size": 12},
                                "xref": "paper",
                                "yref": "paper", 
                                "x": 0.5,
                                "y": 0.4
                            }]
                        }
                    }
                }
            )
    except Exception as e:
        logger.error(f"Error retrieving chart {chart_index} for dashboard {dashboard_id}: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Error retrieving chart: {str(e)}"}
        )

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
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)

