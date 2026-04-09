# EcoSense — AI Smart Farming Dashboard

## Files to copy into your ecosense folder
Place all files from this zip into your existing ecosense folder.
Keep your existing: crop_config.json, all .pkl encoder/model files.

## Deploy to Render.com
1. Push full folder to GitHub (private repo)
2. render.com → New Web Service → connect repo
3. Build: `pip install -r requirements.txt`
4. Start: `gunicorn app:app`
5. Add env var: GEMINI_API_KEY = your key

## Local run
python app.py → open http://localhost:5000
