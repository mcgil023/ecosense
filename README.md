# EcoSense — What it does and what it's useful for

What it does:
- Collects telemetry from ESP32 sensors (soil moisture, temperature, humidity, light) via a simple POST endpoint (/esp32).
- Fetches external weather data and correlates it with local sensor readings.
- Stores live and historical readings and exposes a live view at /live.
- Runs a lightweight AI ruleset to provide basic recommendations (irrigation suggestions, alerting for out-of-range readings).
- Provides a web dashboard for visualization and quick decision-making.

Why it's useful:
- Small farms and greenhouses get real-time visibility into key environmental metrics.
- Combines on-site sensor data with weather forecasts to avoid overwatering and reduce resource waste.
- Historical trends help identify recurring issues and optimize planting schedules.
- Low-cost ESP32 integration makes deployment affordable and extensible for hobbyists and small producers.

Quick start (local):
1. Install dependencies: `pip install -r requirements.txt`
2. Run locally: `python app.py`
3. Open dashboard: `http://localhost:5000`

Deploy to Render.com:
1. Push the repo to GitHub and create a new Web Service on render.com.
2. Build command: `pip install -r requirements.txt`
3. Start command: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --timeout 120`
4. Configure environment variables: `GEMINI_API_KEY`, `WEATHER_API_KEY`, `WEATHER_CITY` (if used).

ESP32 integration:
- POST sensor JSON to `/esp32` (example payload: `{ "device_id": "esp1", "soil_moisture": 42, "temp_c": 24.5, "humidity": 60, "light": 300 }`).
- View live feed at `/live`.

Notes:
- This project is intended as a simple, extensible starting point for small-scale smart farming. Contributions welcome.
