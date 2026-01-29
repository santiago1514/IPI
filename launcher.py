import subprocess
import sys
import os
import webbrowser
import time

BASE_DIR = os.path.dirname(sys.executable)

streamlit_cmd = [
    sys.executable,
    "-m",
    "streamlit",
    "run",
    os.path.join(BASE_DIR, "main2.py"),
    "--server.headless=true"
]

subprocess.Popen(streamlit_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

time.sleep(3)
webbrowser.open("http://localhost:8501")
