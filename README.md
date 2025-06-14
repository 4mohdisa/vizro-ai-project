# Vizro AI Dashboard Builder

A modern web application that allows users to upload CSV data and generate interactive dashboards with AI assistance.

## Project Structure

```
/backend
  ├── main.py               # FastAPI application
  ├── dashboard_utils.py    # Dashboard generation utilities
  └── static/               # Static HTML/CSS/JS files
```

## Features

- Upload CSV data and automatically analyze columns
- Select from different chart types (bar, line, pie, scatter)
- Automatic conversion of time formats (e.g., "8 hours 45 minutes") to numeric values
- Grid layout dashboard generation
- Interactive dashboard viewing with plotly.js

## Installation

1. Install the required dependencies:

```bash
pip install -r requirements.txt
```

2. Make sure you have the environment variables set up (optional):

```
OPENAI_API_KEY=your_api_key_here  # if you want to enable Vizro AI features
```

## Running the Application

Start the FastAPI server:

```bash
cd backend
uvicorn main:app --reload --port 8080
```

Then open your browser and navigate to:
```
http://127.0.0.1:8080
```

## Usage

1. Upload a CSV file
2. Select chart types (up to 4)
3. Click "Generate Dashboard"
4. View the generated dashboard in a new tab

## Technology Stack

- **Backend**: FastAPI + Uvicorn
- **Data Processing**: Pandas
- **Visualization**: Vizro + Plotly
- **Frontend**: HTML, CSS (Tailwind), JavaScript

## Upgrading from the Previous Version

This application replaces the previous Flask-based implementation with a more efficient FastAPI architecture. Key improvements:

1. Eliminated the need for separate dashboard server processes
2. Improved performance with async request handling
3. Better error reporting and feedback
4. Direct dashboard rendering in the main application

## Known Limitations

- Currently supports up to 4 charts per dashboard
- Dashboard settings are fixed to a 2-column grid layout
- Some complex CSV data types may require manual preprocessing
