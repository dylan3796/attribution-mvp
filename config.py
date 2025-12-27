"""Configuration management using environment variables."""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Database configuration
DB_PATH = os.getenv("DB_PATH", "attribution.db")

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "attribution.log")

# OpenAI API configuration (optional)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
