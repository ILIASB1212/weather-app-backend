
from datetime import date, datetime
from fastapi import HTTPException
from math import ceil

# Restore extract_forecast_list for app.py import
def extract_forecast_list(api_response):
    forecast_list = []
    kelvin = 273.15
    for item in api_response.get("list", []):
        timestamp_value = item.get("dt")
        date_time_obj = datetime.fromtimestamp(timestamp_value)
        formatted_date = date_time_obj.strftime("%Y-%m-%d %H:%M")
        main_data = item.get("main", {})
        min_k = main_data.get("temprature_min")
        max_k = main_data.get("temprature_max")
        min_c = round((min_k - kelvin), 1) if min_k is not None else None
        max_c = round((max_k - kelvin), 1) if max_k is not None else None
        weather = item.get("weather", [{}])[0].get("main", "N/A")
        forecast_list.append({
            "time": formatted_date,
            "min_c": min_c,
            "max_c": max_c,
            "weather": weather
        })
    return forecast_list

# Utility function to save forecast data to the database
def save_forecast_to_db(location_query, date_range_start, date_range_end, overall_min_temp_c, overall_max_temp_c, forecast_list, note=None):
    """
    Saves the provided forecast data to the WeatherRequest table.
    Returns the created WeatherRequest instance.
    """
    from database import WeatherRequest, get_session
    import json
    db_entry = WeatherRequest(
        location_query=location_query,
        date_range_start=date_range_start,
        date_range_end=date_range_end,
        overall_min_temp_c=overall_min_temp_c,
        overall_max_temp_c=overall_max_temp_c,
        full_forecast_json=json.dumps(forecast_list),
        note=note
    )
    session_gen = get_session()
    session = next(session_gen)
    session.add(db_entry)
    session.commit()
    session.refresh(db_entry)
    return db_entry


from datetime import datetime
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