import os
import pandas as pd
import io
import json
import logging
import uuid
import traceback
from pathlib import Path
from typing import Dict, List, Any, Optional

# Vizro imports
from vizro import Vizro
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
        
        # Create a StringIO object from the CSV string
        csv_buffer = io.StringIO(csv_data)
        
        # Read the CSV data
        try:
            df = pd.read_csv(csv_buffer)
            logger.debug(f"DataFrame shape: {df.shape}")
        except Exception as csv_error:
            logger.error(f"Failed to parse CSV data: {csv_error}")
            raise ValueError(f"Invalid CSV format: {str(csv_error)}")
            
        if df.empty:
            logger.warning("Dataframe is empty after CSV parsing")
            raise ValueError("The uploaded CSV file appears to be empty")
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
        date_cols = []
        
        # Try to identify date columns
        for col in df.columns:
            if col not in numeric_cols and col not in categorical_cols:
                try:
                    pd.to_datetime(df[col])
                    date_cols.append(col)
                except:
                    pass
        
        # Try to convert string columns that might be dates
        for col in list(categorical_cols):  # Create a copy to avoid modification during iteration
            if any(date_keyword in col.lower() for date_keyword in ['date', 'time', 'day', 'month', 'year']):
                try:
                    pd.to_datetime(df[col])
                    date_cols.append(col)
                    categorical_cols.remove(col)
                except:
                    pass
        
        # Try to convert string columns that might be numeric
        for col in list(categorical_cols):  # Create a copy to avoid modification during iteration
            if any(num_keyword in col.lower() for num_keyword in ['total', 'sum', 'count', 'amount', 'price', 'cost', 'value', 'number']):
                try:
                    # Try to extract numeric values from strings like "8 hours" -> 8
                    df[col + '_numeric'] = df[col].str.extract(r'(\d+\.?\d*)').astype(float)
                    if not df[col + '_numeric'].isna().all():
                        numeric_cols.append(col + '_numeric')
                except:
                    pass
        
        # If we still don't have numeric columns, create a count column
        if not numeric_cols:
            df['count'] = 1
            numeric_cols = ['count']
        
        # Create chart recommendations based on data types
        chart_recommendations = []
        
        # For bar charts, we need at least one numeric and one categorical column
        if numeric_cols and categorical_cols:
            chart_recommendations.append({
                'type': 'bar',
                'suitable': True,
                'message': 'Bar charts are great for comparing values across categories.',
                'x_axis': categorical_cols[0],
                'y_axis': numeric_cols[0],
                'title': f"{numeric_cols[0]} by {categorical_cols[0]}"
            })
        else:
            chart_recommendations.append({
                'type': 'bar',
                'suitable': False,
                'message': 'Bar charts require at least one numeric and one categorical column.'
            })
        
        # For line charts, we need at least one date column and one numeric column, or two numeric columns
        if date_cols and numeric_cols:
            chart_recommendations.append({
                'type': 'line',
                'suitable': True,
                'message': 'Line charts are perfect for showing trends over time.',
                'x_axis': date_cols[0],
                'y_axis': numeric_cols[0],
                'title': f"{numeric_cols[0]} over time"
            })
        elif len(numeric_cols) >= 2:
            chart_recommendations.append({
                'type': 'line',
                'suitable': True,
                'message': 'Line charts can show relationships between numeric values.',
                'x_axis': numeric_cols[0],
                'y_axis': numeric_cols[1],
                'title': f"{numeric_cols[1]} vs {numeric_cols[0]}"
            })
        else:
            chart_recommendations.append({
                'type': 'line',
                'suitable': False,
                'message': 'Line charts require at least one date column and one numeric column, or two numeric columns.'
            })
        
        # For pie charts, we need at least one numeric and one categorical column
        if numeric_cols and categorical_cols:
            chart_recommendations.append({
                'type': 'pie',
                'suitable': True,
                'message': 'Pie charts show the composition of a whole.',
                'labels': categorical_cols[0],
                'values': numeric_cols[0],
                'title': f"Distribution of {numeric_cols[0]} by {categorical_cols[0]}"
            })
        else:
            chart_recommendations.append({
                'type': 'pie',
                'suitable': False,
                'message': 'Pie charts require at least one numeric and one categorical column.'
            })
        
        # For scatter plots, we need at least two numeric columns
        if len(numeric_cols) >= 2:
            chart_recommendations.append({
                'type': 'scatter',
                'suitable': True,
                'message': 'Scatter plots show the relationship between two variables.',
                'x_axis': numeric_cols[0],
                'y_axis': numeric_cols[1], 
                'title': f"{numeric_cols[1]} vs {numeric_cols[0]}"
            })
        else:
            chart_recommendations.append({
                'type': 'scatter',
                'suitable': False,
                'message': 'Scatter plots require at least two numeric columns.'
            })
        
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
    """Create a dashboard from the provided configuration"""
    try:
        # Make sure the DASHBOARD_FOLDER exists
        os.makedirs(DASHBOARD_FOLDER, exist_ok=True)
        
        # Extract data from the request
        csv_data = data.get('data', '')
        if not csv_data:
            logger.error("No CSV data provided in request")
            raise ValueError("No CSV data provided")
            
        selected_charts = data.get('charts', [])
        
        # Ensure we have diverse chart types for the dashboard
        default_chart_types = ['bar', 'line', 'pie', 'scatter']
        
        # Important: Keep track of original chart selections for strict adherence
        original_selections = selected_charts.copy() if selected_charts else []
        
        if len(selected_charts) == 0:
            # If no charts selected, use all default types
            selected_charts = default_chart_types.copy()
            logger.info("Using default chart types for dashboard")
        elif len(selected_charts) < 4:
            # If some charts selected but fewer than 4, add missing types
            # from defaults to ensure diversity
            missing_count = 4 - len(selected_charts)
            
            # Find chart types that aren't already selected
            available_types = [t for t in default_chart_types if t not in selected_charts]
            
            if available_types:
                # Add missing chart types from available defaults first
                selected_charts.extend(available_types[:missing_count])
                missing_count -= len(available_types)
            
            # If we still need more, then duplicate existing ones without repeating too much
            if missing_count > 0:
                current_types = selected_charts.copy()
                while len(selected_charts) < 4:
                    # Cycle through current types to avoid too many duplicates
                    selected_charts.append(current_types[len(selected_charts) % len(current_types)])
                
            logger.info(f"Extended chart selection to ensure diversity: {selected_charts}")
        
        logger.info(f"Chart types requested by user: {original_selections}")
        logger.info(f"Final chart types to be created: {selected_charts[:4]}")
        
        # This is redundant given our earlier check, but we'll keep it for safety
        if not csv_data:
            raise ValueError("No CSV data provided")
        
        # Create a directory for the dashboard with robust error handling
        dashboard_path = os.path.join(DASHBOARD_FOLDER, dashboard_id)
        try:
            os.makedirs(dashboard_path, exist_ok=True)
            logger.info(f"Created dashboard directory: {dashboard_path}")
        except Exception as dir_error:
            logger.error(f"Error creating dashboard directory: {str(dir_error)}")
            raise ValueError(f"Could not create dashboard directory: {str(dir_error)}")
        
        # Save the CSV data to a file with robust error handling
        csv_path = os.path.join(dashboard_path, 'data.csv')
        try:
            with open(csv_path, 'w') as f:
                f.write(csv_data)
            logger.info(f"Saved CSV data to: {csv_path}")
        except Exception as csv_error:
            logger.error(f"Error saving CSV data: {str(csv_error)}")
            raise ValueError(f"Could not save CSV data: {str(csv_error)}")
        
        # Analyze the CSV data
        try:
            analysis = analyze_csv_data(csv_data)
            if not analysis or not isinstance(analysis, dict):
                raise ValueError("Invalid analysis result format")
                
            # Extract analysis results
            if 'df' not in analysis:
                raise ValueError("Analysis missing dataframe")
                
            df = analysis['df']
            numeric_cols = analysis.get('numeric_columns', [])
            categorical_cols = analysis.get('categorical_columns', [])
            
            # Validate minimum required columns
            if not numeric_cols and not categorical_cols:
                logger.warning("No usable columns detected in CSV data")
                raise ValueError("Could not detect any usable columns in your CSV. Please ensure it contains numeric or categorical data.")
                
        except Exception as analysis_error:
            logger.exception(f"CSV analysis failed: {analysis_error}")
            raise ValueError(f"Failed to analyze CSV data: {str(analysis_error)}")
        
        logger.info(f"DataFrame shape: {df.shape}")
        logger.info(f"Columns: {df.columns.tolist()}")
        logger.debug(f"Data types: {df.dtypes.to_dict()}")
        logger.info(f"Numeric columns: {numeric_cols}")
        logger.info(f"Categorical columns: {categorical_cols}")
        
        # Create a unique ID prefix for components
        chart_id_prefix = f"dashboard_{dashboard_id}"
        
        # Create dashboard components
        components = []
        
        # Enhanced debugging for chart generation
        logger.info(f"\n{'='*50}")
        logger.info(f"Dashboard ID: {dashboard_id}")
        logger.info(f"Selected chart types: {selected_charts[:4]}")
        logger.info(f"Numeric columns: {numeric_cols}")
        logger.info(f"Categorical columns: {categorical_cols}")
        logger.debug(f"Data sample:\n{df.head(2)}")
        logger.info(f"{'='*50}\n")
        
        # Use chart recommendations from analysis based on data patterns
        chart_recommendations = analysis.get('chart_recommendations', [])
        chart_configs = {}
        
        # Build a map of chart type to recommended configuration
        if chart_recommendations:
            logger.info("Using data-driven chart configurations")
            for chart_rec in chart_recommendations:
                chart_type = chart_rec.get('type')
                if chart_type and chart_rec.get('suitable', False):
                    chart_configs[chart_type] = chart_rec
                    logger.debug(f"Found suitable configuration for {chart_type}")
        else:
            logger.info("No chart recommendations found, using default configuration logic")
        
        # Add 'total_hours' to numeric columns if it exists but wasn't detected
        if 'total_hours' in df.columns and 'total_hours' not in numeric_cols:
            logger.info("Adding 'total_hours' to numeric columns")
            numeric_cols.append('total_hours')
        
        # If we still don't have numeric columns, create a count column
        if not numeric_cols:
            logger.info("No numeric columns found, creating 'count' column")
            df['count'] = 1
            numeric_cols = ['count']
        
        # Ensure we have valid chart types to create
        chart_types_to_create = []
        
        # If user explicitly selected charts, prioritize those exact selections
        if original_selections:
            # Make sure we respect the user's original chart type selections in order
            logger.info("Prioritizing user-selected chart types")
            
            # First add all user-selected chart types
            for chart_type in original_selections[:4]:
                if chart_type not in chart_types_to_create:
                    chart_types_to_create.append(chart_type)
            
            # Then fill remaining slots with diverse types
            remaining_slots = 4 - len(chart_types_to_create)
            if remaining_slots > 0:
                for chart_type in selected_charts:
                    if chart_type not in chart_types_to_create and len(chart_types_to_create) < 4:
                        chart_types_to_create.append(chart_type)
        else:
            # No user selections, use the balanced selection we created earlier
            chart_types_to_create = selected_charts[:4]
        
        logger.info(f"Final chart creation order: {chart_types_to_create}")
        
        for i, chart_type in enumerate(chart_types_to_create):
            try:
                # Generate a truly unique chart ID with type and index
                chart_id = f"{chart_id_prefix}_chart_{i}_{chart_type}_{uuid.uuid4().hex[:6]}"
                print(f"\n🔶 Creating chart [{i}]: type={chart_type}, id={chart_id}")
                
                # Check if we have data-driven recommendations for this chart type
                if chart_type in chart_configs:
                    config = chart_configs[chart_type]
                    logger.info(f"Using data-driven recommendation for {chart_type} chart")
                    
                    if chart_type == 'bar':
                        x_col = config.get('x_axis', categorical_cols[0] if categorical_cols else None)
                        y_col = config.get('y_axis', numeric_cols[0] if numeric_cols else None)
                        title = config.get('title', f"{chart_type.capitalize()} Chart")
                        
                        if x_col in df.columns and y_col in df.columns:
                            logger.info(f"Creating bar chart [{i}]: type={chart_type}, x={x_col}, y={y_col}")
                            fig = px.bar(df, x=x_col, y=y_col, title=title)
                            components.append(vm.Graph(id=chart_id, figure=fig))
                        else:
                            raise ValueError(f"Recommended columns not found in DataFrame: x={x_col}, y={y_col}")
                            
                    elif chart_type == 'line':
                        x_col = config.get('x_axis', numeric_cols[0] if numeric_cols else None)
                        y_col = config.get('y_axis', numeric_cols[1] if len(numeric_cols) > 1 else numeric_cols[0] if numeric_cols else None)
                        title = config.get('title', f"{chart_type.capitalize()} Chart")
                        
                        if x_col in df.columns and y_col in df.columns:
                            logger.info(f"Creating line chart [{i}]: type={chart_type}, x={x_col}, y={y_col}")
                            fig = px.line(df, x=x_col, y=y_col, title=title)
                            components.append(vm.Graph(id=chart_id, figure=fig))
                        else:
                            raise ValueError(f"Recommended columns not found in DataFrame: x={x_col}, y={y_col}")
                            
                    elif chart_type == 'pie':
                        names_col = config.get('labels', config.get('x_axis', categorical_cols[0] if categorical_cols else None))
                        values_col = config.get('values', config.get('y_axis', numeric_cols[0] if numeric_cols else None))
                        title = config.get('title', f"{chart_type.capitalize()} Chart")
                        
                        if names_col in df.columns and values_col in df.columns:
                            logger.info(f"Creating pie chart [{i}]: type={chart_type}, names={names_col}, values={values_col}")
                            fig = px.pie(df, names=names_col, values=values_col, title=title)
                            components.append(vm.Graph(id=chart_id, figure=fig))
                        else:
                            raise ValueError(f"Recommended columns not found in DataFrame: names={names_col}, values={values_col}")
                            
                    elif chart_type == 'scatter':
                        x_col = config.get('x_axis', numeric_cols[0] if numeric_cols else None)
                        y_col = config.get('y_axis', numeric_cols[1] if len(numeric_cols) > 1 else numeric_cols[0] if numeric_cols else None)
                        title = config.get('title', f"{chart_type.capitalize()} Chart")
                        
                        if x_col in df.columns and y_col in df.columns:
                            logger.info(f"Creating scatter plot [{i}]: type={chart_type}, x={x_col}, y={y_col}")
                            fig = px.scatter(df, x=x_col, y=y_col, title=title)
                            components.append(vm.Graph(id=chart_id, figure=fig))
                        else:
                            raise ValueError(f"Recommended columns not found in DataFrame: x={x_col}, y={y_col}")
                else:
                    # Fallback to intelligent chart creation logic based on available data
                    logger.info(f"Using optimized fallback logic for chart type: {chart_type}")
                    
                    # Create a fallback title for the chart
                    chart_title = f"{chart_type.capitalize()} Chart {i+1}"
                    
                    if chart_type == 'bar':
                        if numeric_cols and categorical_cols:
                            # Most common case: categorical for x-axis, numeric for height
                            x_col = categorical_cols[0]
                            y_col = numeric_cols[0]
                            logger.info(f"Creating bar chart [{i}]: x={x_col}, y={y_col}")
                            fig = px.bar(df, x=x_col, y=y_col, title=chart_title)
                            components.append(vm.Graph(id=chart_id, figure=fig))  
                        elif len(numeric_cols) >= 2:
                            # If we have 2+ numeric columns but no categorical, use first numeric as x
                            x_col = numeric_cols[0]
                            y_col = numeric_cols[1]
                            logger.info(f"Creating bar chart [{i}] with numeric x-axis: x={x_col}, y={y_col}")
                            fig = px.bar(df, x=x_col, y=y_col, title=chart_title)
                            components.append(vm.Graph(id=chart_id, figure=fig))
                        else:
                            logger.warning(f"Cannot create bar chart: numeric_cols={numeric_cols}, categorical_cols={categorical_cols}")
                            # Try to create a different chart type instead
                            if len(numeric_cols) >= 1 and i == 0:  # Only attempt fallback on first chart
                                logger.info(f"Falling back to histogram for numeric column: {numeric_cols[0]}")
                                fig = px.histogram(df, x=numeric_cols[0], title=f"Histogram of {numeric_cols[0]}")
                                components.append(vm.Graph(id=chart_id, figure=fig))
                    elif chart_type == 'line':
                        if len(numeric_cols) >= 2:
                            # Ideal case: 2+ numeric columns
                            x_col = numeric_cols[0]
                            y_col = numeric_cols[1]
                            logger.info(f"Creating line chart [{i}]: x={x_col}, y={y_col}")
                            fig = px.line(df, x=x_col, y=y_col, title=chart_title)
                            components.append(vm.Graph(id=chart_id, figure=fig))
                        elif numeric_cols and categorical_cols:
                            # Next best: 1 numeric, 1+ categorical
                            x_col = categorical_cols[0]
                            y_col = numeric_cols[0]
                            logger.info(f"Creating line chart [{i}] with categorical x-axis: x={x_col}, y={y_col}")
                            fig = px.line(df, x=x_col, y=y_col, title=chart_title)
                            components.append(vm.Graph(id=chart_id, figure=fig))
                        elif len(numeric_cols) == 1:
                            # Last resort: single numeric column shown against index
                            y_col = numeric_cols[0]
                            logger.info(f"Creating line chart [{i}] using index as x-axis: y={y_col}")
                            fig = px.line(df, y=y_col, title=f"Trend of {y_col}")
                            components.append(vm.Graph(id=chart_id, figure=fig))
                        else:
                            logger.warning(f"Cannot create line chart: no suitable columns")
                            
                    elif chart_type == 'pie':
                        if numeric_cols and categorical_cols:
                            # Ideal case: categorical for names, numeric for values
                            names_col = categorical_cols[0]
                            values_col = numeric_cols[0]
                            logger.info(f"Creating pie chart [{i}]: names={names_col}, values={values_col}")
                            fig = px.pie(df, names=names_col, values=values_col, title=chart_title)
                            components.append(vm.Graph(id=chart_id, figure=fig))
                        elif categorical_cols:
                            # Fallback: use value counts of categorical column
                            names_col = categorical_cols[0]
                            logger.info(f"Creating pie chart [{i}] using value counts: names={names_col}")
                            value_counts = df[names_col].value_counts()
                            fig = px.pie(values=value_counts.values, names=value_counts.index, title=f"Distribution of {names_col}")
                            components.append(vm.Graph(id=chart_id, figure=fig))
                        else:
                            logger.warning(f"Cannot create pie chart: no suitable columns")
                    
                    elif chart_type == 'scatter':
                        if len(numeric_cols) >= 2:
                            # Ideal case: 2+ numeric columns
                            x_col = numeric_cols[0]
                            y_col = numeric_cols[1]
                            
                            # Check for a potential color dimension
                            color_col = None
                            if categorical_cols:
                                color_col = categorical_cols[0]
                                
                            logger.info(f"Creating scatter plot [{i}]: x={x_col}, y={y_col}, color={color_col}")
                            if color_col:
                                fig = px.scatter(df, x=x_col, y=y_col, color=color_col, title=chart_title)
                            else:
                                fig = px.scatter(df, x=x_col, y=y_col, title=chart_title)
                            components.append(vm.Graph(id=chart_id, figure=fig))
                        elif numeric_cols and len(numeric_cols) == 1:
                            # Last resort: single numeric column shown against index
                            y_col = numeric_cols[0]
                            logger.info(f"Creating scatter plot [{i}] using index: y={y_col}")
                            fig = px.scatter(df, y=y_col, title=f"Distribution of {y_col}")
                            components.append(vm.Graph(id=chart_id, figure=fig))
                        else:
                            logger.warning(f"Cannot create scatter chart: no suitable columns")
                            # Try a different visualization if scatter isn't possible
                            if categorical_cols:
                                names_col = categorical_cols[0]
                                logger.info(f"Falling back to bar count for categorical column: {names_col}")
                                fig = px.histogram(df, x=names_col, title=f"Counts of {names_col}")
                                components.append(vm.Graph(id=chart_id, figure=fig))
            except Exception as chart_error:
                logger.error(f"Error creating chart {i}: {str(chart_error)}")
                logger.exception("Chart creation exception details:")
                
                # Attempt to create a fallback chart with whatever data we have
                if not components and i == len(chart_types_to_create) - 1:  # Last chart and no components yet
                    logger.warning("Critical: No successful charts created, adding fallback chart")
                    try:
                        if numeric_cols:
                            # Create a simple histogram of first numeric column
                            fallback_col = numeric_cols[0]
                            fig = px.histogram(
                                df, 
                                x=fallback_col, 
                                title=f"Fallback Chart: Distribution of {fallback_col}",
                                labels={fallback_col: fallback_col.replace('_', ' ').title()}
                            )
                            components.append(vm.Graph(id=f"{chart_id_prefix}_fallback", figure=fig))
                            logger.info(f"Created fallback histogram chart with column: {fallback_col}")
                        elif categorical_cols:
                            # Create a count plot of first categorical
                            fallback_col = categorical_cols[0]
                            value_counts = df[fallback_col].value_counts()
                            fig = px.bar(
                                x=value_counts.index, 
                                y=value_counts.values,
                                title=f"Fallback Chart: Counts of {fallback_col}",
                                labels={'x': fallback_col.replace('_', ' ').title(), 'y': 'Count'}
                            )
                            components.append(vm.Graph(id=f"{chart_id_prefix}_fallback", figure=fig))
                            logger.info(f"Created fallback bar chart with categorical column: {fallback_col}")
                    except Exception as fallback_error:
                        logger.error(f"Even fallback chart failed: {str(fallback_error)}")
                        logger.exception("Fallback chart exception details:")
                    

        try:
            logger.info(f"Creating Vizro dashboard with {len(components)} components")
            dashboard = vm.Dashboard(
                title="AI Dashboard",
                pages=[vm.Page(id="main_page", title="Dashboard", components=components)]
            )
            logger.info("Successfully created Vizro dashboard object")
        except Exception as dashboard_error:
            logger.exception(f"Failed to create Vizro dashboard object: {str(dashboard_error)}")
            raise ValueError(f"Failed to create dashboard: {str(dashboard_error)}")
        
        # Save dashboard configuration to file for persistence with robust error handling
        dashboard_config = {
            'title': 'AI Dashboard',
            'charts': [{'type': chart_type} for chart_type in selected_charts[:4]],
            'data_path': csv_path
        }
        
        config_path = os.path.join(dashboard_path, 'config.json')
        try:
            with open(config_path, 'w') as f:
                json.dump(dashboard_config, f)
            logger.info(f"Saved dashboard configuration to: {config_path}")
        except Exception as config_error:
            logger.error(f"Error saving configuration: {str(config_error)}")
            # This is not fatal, we can continue with in-memory dashboard
        
        return {
            'success': True,
            'dashboard_id': dashboard_id,
            'dashboard': dashboard
        }
    except Exception as e:
        logger.error(f"Error creating dashboard: {str(e)}")
        logger.exception("Exception details:")
        return {
            'success': False,
            'error': str(e)
        }

# Store active dashboards in memory
active_dashboards = {}

def get_dashboard(dashboard_id):
    """Retrieve a dashboard by ID"""
    # Check if dashboard exists in memory
    if dashboard_id in active_dashboards:
        return active_dashboards[dashboard_id]
    
    # Otherwise try to load it from storage
    dashboard_path = os.path.join(DASHBOARD_FOLDER, dashboard_id)
    config_path = os.path.join(dashboard_path, 'config.json')
    
    if not os.path.exists(config_path):
        logger.error(f"Config path does not exist: {config_path}")
        return None
    
    try:
        # Load configuration
        import json
        with open(config_path, 'r') as f:
            config = json.load(f)
        
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
                'charts': chart_types
            }, dashboard_id)
            
            if result.get('success'):
                # Cache the dashboard
                active_dashboards[dashboard_id] = result['dashboard']
                return result['dashboard']
            else:
                logger.error(f"Failed to recreate dashboard: {result.get('error')}")
                return None
        except Exception as file_err:
            logger.error(f"Error reading data file {data_path}: {file_err}")
            return None
    except Exception as e:
        logger.error(f"Error loading dashboard {dashboard_id}: {str(e)}")
        logger.exception("Dashboard loading exception details:")
        return None
