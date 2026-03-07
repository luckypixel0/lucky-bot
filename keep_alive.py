from flask import Flask
from threading import Thread

app = Flask(__name__)


@app.get("/")
def healthcheck():
    return "Lucky Bot is alive! 🍀"


def run():
    app.run(host="0.0.0.0", port=8080, debug=False)


def keep_alive():
    thread = Thread(target=run, daemon=True)
    thread.start()
