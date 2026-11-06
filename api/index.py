"""
Vercel Serverless Function Entry Point for Block A Digital Twin System
Directs incoming HTTP requests to the core Flask application.
"""

import os
import sys

# Ensure project root is at the head of sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# Import Flask WSGI application instance
from app import app

