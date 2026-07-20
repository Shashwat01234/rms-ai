# app.py — Entry point alias for Gunicorn / Render
from server import app

if __name__ == "__main__":
    app.run()
