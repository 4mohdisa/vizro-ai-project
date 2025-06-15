import os
import pandas as pd
import io
import json
import logging
import traceback
from typing import Optional

# Vizro imports
import vizro.models as vm
import vizro.plotly.express as px

# Directory for dashboard storage
DASHBOARD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'dashboards')
os.makedirs(DASHBOARD_FOLDER, exist_ok=True)

logger = logging.getLogger(__name__)

def convert_time_to_float(s):
    """Convert time string like '8 hours 45 minutes' to float hours"""
    import re
    if not isinstance(s, str):
        return 0
    hours = re.search(r'(\d+)\s*hour', s)
    minutes = re.search(r'(\d+)\s*minute', s)
    h = int(hours.group(1)) if hours else 0
    m = int(minutes.group(1)) if minutes else 0
    return round(h + m / 60.0, 2)

def analyze_csv_data(csv_data: str) -> dict:
    """Analyze CSV data to determine column types and suggest visualizations using pandas
    
    Args:
        csv_data: String containing CSV data
        
    Returns:
        dict: Analysis results including dataframe, column types and chart recommendations
    """
    try:
        logger.info("Analyzing CSV data with pandas")
        
        # Read the CSV data with simplified guard
        try:
            df = pd.read_csv(io.StringIO(csv_data))
        except Exception as e:
            raise ValueError(f"Invalid CSV format: {e}")
            
        if df.empty:
            raise ValueError("Uploaded CSV file is empty")
            
        logger.debug(f"DataFrame shape: {df.shape}")
        logger.debug(f"DataFrame columns: {df.columns.tolist()}")
        logger.debug(f"Sample data:\n{df.head(2).to_string()}")
        
        # Identify column types
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        
        # Check for time worked column
        if 'Total Time Worked' in df.columns or 'Total' in df.columns:
            col_name = 'Total Time Worked' if 'Total Time Worked' in df.columns else 'Total'
            df['total_hours'] = df[col_name].apply(convert_time_to_float)
            if 'total_hours' not in numeric_cols:
                numeric_cols.append('total_hours')
                
        categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
        
        # Merged date column detection in single pass
        date_cols, to_reinterpret = [], []
        for col in df.columns:
            if col in numeric_cols:
                continue
            
            # Check if this is a categorical column with date keywords
            if col in categorical_cols and any(k in col.lower() for k in ['date','time','day','month','year']):
                to_reinterpret.append(col)
            # For other non-numeric columns, try parsing as dates
            elif col not in categorical_cols:
                try:
                    pd.to_datetime(df[col])
                    date_cols.append(col)
                except ValueError:  # Ignore columns that can't be parsed as dates
                    pass

        # Now convert all to_reinterpret at once:
        for col in to_reinterpret:
            df[col] = pd.to_datetime(df[col], errors='coerce')
            date_cols.append(col)
            categorical_cols.remove(col)
        
        # If we still don't have numeric columns, create a count column
        if not numeric_cols:
            df['count'] = 1
            numeric_cols = ['count']
        
        # Create chart recommendations based on data types
        def make_rec(type_, suitable, msg, **kwargs):
            base = {'type': type_, 'suitable': suitable, 'message': msg}
            base.update(kwargs)
            return base
        
        chart_recommendations = []
        
        # Bar charts
        chart_recommendations.append(
            make_rec(
                'bar',
                bool(numeric_cols and categorical_cols),
                'Bar charts are great for comparing values across categories.' if numeric_cols and categorical_cols 
                else 'Bar charts require at least one numeric and one categorical column.',
                x_axis=categorical_cols[0] if categorical_cols else None,
                y_axis=numeric_cols[0] if numeric_cols else None,
                title=f"{numeric_cols[0]} by {categorical_cols[0]}" if numeric_cols and categorical_cols else None
            )
        )
        
        # Line charts
        if date_cols and numeric_cols:
            chart_recommendations.append(
                make_rec(
                    'line', True,
                    'Line charts are perfect for showing trends over time.',
                    x_axis=date_cols[0], y_axis=numeric_cols[0],
                    title=f"{numeric_cols[0]} over time"
                )
            )
        elif len(numeric_cols) >= 2:
            chart_recommendations.append(
                make_rec(
                    'line', True,
                    'Line charts can show relationships between numeric values.',
                    x_axis=numeric_cols[0], y_axis=numeric_cols[1],
                    title=f"{numeric_cols[1]} vs {numeric_cols[0]}"
                )
            )
        else:
            chart_recommendations.append(
                make_rec(
                    'line', False,
                    'Line charts require at least one date column and one numeric column, or two numeric columns.'
                )
            )
        
        # Pie charts
        chart_recommendations.append(
            make_rec(
                'pie',
                bool(numeric_cols and categorical_cols),
                'Pie charts show the composition of a whole.' if numeric_cols and categorical_cols
                else 'Pie charts require at least one numeric and one categorical column.',
                labels=categorical_cols[0] if categorical_cols else None,
                values=numeric_cols[0] if numeric_cols else None,
                title=f"Distribution of {numeric_cols[0]} by {categorical_cols[0]}" if numeric_cols and categorical_cols else None
            )
        )
        
        # Scatter plots
        chart_recommendations.append(
            make_rec(
                'scatter',
                bool(len(numeric_cols) >= 2),
                'Scatter plots show the relationship between two variables.' if len(numeric_cols) >= 2
                else 'Scatter plots require at least two numeric columns.',
                x_axis=numeric_cols[0] if len(numeric_cols) >= 1 else None,
                y_axis=numeric_cols[1] if len(numeric_cols) >= 2 else None,
                title=f"{numeric_cols[1]} vs {numeric_cols[0]}" if len(numeric_cols) >= 2 else None
            )
        )
        
        return {
            'df': df,
            'numeric_columns': numeric_cols,
            'categorical_columns': categorical_cols,
            'date_columns': date_cols,
            'chart_recommendations': chart_recommendations
        }
    
    except Exception as e:
        print(f"❌ Error analyzing CSV data: {str(e)}")
        traceback.print_exc()
        return None

def create_dashboard_from_config(data, dashboard_id):
    """Create a Vizro Dashboard object from the provided configuration
    
    Args:
        data: Dictionary containing CSV data and chart selections
        dashboard_id: Unique identifier for the dashboard
        
    Returns:
        dict: Result dictionary containing success status, dashboard object, and error message if any
    """
    try:
        # 1. Guard
        csv_data = data.get('data', '')
        if not csv_data:
            raise ValueError("No CSV data provided")
            
        selected_charts = data.get('charts', [])
        
        # 2. Chart selection
        default_types = ['bar', 'line', 'pie', 'scatter']
        if not selected_charts:
            selected_charts = default_types.copy()
        selected_charts = (selected_charts + default_types)[:4]
        
        # 3. Single try for disk writes
        dashboard_path = os.path.join(DASHBOARD_FOLDER, dashboard_id)
        csv_path = os.path.join(dashboard_path, 'data.csv')
        try:
            os.makedirs(dashboard_path, exist_ok=True)
            with open(csv_path, 'w') as f:
                f.write(csv_data)
        except Exception as e:
            raise RuntimeError(f"Disk write failed: {e}")
        
        # 4. Analyze CSV (unchanged)
        analysis = analyze_csv_data(csv_data)
        if not analysis:
            raise ValueError("Failed to analyze CSV data")
            
        df = analysis['df']
        numeric_cols = analysis.get('numeric_columns', [])
        categorical_cols = analysis.get('categorical_columns', [])
        
        # 5. Build components with one-block fallbacks
        components = []
        for i, t in enumerate(selected_charts):
            chart_id = f"{dashboard_id}_chart_{i}_{t}"
            title = f"{t.capitalize()} Chart {i+1}"
            
            if t == 'bar' and categorical_cols and numeric_cols:
                fig = px.bar(df, x=categorical_cols[0], y=numeric_cols[0], title=title)
            elif t == 'line' and len(numeric_cols) >= 2:
                fig = px.line(df, x=numeric_cols[0], y=numeric_cols[1], title=title)
            elif t == 'pie' and categorical_cols and numeric_cols:
                fig = px.pie(df, names=categorical_cols[0], values=numeric_cols[0], title=title)
            elif t == 'scatter' and len(numeric_cols) >= 2:
                fig = px.scatter(df, x=numeric_cols[0], y=numeric_cols[1], title=title)
            else:
                if numeric_cols:
                    fig = px.histogram(df, x=numeric_cols[0], title=title)
                elif categorical_cols:
                    vc = df[categorical_cols[0]].value_counts()
                    fig = px.bar(x=vc.index, y=vc.values, title=title)
                else:
                    continue
                    
            components.append(vm.Graph(id=chart_id, figure=fig))

        # 6. Final dashboard
        page = vm.Page(id=f"page_{dashboard_id}", title="Dashboard", components=components)
        dashboard = vm.Dashboard(title="AI Dashboard", pages=[page])

        return {'success': True, 'dashboard_id': dashboard_id, 'dashboard': dashboard}
        
    except Exception as e:
        logger.error(f"Error creating dashboard: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

def get_dashboard(dashboard_id: str) -> Optional[vm.Dashboard]:
    """Retrieve a Vizro Dashboard by ID by rebuilding it from stored configuration
    
    Args:
        dashboard_id: Unique identifier for the dashboard
        
    Returns:
        Optional[vm.Dashboard]: The Vizro Dashboard object if found/created, None otherwise
    """
    # Otherwise try to load it from storage and rebuild
    dashboard_path = os.path.join(DASHBOARD_FOLDER, dashboard_id)
    config_path = os.path.join(dashboard_path, 'config.json')
    
    if not os.path.exists(config_path):
        logger.error(f"Dashboard config not found at {config_path}")
        return None
    
    try:
        # Load configuration
        with open(config_path, 'r') as f:
            config = json.load(f)
        logger.info(f"Loaded config for dashboard {dashboard_id}")
        
        # Load data - handle both absolute and relative paths
        data_path = config.get('data_path')
        if not os.path.isabs(data_path):
            # If it's a relative path, make it absolute relative to dashboard folder
            data_path = os.path.join(dashboard_path, os.path.basename(data_path))
            
        # Default to data.csv in the dashboard directory if not specified or not found
        if not data_path or not os.path.exists(data_path):
            data_path = os.path.join(dashboard_path, 'data.csv')
            
        if not os.path.exists(data_path):
            logger.error(f"Data file not found at: {data_path}")
            return None
            
        # Safely read data file
        try:
            with open(data_path, 'r') as data_file:
                csv_data = data_file.read()
                
            # Get chart definitions from config
            charts_config = config.get('charts', [])
            chart_types = []
            
            # Handle both formats: array of strings or array of objects with 'type' property
            for chart in charts_config:
                if isinstance(chart, str):
                    chart_types.append(chart)
                elif isinstance(chart, dict) and 'type' in chart:
                    chart_types.append(chart['type'])
            
            # If no chart types found, use default chart types
            if not chart_types:
                chart_types = ['bar', 'line', 'pie', 'scatter']
            
            logger.info(f"Recreating dashboard {dashboard_id} with chart types: {chart_types}")
            
            # Recreate the dashboard
            result = create_dashboard_from_config({
                'data': csv_data,
                'charts': chart_types,
                'title': config.get('title', 'AI Dashboard')  # Pass the title if available
            }, dashboard_id)
            
            if result.get('success'):
                # Return the dashboard
                return result['dashboard']
            else:
                logger.error(f"Failed to recreate dashboard: {result.get('error')}")
                return None
        except Exception as file_err:
            logger.error(f"Error reading data file {data_path}: {file_err}")
            logger.exception("Data file reading exception details:")
            return None
    except Exception as e:
        logger.error(f"Error loading dashboard {dashboard_id}: {str(e)}")
        logger.exception("Dashboard loading exception details:")
        return None
