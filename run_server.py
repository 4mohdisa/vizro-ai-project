#!/usr/bin/env python3
"""
Launcher script for the Vizro AI Dashboard Builder
"""

import os
import sys
import uvicorn

# Add the backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

# Default port (can be overridden by environment variable)
PORT = int(os.environ.get('PORT', 8082))

if __name__ == "__main__":
    print(f"🚀 Starting Vizro AI Dashboard Builder at http://127.0.0.1:{PORT}")
    uvicorn.run("backend.main:app", host="0.0.0.0", port=PORT, reload=True)
