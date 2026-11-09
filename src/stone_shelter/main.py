"""Expose the assembled FastAPI application to Uvicorn."""

from stone_shelter.app import create_app

app = create_app()
