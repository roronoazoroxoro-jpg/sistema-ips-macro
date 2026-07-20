import os

from waitress import serve

from app import app
from database import init_db


if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", "5000"))
    serve(app, host="0.0.0.0", port=port)
