from typing import Optional
from datetime import datetime, date
from sqlmodel import Field, SQLModel, create_engine, Session

sqlite_file_name = "weather.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"


engine = create_engine(sqlite_url, echo=True, connect_args={"check_same_thread": False})


class WeatherRequest(SQLModel, table=True):
    """
    Table to store weather requests and the resulting aggregated forecast data.
    """

    id: Optional[int] = Field(default=None, primary_key=True)

    location_query: str
    date_range_start: date
    date_range_end: date
    request_timestamp: datetime = Field(default_factory=datetime.utcnow)

    overall_min_temp_c: float
    overall_max_temp_c: float
    full_forecast_json: str = Field(default="[]")

    # Optional note field for update operations
    note: Optional[str] = None


def create_db_and_tables():
    """
    Creates the database file and all tables defined by SQLModel.
    """
    SQLModel.metadata.create_all(engine)

def get_session():
    """
    FastAPI dependency that provides a database session.
    """
    with Session(engine) as session:
        yield session

if __name__ == "__main__":
    create_db_and_tables()
    print(f"Database setup complete. File: {sqlite_file_name}")