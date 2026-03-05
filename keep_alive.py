from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Lucky Bot is alive! 🤖✨"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()
```

**C) Create `requirements.txt`:**
- Tap "New File" → name it `requirements.txt`
- Paste this:
```
discord.py==2.3.2
flask==3.0.0
yt-dlp==2024.1.0
PyNaCl==1.5.0
aiohttp==3.9.1
Pillow==10.2.0
requests==2.31.0
wavelink==3.2.0
