from database import create_db_and_tables, get_session, WeatherRequest
from fastapi import FastAPI, Depends, HTTPException, status
from utils import get_data, validate_date_range
from fastapi.responses import JSONResponse
from utils import extract_forecast_list
from sqlmodel import Session, select
from datetime import date, datetime 
from pydantic import BaseModel
from typing import Optional
from math import ceil
import requests
import json

app = FastAPI()

@app.on_event("startup")
def on_startup():
    create_db_and_tables()

# --- Pydantic Models ---

class OneLocationRequest(BaseModel):
    Location: Optional[str] = None

class LocationRequest(BaseModel):
    Location: Optional[str] = None
    Latitude: Optional[float] = None 
    Longitude: Optional[float] = None
    zipcode: Optional[str] = None

class HistoryRequest(LocationRequest):
    start_date: str 
    end_date: str 

class WeatherUpdateRequest(BaseModel):
    location_query: Optional[str] = None
    date_range_start: Optional[str] = None
    date_range_end: Optional[str] = None
    note: Optional[str] = None 

# --- Endpoints ---

@app.get("/")
async def root():
    """Returns basic information and assessment metadata."""
    return {
        "message": "Welcome to the PM Accelerator Weather API!",
        "developer": "Ilias Baher", 
        "info_button_description": """Hiring and getting hired for product management roles is hard. In the short timeframe of an interview, it is difficult to precisely assess and display the necessary, complex skills.
                                        Product Managers play key roles in a company. Hiring for those positions shouldn‘t be a guessing game.
                                        It is our vision, to make it simple and beneficial for Product Managers to accurately display their skills and empower hiring companies to choose the right Product Manager every time"""}

@app.post("/weather")
async def get_current_weather(location: OneLocationRequest):
    """Retrieves current weather data for a single location."""
    url = "https://weather-api167.p.rapidapi.com/api/weather/current"
    querystring = {"place":location.Location,"units":"standard","lang":"en","mode":"json"}

    headers = {
    'x-rapidapi-key': "294c57f699msh585515beaf6c5bep16c206jsn335d557e1b4f",
    'x-rapidapi-host': "weather-api167.p.rapidapi.com",
    'Accept': "application/json"
}

    response = requests.get(url, headers=headers, params=querystring)
    if response.status_code != 200:
        return {"error": "API request failed", "status_code": response.status_code, "detail": response.text}
    
    json_response = response.json()
    weather_data = get_data(json_response)
    return [
        weather_data.get("description"),
        f"Current Temp: {weather_data.get('temperature_current')} °C",
        f"Min Temp: {weather_data.get('temperature_min')} °C",
        f"Max Temp: {weather_data.get('temperature_max')} °C",
        f"Humidity: {weather_data.get('humidity')} %",
        f"Wind Speed: {weather_data.get('wind_speed')} m/s",
        f"Rain: {weather_data.get('rain')} mm" ,
        f"Snow: {weather_data.get('snow')} mm",
        f"Sunrise: {weather_data.get('sunrise')}",
        f"Sunset: {weather_data.get('sunset')}"
    ]

kelven=273.15
@app.post("/forecast")
async def get_forecast(location: LocationRequest):
    """Retrieves the 5-day forecast for a location."""
    url = "https://weather-api167.p.rapidapi.com/api/weather/forecast"

    querystring = {"lon":location.Longitude,"lat":location.Latitude,"place":location.Location,
                   "zip":location.zipcode,"cnt":"40","units":"standard","type":"three_hour","mode":"json","lang":"en"}

    headers = {
    'x-rapidapi-key': "294c57f699msh585515beaf6c5bep16c206jsn335d557e1b4f",
    'x-rapidapi-host': "weather-api167.p.rapidapi.com",
    'Accept': "application/json"
}

    response = requests.get(url, headers=headers, params=querystring)
    if response.status_code != 200:
        return {"error": "API request failed", "status_code": response.status_code, "detail": response.text}
    
    result=response.json()
    forecast_list = []
    for i in range (len(result.get("list"))):
        timestamp_value = result.get("list")[i].get("dt") 
        date_time_obj = datetime.fromtimestamp(timestamp_value)
        formatted_date = date_time_obj.strftime("%d-%m-%Y-%H")
        forecast_list.append([formatted_date,
            ceil(result.get("list")[i].get("main").get("temprature_min")-273.15),
            ceil(result.get("list")[i].get("main").get("temprature_max")-273.15),
            result.get("list")[i].get("weather")[0].get("main")]
            )
    return forecast_list

# --- CRUD Operations ---

@app.post("/create_request", status_code=status.HTTP_201_CREATED)
async def create_request(
    request: HistoryRequest, 
    session: Session = Depends(get_session)
):
    """CREATE: Fetches a forecast, aggregates data, and saves the record to the database."""
    if not (request.Location or request.Latitude and request.Longitude or request.zipcode):
        raise HTTPException(
            status_code=400, 
            detail="Must provide location name, coordinates, or zip code."
        )
    
    # Validation and Date Conversion
    start_dt, end_dt = validate_date_range(request.start_date, request.end_date)
    url = "https://weather-api167.p.rapidapi.com/api/weather/forecast"
    headers = {
    'x-rapidapi-key': "294c57f699msh585515beaf6c5bep16c206jsn335d557e1b4f",
    'x-rapidapi-host': "weather-api167.p.rapidapi.com",
    'Accept': "application/json"
}
    querystring = {"lon":request.Longitude,"lat":request.Latitude,"place":request.Location,
                       "zip":request.zipcode,"cnt":"40","units":"standard","type":"three_hour","mode":"json","lang":"en"}
    result = requests.get(url, headers=headers, params=querystring).json()
    forecast_items = extract_forecast_list(result)
    # Filter by requested date range
    filtered_forecast = []
    min_temps = []
    max_temps = []
    for item in forecast_items:
        item_date = datetime.strptime(item['time'], "%Y-%m-%d %H:%M").date()
        if start_dt <= item_date <= end_dt:
            if item['min_c'] is not None:
                min_temps.append(item['min_c'])
            if item['max_c'] is not None:
                max_temps.append(item['max_c'])
            filtered_forecast.append(item)
    if not min_temps:
        raise HTTPException(
            status_code=404,
            detail="No forecast data available for the specified location/date range."
        )
    overall_min = min(min_temps)
    overall_max = max(max_temps)
    db_entry = WeatherRequest(
        location_query=request.Location or request.zipcode or f"Lat:{request.Latitude}, Lon:{request.Longitude}",
        date_range_start=start_dt,
        date_range_end=end_dt,
        overall_min_temp_c=overall_min,
        overall_max_temp_c=overall_max,
        full_forecast_json=json.dumps(filtered_forecast),
        note=None
    )
    session.add(db_entry)
    session.commit()
    session.refresh(db_entry)

    return {
        "message": "Weather request saved successfully!",
        "id": db_entry.id,
        "summary": {
            "location_query": db_entry.location_query,
            "date_range": f"{db_entry.date_range_start} to {db_entry.date_range_end}",
            "overall_min_temp_c": db_entry.overall_min_temp_c,
            "overall_max_temp_c": db_entry.overall_max_temp_c,
            "request_timestamp": db_entry.request_timestamp.isoformat()
        },
        "detailed_forecast": json.loads(db_entry.full_forecast_json)
    }


@app.get("/read_request/{request_id}", response_model=WeatherRequest)
async def read_request(request_id: int, session: Session = Depends(get_session)):
    """READ: Allows users to read a single previous weather information record by ID."""
    
    db_entry = session.get(WeatherRequest, request_id)

    if not db_entry:
        raise HTTPException(status_code=404, detail="Request record not found")

    # Defensive: handle missing fields and empty forecast
    full_forecast = []
    try:
        if db_entry.full_forecast_json:
            full_forecast = json.loads(db_entry.full_forecast_json)
    except Exception:
        full_forecast = []

    return {
        "id": db_entry.id,
        "location_query": db_entry.location_query,
        "date_range_start": db_entry.date_range_start,
        "date_range_end": db_entry.date_range_end,
        "request_timestamp": db_entry.request_timestamp.isoformat() if db_entry.request_timestamp else None,
        "overall_min_temp_c": db_entry.overall_min_temp_c,
        "overall_max_temp_c": db_entry.overall_max_temp_c,
        "full_forecast_json": full_forecast,
        "note": db_entry.note
    }


@app.get("/read_all_requests")
async def read_all_requests(session: Session = Depends(get_session)):
    """READ: Retrieves all stored weather request records from the database."""
    
    # Query all records
    statements = select(WeatherRequest)
    results = session.exec(statements).all()
    
    # Convert date/datetime objects to strings for clean JSON output
    clean_results = []
    for db_request in results:
        # Use model_dump to get a dict representation
        data = db_request.model_dump()
        
        # Serialize date and datetime objects
        for key, value in data.items():
            if isinstance(value, (date, datetime)):
                data[key] = value.isoformat()
        
        # Convert the forecast JSON string back to a structured object for display
        try:
            data['full_forecast_json'] = json.loads(data['full_forecast_json'])
        except:
            data['full_forecast_json'] = [] # Default to empty list on error

        clean_results.append(data)
        
    return clean_results


@app.patch("/update_request/{request_id}")
async def update_request(
    request_id: int, 
    update: WeatherUpdateRequest, 
    session: Session = Depends(get_session)
):
    """UPDATE: Allows updating non-weather data (e.g., location name or notes)."""
    
    db_request = session.get(WeatherRequest, request_id)

    if not db_request:
        raise HTTPException(status_code=404, detail="Request record not found")

    update_data = update.model_dump(exclude_unset=True)

    # Convert date strings to date objects if present
    if "date_range_start" in update_data and update_data["date_range_start"]:
        try:
            update_data["date_range_start"] = datetime.strptime(update_data["date_range_start"], "%Y-%m-%d").date()
        except Exception:
            raise HTTPException(status_code=400, detail="date_range_start must be in YYYY-MM-DD format")
    if "date_range_end" in update_data and update_data["date_range_end"]:
        try:
            update_data["date_range_end"] = datetime.strptime(update_data["date_range_end"], "%Y-%m-%d").date()
        except Exception:
            raise HTTPException(status_code=400, detail="date_range_end must be in YYYY-MM-DD format")

    for key, value in update_data.items():
        if value is not None:
            setattr(db_request, key, value)

    session.add(db_request)
    session.commit()
    session.refresh(db_request)

    return {
        "message": "Weather request updated successfully!",
        "id": db_request.id,
        "summary": {
            "location_query": db_request.location_query,
            "date_range": f"{db_request.date_range_start} to {db_request.date_range_end}",
            "overall_min_temp_c": db_request.overall_min_temp_c,
            "overall_max_temp_c": db_request.overall_max_temp_c,
            "request_timestamp": db_request.request_timestamp.isoformat()
        },
        "detailed_forecast": json.loads(db_request.full_forecast_json)
    }


@app.delete("/delete_request/{request_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_request(request_id: int, session: Session = Depends(get_session)):
    """DELETE: Allows deleting a record from the database."""
    
    request = session.get(WeatherRequest, request_id)
    
    if not request:
        return

    session.delete(request)
    session.commit()
    
    return


# --- Optional API Integration (2.2) ---

@app.post("/location_info")
async def get_location_info(location: LocationRequest):
    """Provides Google Maps data and YouTube search links for the location."""
    
    query = location.Location or f"{location.Latitude}, {location.Longitude}"
    
    youtube_results = await google_search_youtube_videos(query)
 
    map_link = f"https://www.google.com/maps/search/{query.replace(' ', '+')}"
    
    return {
        "location_query": query,
        "google_maps_link": map_link,
        "youtube_videos": youtube_results
    }

async def google_search_youtube_videos(query: str):
    # This is a placeholder for real API calls or structured search results
    return [
        f"https://www.youtube.com/results?search_query={query.replace(' ', '+')} travel",
        f"https://www.youtube.com/results?search_query={query.replace(' ', '+')} guide"
    ]


# --- Data Export (2.3) ---

@app.get("/export_json/{request_id}")
async def export_json(request_id: int, session: Session = Depends(get_session)):
    """Exports a single stored request record as a JSON response (for download)."""
    
    db_request = session.get(WeatherRequest, request_id)
    
    if not db_request:
        raise HTTPException(status_code=404, detail="Request record not found")
        
    # Convert the SQLModel object to a dictionary
    export_data = db_request.model_dump() 
    
    # FIX: Convert date/datetime objects to strings before serialization
    for key, value in export_data.items():
        if isinstance(value, (date, datetime)):
            export_data[key] = value.isoformat()

    # Convert the stored JSON string back to a JSON object
    try:
        export_data['full_forecast_json'] = json.loads(export_data['full_forecast_json'])
    except:
        pass 
        
    # Return as a JSONResponse with a custom filename hint for download
    return JSONResponse(
        content=export_data,
        headers={"Content-Disposition": f"attachment; filename=weather_request_{request_id}.json"}
    )