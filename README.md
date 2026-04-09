# EcoSense — AI Smart Farming Dashboard

## Deploy to Render.com
1. Push full folder to GitHub
2. render.com → New Web Service → connect repo
3. Build: `pip install -r requirements.txt`
4. Start: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --timeout 120`
5. Add env vars: GEMINI_API_KEY, WEATHER_API_KEY, WEATHER_CITY

## Local run
python app.py → open http://localhost:5000

## ESP32
POST JSON to: https://your-app.onrender.com/esp32
Check live data: https://your-app.onrender.com/live
