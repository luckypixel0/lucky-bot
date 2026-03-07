from flask import Flask
import threading

app = Flask(__name__)

@app.route('/')
def home():
    return "Lucky Bot is alive!", 200

def run():
    """Run Gunicorn server"""
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    
    # Use Gunicorn instead of Flask dev server
    from gunicorn.app.base import BaseApplication
    
    class StandaloneApplication(BaseApplication):
        def __init__(self, app, options=None):
            self.application = app
            self.options = options or {}
            super().__init__()
        
        def load_config(self):
            for key, value in self.options.items():
                self.cfg.set(key.lower(), value)
        
        def load(self):
            return self.application
    
    options = {
        'bind': '0.0.0.0:8080',
        'workers': 1,
        'worker_class': 'sync',
        'timeout': 60,
    }
    
    StandaloneApplication(app, options).run()

def keep_alive():
    """Start server in background thread"""
    thread = threading.Thread(target=run)
    thread.daemon = True
    thread.start()
