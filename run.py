from flask import Flask
from flask_migrate import Migrate
from app import create_app, db
import os
import sys
import logging
import argparse

app = create_app()
migrate = Migrate(app, db)

if __name__ == "__main__":
    # Set logging level to DEBUG
    logging.basicConfig(level=logging.DEBUG)

    parser = argparse.ArgumentParser(description='Run the Flask app.')
    parser.add_argument('--port', type=int, default=int(os.getenv("FLASK_RUN_PORT", "5000")),
                        help='The port to run the app on.')
    args = parser.parse_args()

    # lightweight CLI passthrough for Flask-Migrate
    if len(sys.argv) > 1 and sys.argv[1] == "db":
        from flask.cli import main as flask_main
        os.environ.setdefault("FLASK_APP", "run.py")
        flask_main()
    else:
        host = os.getenv("FLASK_RUN_HOST", "127.0.0.1")
        app.run(host=host, port=args.port, debug=os.getenv("FLASK_ENV") == "development")
