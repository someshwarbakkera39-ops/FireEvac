"""
Configuration settings for Block A Digital Twin System
"""

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "block-a-production-secret-key-2026")
    DATA_PATH = os.path.join(BASE_DIR, "static", "data", "building_model.json")
    DB_PATH = os.path.join(BASE_DIR, "database", "digital_twin.db")
    DEBUG = False
    TESTING = False

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

class TestingConfig(Config):
    TESTING = True
    DEBUG = True

config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig
}

