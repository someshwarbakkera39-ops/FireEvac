"""
Production WSGI Entrypoint for Block A Digital Twin System
Suitable for Gunicorn, Waitress, or Cloud PaaS deployments (Render, AWS, Heroku)
"""

from app import app

if __name__ == "__main__":
    app.run()

