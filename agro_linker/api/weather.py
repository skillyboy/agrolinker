"""
Weather data API endpoints for Agro Linker using Django Ninja.
"""
from typing import List, Optional
from ninja import Router, Schema, Query
from django.shortcuts import get_object_or_404
from django.http import HttpRequest
from ..models import WeatherData
from datetime import datetime, date, timedelta
from random import uniform
from ..schemas import *

router = Router(tags=["Weather Data"])

# ====================== ENDPOINTS ======================
@router.get("/", response=List[WeatherDataOut], summary="List weather data")
def list_weather_data(request, filters: WeatherFilter = Query(...)):
    """
    Get historical weather data with optional filters:
    - location: Filter by specific location
    - start_date: Filter data from this date
    - end_date: Filter data until this date
    """
    queryset = WeatherData.objects.all()
    
    if filters.location:
        queryset = queryset.filter(location=filters.location)
    if filters.start_date:
        queryset = queryset.filter(date__gte=filters.start_date)
    if filters.end_date:
        queryset = queryset.filter(date__lte=filters.end_date)
        
    return queryset.order_by('-date')

@router.get("/{weather_id}", response=WeatherDataOut, summary="Get weather record")
def get_weather_data(request, weather_id: int):
    """Get specific weather data record by ID"""
    return get_object_or_404(WeatherData, id=weather_id)

@router.post("/", response=WeatherDataOut, summary="Create weather record")
def create_weather_data(request, payload: WeatherDataIn):
    """Create new weather data record (Admin only)"""
    weather = WeatherData.objects.create(**payload.dict())
    return weather

@router.get("/forecast/", response=List[WeatherForecastOut], summary="Get weather forecast")
def get_forecast(request, location: str, days: int = 7):
    """
    Get weather forecast for a location (mock implementation)
    
    Parameters:
    - location: Required location name
    - days: Number of days to forecast (default: 7)
    """
    # This is a mock implementation - replace with actual API call
    forecast = []
    for i in range(days):
        forecast.append({
            'date': date.today() + timedelta(days=i),
            'temperature': round(uniform(20, 30), 2),  # Random temp between 20-30
            'humidity': round(uniform(40, 80)),        # Random humidity 40-80%
            'precipitation': round(uniform(0, 20)),    # Random precip 0-20mm
            'wind_speed': round(uniform(5, 15))        # Random wind 5-15 km/h
        })
    
    return forecast