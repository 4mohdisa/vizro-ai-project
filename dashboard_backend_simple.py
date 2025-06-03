import os
import uuid
import pandas as pd
import plotly.express as px
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from vizro_ai import VizroAI
from vizro import Vizro
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Configure CORS to allow requests from any origin with all necessary headers
CORS(app, resources={r"/*": {"origins": "*", "allow_headers": "*", "methods": "*"}}, supports_credentials=True)

# Add explicit CORS headers to all responses
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,X-Requested-With')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    return response

# Directory for storing uploaded files and generated dashboards
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
DASHBOARD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dashboards')

# Create directories if they don't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DASHBOARD_FOLDER, exist_ok=True)


# Function to analyze CSV data
def analyze_csv_data(csv_path):
    """Analyze CSV data to determine column types and suggest visualizations"""
    try:
        # Read the CSV file
        df = pd.read_csv(csv_path)
        
        # Identify column types
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        
        # New block after reading the CSV
        if 'Total Time Worked' in df.columns:
            def convert_time_to_float(s):
                import re
                hours = re.search(r'(\d+)\s*hour', s)
                minutes = re.search(r'(\d+)\s*minute', s)
                h = int(hours.group(1)) if hours else 0
                m = int(minutes.group(1)) if minutes else 0
                return round(h + m / 60.0, 2)
            
            df['total_hours'] = df['Total Time Worked'].apply(convert_time_to_float)
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
        
        # Create chart recommendations
        chart_recommendations = {}
        
        # Bar chart recommendation
        if categorical_cols and numeric_cols:
            chart_recommendations['bar'] = {
                'x': categorical_cols[0],
                'y': numeric_cols[0],
                'title': f"{numeric_cols[0]} by {categorical_cols[0]}"
            }
        
        # Line chart recommendation
        if date_cols and numeric_cols:
            chart_recommendations['line'] = {
                'x': date_cols[0],
                'y': numeric_cols[0],
                'title': f"{numeric_cols[0]} over Time"
            }
        elif categorical_cols and numeric_cols:
            chart_recommendations['line'] = {
                'x': categorical_cols[0],
                'y': numeric_cols[0],
                'title': f"{numeric_cols[0]} Trend"
            }
        
        # Pie chart recommendation
        if categorical_cols and numeric_cols:
            chart_recommendations['pie'] = {
                'names': categorical_cols[0],
                'values': numeric_cols[0],
                'title': f"Distribution of {numeric_cols[0]} by {categorical_cols[0]}"
            }
        
        # Scatter plot recommendation
        if len(numeric_cols) >= 2:
            chart_recommendations['scatter'] = {
                'x': numeric_cols[0],
                'y': numeric_cols[1],
                'title': f"Relationship between {numeric_cols[0]} and {numeric_cols[1]}"
            }
        
        analysis = {
            "df": df,
            "numeric_columns": numeric_cols,
            "categorical_columns": categorical_cols,
            "date_columns": date_cols,
            "chart_recommendations": chart_recommendations
        }
        
        return analysis
    except Exception as e:
        return None

# Route for the home page
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

# Route for dashboard information
@app.route('/dashboard-info')
def dashboard_info():
    dashboard_id = request.args.get('id')
    if not dashboard_id:
        return jsonify({'error': 'No dashboard ID provided'}), 400
    
    dashboard_path = os.path.join(DASHBOARD_FOLDER, dashboard_id)
    if not os.path.exists(dashboard_path):
        return jsonify({'error': 'Dashboard not found'}), 404
    
    # Get the port for this dashboard
    dashboard_port = 8090 + (int(dashboard_id, 16) % 100)
    
    return jsonify({
        'id': dashboard_id,
        'url': f"http://127.0.0.1:{dashboard_port}",
        'message': 'Dashboard information retrieved successfully'
    })

# Keep the original dashboard route for backward compatibility
@app.route('/dashboard')
def serve_dashboard():
    dashboard_id = request.args.get('id')
    if not dashboard_id:
        return jsonify({'error': 'No dashboard ID provided'}), 400
    
    # Redirect to dashboard-info to get the Vizro dashboard URL
    return dashboard_info()

# Route for uploading CSV data
@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file:
        # Generate a unique ID for this upload
        upload_id = uuid.uuid4().hex
        
        # Save the file
        file_path = os.path.join(UPLOAD_FOLDER, f"{upload_id}.csv")
        file.save(file_path)
        
        # Analyze the CSV data
        analysis = analyze_csv_data(file_path)
        
        if analysis:
            return jsonify({
                'id': upload_id,
                'message': 'File uploaded and analyzed successfully',
                'analysis': {
                    'numeric_columns': analysis['numeric_columns'],
                    'categorical_columns': analysis['categorical_columns'],
                    'date_columns': analysis['date_columns'],
                    'chart_recommendations': analysis['chart_recommendations']
                }
            })
        else:
            return jsonify({'error': 'Error analyzing CSV data'}), 500
    
    return jsonify({'error': 'Error uploading file'}), 500

# Route for generating a dashboard
# Import all necessary modules at the global scope
import sys
import json
import time
import threading
import subprocess
import signal

@app.route('/generate', methods=['POST'])
def generate():
    try:
        print("Generate endpoint called")
        data = request.json
        print(f"Received data: {data.keys() if data else None}")
        
        # Extract data from the request
        charts = data.get('charts', [])
        layout = data.get('layout', 'grid')
        columns = data.get('columns', 2)
        csv_data = data.get('data', '')
        
        if not csv_data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Generate a unique ID for this dashboard
        dashboard_id = uuid.uuid4().hex
        
        # Create a directory for this dashboard
        dashboard_path = os.path.join(DASHBOARD_FOLDER, dashboard_id)
        os.makedirs(dashboard_path, exist_ok=True)
        
        # Save the CSV data to a file
        csv_path = os.path.join(dashboard_path, "data.csv")
        with open(csv_path, 'w') as f:
            f.write(csv_data)
        
        # Analyze the data
        analysis = analyze_csv_data(csv_path)
        if not analysis:
            return jsonify({'error': 'Error analyzing CSV data'}), 500
        
        # Extract analysis results
        df = analysis['df']
        numeric_cols = analysis['numeric_columns']
        categorical_cols = analysis['categorical_columns']
        date_cols = analysis['date_columns']
        chart_recommendations = analysis['chart_recommendations']
        
        # Print debug information
        print(f"Selected charts: {charts}")
        
        # Create Vizro dashboard
        dashboard = create_vizro_dashboard(df, charts)
        
        # Save the dashboard configuration
        os.makedirs(dashboard_path, exist_ok=True)
        
        # Start the Vizro dashboard on a specific port
        dashboard_port = 8090 + (int(dashboard_id, 16) % 100)  # Use a port based on dashboard ID
        
        # Return the dashboard URL
        dashboard_url = f"http://127.0.0.1:{dashboard_port}"
        
        # Launch the dashboard using a standalone script in a separate process
        
        # Kill any existing process on the dashboard port
        try:
            kill_cmd = f"lsof -ti:{dashboard_port} | xargs kill -9"
            subprocess.run(kill_cmd, shell=True, stderr=subprocess.PIPE)
            print(f"Killed any existing process on port {dashboard_port}")
        except Exception as e:
            print(f"Note: No process to kill on port {dashboard_port}: {str(e)}")
        
        # Create a configuration file for the dashboard
        config = {
            "title": "AI Dashboard",
            "data_path": os.path.join(dashboard_path, "data.csv"),
            "charts": []
        }
        
        # Add chart configurations
        for i, chart_type in enumerate(charts[:4]):
            config["charts"].append({
                "id": f"chart_{i}_{dashboard_id[:8]}",  # Use part of dashboard ID for uniqueness
                "type": chart_type
            })
        
        # Save the configuration
        config_path = os.path.join(dashboard_path, "dashboard_config.json")
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"\n==== DASHBOARD DEBUG INFO ====")
        print(f"Dashboard ID: {dashboard_id}")
        print(f"Dashboard Port: {dashboard_port}")
        print(f"Dashboard URL: {dashboard_url}")
        print(f"Dashboard Config: {config_path}")
        print(f"Dashboard Data: {os.path.join(dashboard_path, 'data.csv')}")
        print(f"==== END DEBUG INFO ====\n")
        
        # Launch the dashboard in a separate process
        try:
            # Make the script executable
            subprocess.run(["chmod", "+x", "run_dashboard.py"])
            
            # Launch the dashboard process
            dashboard_cmd = [sys.executable, "run_dashboard.py", config_path, str(dashboard_port)]
            print(f"Launching dashboard with command: {' '.join(dashboard_cmd)}")
            
            # Use Popen to run in background and show output directly in terminal for debugging
            process = subprocess.Popen(
                dashboard_cmd
                # Output streams not piped so they appear directly in terminal
            )
            
            # Store the process ID in a file for later cleanup
            with open(os.path.join(dashboard_path, "process.pid"), 'w') as f:
                f.write(str(process.pid))
            
            print(f"Started dashboard process with PID {process.pid}")
            
            # Wait a moment to see if the process crashes immediately
            time.sleep(1)
            if process.poll() is not None:
                # Process already exited
                stdout, stderr = process.communicate()
                print(f"Dashboard process exited immediately with code {process.returncode}")
                print(f"STDOUT: {stdout}")
                print(f"STDERR: {stderr}")
                raise Exception(f"Dashboard process failed to start: {stderr}")
            
            # Store the process for later cleanup
            if not hasattr(app, 'dashboard_processes'):
                app.dashboard_processes = {}
            app.dashboard_processes[dashboard_port] = process
            
        except Exception as e:
            print(f"Error launching dashboard: {str(e)}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': f'Failed to start dashboard: {str(e)}'}), 500
        
        # Wait a moment for the dashboard to start
        time.sleep(3)  # Give it a bit more time to ensure the server is up
        
        return jsonify({
            'id': dashboard_id,
            'url': dashboard_url,
            'port': dashboard_port,
            'charts': charts
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error in generate endpoint: {str(e)}")
        return jsonify({'error': f'Error generating dashboard: {str(e)}'}), 500

def create_vizro_dashboard(df, selected_charts):
    """Create a dashboard using Vizro AI"""
    try:
        # Make sure we have the OpenAI API key
        openai_api_key = os.environ.get("OPENAI_API_KEY")
        if not openai_api_key:
            raise Exception("OPENAI_API_KEY environment variable is not set. Please create a .env file with your API key.")
        
        # The API key is loaded from environment variables by the VizroAI class
        # No need to pass it explicitly - it will use OPENAI_API_KEY from the environment
        vizro_ai = VizroAI(model="gpt-4o")
        
        # Create a prompt based on selected charts
        
        # Reset Vizro before manual creation
        try:
            from vizro import Vizro
            Vizro._reset()
        except Exception:
            pass
            
        # Create charts based on selected chart types
        components = []
        chart_id_prefix = uuid.uuid4().hex[:8]  # Generate unique prefix for chart IDs
        
        # Print data info for debugging
        print(f"DataFrame shape: {df.shape}")
        print(f"DataFrame columns: {df.columns.tolist()}")
        print(f"DataFrame dtypes:\n{df.dtypes}")
        
        # Check for numeric and categorical columns
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
        
        print(f"Numeric columns: {numeric_cols}")
        print(f"Categorical columns: {categorical_cols}")
        
        # If we have 'total_hours' from time conversion, make sure it's used
        if 'total_hours' in df.columns and 'total_hours' not in numeric_cols:
            print("Adding 'total_hours' to numeric columns")
            numeric_cols.append('total_hours')
        
        # If we still don't have numeric columns, create a count column
        if not numeric_cols:
            print("No numeric columns found, creating 'count' column")
            df['count'] = 1
            numeric_cols = ['count']
        
        for i, chart_type in enumerate(selected_charts[:4]):
            try:
                chart_id = f"{chart_id_prefix}_chart_{i}"  # Ensure unique IDs
                
                if chart_type == 'bar':
                    # Find a numeric column and a categorical column
                    if numeric_cols and categorical_cols:
                        print(f"✅ Creating bar chart with x={categorical_cols[0]}, y={numeric_cols[0]}")
                        fig = px.bar(df, x=categorical_cols[0], y=numeric_cols[0])
                        components.append(vm.Graph(id=chart_id, figure=fig))
                    else:
                        print(f"⚠️ Cannot create bar chart: numeric_cols={numeric_cols}, categorical_cols={categorical_cols}")
                elif chart_type == 'line':
                    if len(numeric_cols) >= 2:
                        print(f"✅ Creating line chart with x={numeric_cols[0]}, y={numeric_cols[1]}")
                        fig = px.line(df, x=numeric_cols[0], y=numeric_cols[1])
                        components.append(vm.Graph(id=chart_id, figure=fig))
                    elif numeric_cols and categorical_cols:
                        print(f"✅ Creating line chart with x={categorical_cols[0]}, y={numeric_cols[0]}")
                        fig = px.line(df, x=categorical_cols[0], y=numeric_cols[0])
                        components.append(vm.Graph(id=chart_id, figure=fig))
                    else:
                        print(f"⚠️ Cannot create line chart: numeric_cols={numeric_cols}, categorical_cols={categorical_cols}")
                elif chart_type == 'pie':
                    if numeric_cols and categorical_cols:
                        print(f"✅ Creating pie chart with names={categorical_cols[0]}, values={numeric_cols[0]}")
                        fig = px.pie(df, names=categorical_cols[0], values=numeric_cols[0])
                        components.append(vm.Graph(id=chart_id, figure=fig))
                    else:
                        print(f"⚠️ Cannot create pie chart: numeric_cols={numeric_cols}, categorical_cols={categorical_cols}")
                elif chart_type == 'scatter':
                    if len(numeric_cols) >= 2:
                        print(f"✅ Creating scatter plot with x={numeric_cols[0]}, y={numeric_cols[1]}")
                        fig = px.scatter(df, x=numeric_cols[0], y=numeric_cols[1])
                        components.append(vm.Graph(id=chart_id, figure=fig))
                    else:
                        print(f"⚠️ Cannot create scatter plot: numeric_cols={numeric_cols}")
            except Exception as chart_error:
                print(f"❌ Error creating {chart_type} chart: {str(chart_error)}")
                import traceback
                traceback.print_exc()

        # Create a dashboard with the components
        if not components:
            raise Exception("No valid charts could be created from the dataset. Please check that your data has at least one numeric and one categorical column.")

        dashboard = vm.Dashboard(
            title="AI Dashboard",
            pages=[vm.Page(id="main_page", title="Dashboard", components=components)]
        )
        
        return dashboard
    except Exception as e:
        # Log the error and raise it for handling in the calling function
        import traceback
        traceback.print_exc()
        raise Exception(f"Error creating Vizro dashboard: {str(e)}")


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=True)
