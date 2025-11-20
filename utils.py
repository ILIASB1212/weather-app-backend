
from datetime import date, datetime
from fastapi import HTTPException
from datetime import datetime
from math import ceil

def get_data(json_response):
    kelven=273.15
    weather_description=json_response.get("weather")[0].get("description")
    current_temperature=json_response.get("main").get("temprature_feels_like")-kelven # Celsius
    min_tempeture=json_response.get("main").get("temprature_min")-kelven # Celsius
    max_tempeture=json_response.get("main").get("temprature_max")-kelven # Celsius
    humidity=json_response.get("main").get("humidity") # percentage
    wind_speed=json_response.get("wind").get("speed") # meter/sec
    rain=json_response.get("rain").get("amount") # mm
    snow=json_response.get("snow").get("amount") # mm
    sunrise=datetime.fromtimestamp(json_response.get("sys").get("sunrise"))
    sunrise_hour=sunrise.hour
    sunrise_minutes=sunrise.minute
    sunset=datetime.fromtimestamp(json_response.get("sys").get("sunset"))
    sunset_hour=sunset.hour
    sunset_minutes=sunset.minute
    return {
        "description": weather_description,
        "temperature_current": ceil(current_temperature),
        "temperature_min": ceil(min_tempeture),
        "temperature_max": ceil(max_tempeture),
        "humidity": humidity,
        "wind_speed": wind_speed,
        "rain": rain,
        "snow": snow,
        "sunrise": f"{sunrise_hour}:{sunrise_minutes}",  # Format into a single string
        "sunset": f"{sunset_hour}:{sunset_minutes}"    # Format into a single string
    }


def validate_date_range(start_date_str: str, end_date_str: str):
    """Converts and validates the date range."""
    try:
        # Use date() to strip time component for accurate comparison later
        start_dt = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end_dt = datetime.strptime(end_date_str, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(
            status_code=400, detail="Date format must be YYYY-MM-DD"
        )
    
    if start_dt > end_dt:
        raise HTTPException(
            status_code=400, detail="Start date cannot be after the end date"
        )

    today = date.today()
    if start_dt < today:
        raise HTTPException(
            status_code=400, detail="Start date cannot be in the past"
        )
        
    return start_dt, end_dt