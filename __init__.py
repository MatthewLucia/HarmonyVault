"""
app.py

This module contains the create_app function, which initializes and configures the Flask application.
It sets up configuration settings and registers blueprints for different components of the application.

Author: Matt Lucia
Date: 01/30/2024
"""

# Import necessary modules from Flask
from flask import Flask
import sqlite3

# Function to create the Flask application
def create_app():
    # Initialize the Flask app
    app = Flask(__name__)

    # Configuration settings for the app
    app.config['SECRET_KEY'] = '&jL82hB%#h@k!9l!h'

    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SESSION_PERMANENT'] = True
    app.config['SESSION_USE_SIGNER'] = True

    # Import and register blueprints (views and auth) from respective modules
    from .views import views
    from .auth import auth
    app.register_blueprint(views, url_prefix='/views')
    app.register_blueprint(auth, url_prefix='/auth')

    # Return the configured Flask app
    return app
