from flask import Flask
import threading

app = Flask(__name__)

@app.route('/')
def home():
    return "Lucky Bot is alive!", 200

def run():
    app.run(host="0.0.0.0", port=8080, debug=False)

def keep_alive():
    """Start Flask server in background thread"""
    thread = threading.Thread(target=run)
    thread.daemon = True
    thread.start()
