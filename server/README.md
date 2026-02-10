How to download packages for server
Run the following commands in terminal (from the server folder):

Important: run this command only the first time
python3 -m venv .venv

Then:
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload --port 8000

Then open:

http://127.0.0.1:8000/health
http://127.0.0.1:8000/docs

Both should load
