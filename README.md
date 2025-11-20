# PM Accelerator Weather APIThis is a FastAPI application designed to fetch current and historical weather data.
It uses SQLModel (a combination of SQLAlchemy and Pydantic) to store a history of requests and aggregated forecast data in a local SQLite database (weather.db).
# 🚀 Quick StartTo run this API
-you need Python 3.9+ and the required packages.
-Install dependencies (from requirements.txt):pip install -r requirements.txt
-Run the application using Uvicorn:uvicorn app:app --reload
The database file (weather.db) and tables will be created automatically on startup.
The API documentation (Swagger UI) will be available at http://127.0.0.1:8000/docs.
# 📍 Key Features & EndpointsThe API offers two main types of weather functionality: real-time and historical.
1. Current Weather (Real-Time)Endpoint: POST /current_weather: Fetches the most recent weather conditions for a location.Input: Requires a location query (e.g., city name, coordinates, or zip code).
2. Historical Weather & Request ManagementThis functionality stores and manages records of past weather inquiries in the database.
-PathDescriptionPOST /weather_historyRequests and saves historical weather data for a given location and date range (YYYY-MM-DD).
-GET /historyLists all the stored historical weather requests.GET /history/{request_id}Retrieves the full details of a single, specific historical request.PUT /update_note/{request_id}Adds or changes a descriptive note on a stored request record.
-GET /export_json/{request_id}Downloads a stored request record as a JSON file.GET /trip_planning/{request_id}Provides placeholder YouTube search links for the location based on a stored request.