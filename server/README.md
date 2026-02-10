How to download packages for server
Makes the assumption your virtuan environment is called venv:
Run the following commands in terminal:

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload --port 8000

Then open:

http://127.0.0.1:8000/health
http://127.0.0.1:8000/docs

Both should load
