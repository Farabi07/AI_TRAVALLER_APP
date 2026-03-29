import os
import requests
import json
import asyncio
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Annotated, Literal, TypedDict, List, Optional
from datetime import datetime, timedelta
from urllib.parse import quote

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from openai import AsyncOpenAI
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
import uvicorn

# Load environment variables
load_dotenv()

# --- Configuration & Keys ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
AMADEUS_CLIENT_ID = os.getenv("AMADEUS_CLIENT_ID")
AMADEUS_CLIENT_SECRET = os.getenv("AMADEUS_CLIENT_SECRET")
UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY")

# --- Pydantic Models for JSON Output ---

class ScheduleItem(BaseModel):
    time: str = Field(description="Time of day, e.g., Morning, Midday, Evening, Dinner")
    icon: str = Field(description="Emoji icon relevant to the activity")
    description: str = Field(description="Brief description of the activity")

class DayDetail(BaseModel):
    day: str = Field(description="Day identifier, e.g., 'Day 1'")
    title: str = Field(description="Theme title for the day")
    image_url: str = Field(description="Placeholder URL for the day's image (will be replaced by tool)")
    schedule: List[ScheduleItem]

class StaticMap(BaseModel):
    image_url: str = Field(description="Placeholder URL for static map image (will be replaced by tool)")
    description: str = Field(description="Description of what the map shows")

class TripDetails(BaseModel):
    static_map: StaticMap
    tour_spots_title: str = Field(default="Major Tour Spots", description="Title for the list of spots")
    tour_spots: List[str] = Field(description="List of names of major tourist spots visited")
    days: List[DayDetail]

class DaySummary(BaseModel):
    day: str
    title: str
    activities: List[str]

class Duration(BaseModel):
    days: int
    nights: int

class Buttons(BaseModel):
    view_details: bool = True
    share: bool = True
    save: bool = True

class TripOverview(BaseModel):
    title: str
    image_url: str = Field(description="Placeholder URL for cover image (will be replaced by tool)")
    duration: Duration
    spots_count: int
    categories: List[str] = Field(description="List of categories like Beach, Nature, Food")
    description: str
    summary_itinerary: List[DaySummary]
    buttons: Buttons = Field(default_factory=Buttons)

class TripPlan(BaseModel):
    trip: TripOverview
    details: TripDetails

# --- Global Configuration ---
REQUEST_TIMEOUT = 5  # seconds
DEFAULT_SESSION_ID = str(uuid.uuid4())
IMAGE_CACHE_TTL_DAYS = 7

# In-memory cache: normalized query -> {"url": str, "expires_at": datetime}
UNSPLASH_IMAGE_CACHE = {}

# --- Weather Code Mapping (Module Level) ---
WEATHER_CODE_MAP = {
    0: "☀️ Clear Sky",
    1: "🌤️ Partly Cloudy",
    2: "☁️ Cloudy",
    3: "☁️ Overcast",
    45: "🌫️ Foggy", 48: "🌫️ Foggy",
    51: "🌧️ Drizzle", 53: "🌧️ Drizzle", 55: "🌧️ Drizzle",
    61: "🌧️ Rain", 63: "🌧️ Rain", 65: "🌧️ Rain",
    71: "❄️ Snow/Sleet", 73: "❄️ Snow/Sleet", 75: "❄️ Snow/Sleet", 77: "❄️ Snow/Sleet",
    80: "⛈️ Heavy Rain Showers", 81: "⛈️ Heavy Rain Showers", 82: "⛈️ Heavy Rain Showers",
    85: "❄️ Snow Showers", 86: "❄️ Snow Showers",
    95: "⚡ THUNDERSTORM (Bad Weather)", 96: "⚡ THUNDERSTORM (Bad Weather)", 99: "⚡ THUNDERSTORM (Bad Weather)"
}

def interpret_weather_code(code: int) -> str:
    """Convert WMO weather codes to human-readable descriptions"""
    return WEATHER_CODE_MAP.get(code, "❓ Unknown")

# --- Helper Functions ---

def _normalize_image_query(query: str) -> str:
    return " ".join((query or "").lower().strip().split())

def _build_unsplash_source_url(query: str) -> str:
    """Build a direct Unsplash Source URL as a no-empty-image fallback."""
    safe_query = quote((query or "travel destination").strip())
    return f"https://source.unsplash.com/1600x900/?{safe_query}"

def _get_cached_unsplash_image(query: str) -> Optional[str]:
    key = _normalize_image_query(query)
    if not key:
        return None

    cached = UNSPLASH_IMAGE_CACHE.get(key)
    if not cached:
        return None

    if datetime.utcnow() >= cached["expires_at"]:
        UNSPLASH_IMAGE_CACHE.pop(key, None)
        return None

    return cached.get("url")

def _set_cached_unsplash_image(query: str, image_url: str) -> None:
    key = _normalize_image_query(query)
    if not key or not image_url:
        return

    UNSPLASH_IMAGE_CACHE[key] = {
        "url": image_url,
        "expires_at": datetime.utcnow() + timedelta(days=IMAGE_CACHE_TTL_DAYS)
    }

def _build_unsplash_query_candidates(base_query: str) -> List[str]:
    base = (base_query or "").strip()
    if not base:
        return []

    variants = [
        f"{base} travel photography",
        f"{base} historical places",
        f"{base} heritage site",
        f"{base} famous monument",
        f"{base} tourism",
        f"{base} landmark",
        f"{base} cityscape",
        f"{base} landscape",
        "historical travel destination",
        "world heritage travel"
    ]

    deduped = []
    seen = set()
    for item in variants:
        key = item.lower().strip()
        if key and key not in seen:
            deduped.append(item)
            seen.add(key)
    return deduped

def _extract_unsplash_image_url(photo: dict) -> str:
    """Extract the best available image URL from an Unsplash photo object."""
    urls = photo.get("urls", {})
    for key in ("regular", "full", "small", "thumb"):
        value = urls.get(key)
        if value:
            return value
    return ""

def _is_image_url_reachable(image_url: str) -> bool:
    """Validate that the image URL is reachable for better UX."""
    if not image_url:
        return False

    try:
        head = requests.head(image_url, allow_redirects=True, timeout=REQUEST_TIMEOUT)
        if head.ok:
            return True
    except Exception:
        pass

    try:
        response = requests.get(image_url, stream=True, timeout=REQUEST_TIMEOUT)
        return response.status_code < 400
    except Exception:
        return False

def _score_unsplash_photo(photo: dict, base_query: str) -> float:
    """Score image quality and location relevance for deterministic selection."""
    query_terms = set(_normalize_image_query(base_query).split())
    travel_terms = {
        "travel", "tourism", "historical", "history", "heritage", "landmark",
        "monument", "temple", "museum", "fort", "palace", "castle"
    }

    description = photo.get("description") or ""
    alt_description = photo.get("alt_description") or ""
    location = photo.get("location") or {}
    location_text = " ".join(
        [
            location.get("city") or "",
            location.get("country") or "",
            location.get("name") or ""
        ]
    )
    searchable = f"{description} {alt_description} {location_text}".lower()

    term_hits = sum(1 for term in query_terms if term and term in searchable)
    travel_hits = sum(1 for term in travel_terms if term in searchable)
    likes = float(photo.get("likes", 0) or 0)
    width = float(photo.get("width", 0) or 0)
    height = float(photo.get("height", 1) or 1)
    aspect_ratio = width / height if height else 1.0
    landscape_bonus = 8.0 if aspect_ratio >= 1.25 else 0.0
    premium_bonus = 5.0 if photo.get("premium") else 0.0
    downloads = float(photo.get("downloads", 0) or 0)

    return (term_hits * 25.0) + (travel_hits * 8.0) + (likes * 0.12) + (downloads * 0.01) + landscape_bonus + premium_bonus

def _select_best_unsplash_photo(results: List[dict], base_query: str) -> Optional[dict]:
    """Pick a stable, high-quality, travel-relevant photo."""
    if not results:
        return None

    ranked = sorted(results, key=lambda item: _score_unsplash_photo(item, base_query), reverse=True)

    # Validate top candidates first to avoid returning dead links.
    for photo in ranked[:5]:
        image_url = _extract_unsplash_image_url(photo)
        if image_url and _is_image_url_reachable(image_url):
            return photo

    # If validation fails due transient network, still return best-ranked URL.
    for photo in ranked:
        if _extract_unsplash_image_url(photo):
            return photo

    return None

def _search_unsplash_once(search_query: str, base_query: str, per_page: int = 30) -> Optional[dict]:
    """Run one Unsplash search and return the best matching photo object."""
    url = "https://api.unsplash.com/search/photos"
    params = {
        "query": search_query,
        "client_id": UNSPLASH_ACCESS_KEY,
        "per_page": per_page,
        "orientation": "landscape",
        "order_by": "relevant",
        "content_filter": "high"
    }

    response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    data = response.json()
    results = data.get("results", [])
    if not results:
        return None

    return _select_best_unsplash_photo(results, base_query)

def _search_unsplash_results(search_query: str, per_page: int = 30) -> List[dict]:
    """Run one Unsplash search and return all candidate photo objects."""
    url = "https://api.unsplash.com/search/photos"
    params = {
        "query": search_query,
        "client_id": UNSPLASH_ACCESS_KEY,
        "per_page": per_page,
        "orientation": "landscape",
        "order_by": "relevant",
        "content_filter": "high"
    }

    response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    data = response.json()
    return data.get("results", []) or []

def _random_unsplash_photo(query: str) -> Optional[dict]:
    """Fallback to Unsplash random endpoint when search returns no usable image."""
    url = "https://api.unsplash.com/photos/random"
    params = {
        "query": query,
        "client_id": UNSPLASH_ACCESS_KEY,
        "orientation": "landscape",
        "content_filter": "high"
    }

    response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    data = response.json()
    return data if isinstance(data, dict) else None

def _find_best_unsplash_photo(base_query: str) -> Optional[dict]:
    """Try several location-focused queries and return best available photo."""
    all_results = []
    seen_ids = set()

    for search_query in _build_unsplash_query_candidates(base_query):
        try:
            results = _search_unsplash_results(search_query)
            for photo in results:
                photo_id = photo.get("id")
                if photo_id and photo_id in seen_ids:
                    continue
                if photo_id:
                    seen_ids.add(photo_id)
                all_results.append(photo)
        except Exception as search_error:
            print(f"Unsplash search failed for '{search_query}': {search_error}")

    best_from_search = _select_best_unsplash_photo(all_results, base_query)
    if best_from_search:
        return best_from_search

    # Final Unsplash-only fallback query for historical travel imagery.
    try:
        random_photo = _random_unsplash_photo(f"{base_query} historical travel")
        if random_photo and _extract_unsplash_image_url(random_photo):
            return random_photo
    except Exception as random_error:
        print(f"Unsplash random fallback failed: {random_error}")

    return None

async def fetch_unsplash_image_async(query: str):
    """Async helper to fetch travel photos from Unsplash only (no fallback)."""
    if not UNSPLASH_ACCESS_KEY:
        return _build_unsplash_source_url(query)

    clean_query = (query or "").strip()
    if not clean_query:
        return _build_unsplash_source_url(query)

    try:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, fetch_unsplash_image, clean_query)
    except Exception as e:
        print(f"Error fetching async Unsplash images: {e}")
        return _build_unsplash_source_url(query)

def get_amadeus_token():
    """Authenticates with Amadeus to get a temporary access token."""
    if not AMADEUS_CLIENT_ID or not AMADEUS_CLIENT_SECRET:
        return None
    
    url = "https://test.api.amadeus.com/v1/security/oauth2/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "client_credentials",
        "client_id": AMADEUS_CLIENT_ID,
        "client_secret": AMADEUS_CLIENT_SECRET
    }
    
    try:
        response = requests.post(url, headers=headers, data=data, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.json().get("access_token")
    except Exception as e:
        print(f"Error fetching Amadeus token: {e}")
        return None

def fetch_unsplash_image(query: str):
    """Fetch travel photos from Unsplash only, with 7-day cache."""
    if not UNSPLASH_ACCESS_KEY:
        return _build_unsplash_source_url(query)

    clean_query = (query or "").strip()
    if not clean_query:
        return _build_unsplash_source_url(query)

    cached_image = _get_cached_unsplash_image(clean_query)
    if cached_image:
        return cached_image

    try:
        best_photo = _find_best_unsplash_photo(clean_query)
        image_url = _extract_unsplash_image_url(best_photo or {})
        if image_url:
            _set_cached_unsplash_image(clean_query, image_url)
            return image_url

    except Exception as e:
        print(f"Error fetching Unsplash images: {e}")

    return _build_unsplash_source_url(clean_query)

# --- Tools Definitions ---

@tool
def check_weather(city: str):
    """
    Fetches detailed weather forecast including temperature, precipitation, wind, 
    humidity, and bad weather alerts (storms, etc.) for a specific city.
    Useful for helping the user decide the best day to visit.
    """
    # Step 1: Geocode the city to get lat/lon (Using Open-Meteo Geocoding for zero-config runnability)
    geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=en&format=json"
    
    try:
        geo_res = requests.get(geo_url, timeout=REQUEST_TIMEOUT).json()
        if not geo_res.get("results"):
            return f"Could not find coordinates for {city}."
        
        location = geo_res["results"][0]
        lat, lon = location["latitude"], location["longitude"]
        
        # Step 2: Fetch Weather with more parameters
        weather_url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,precipitation_sum,weathercode,windspeed_10m_max,humidity_2m_max",
            "timezone": "auto",
            "temperature_unit": "celsius"
        }
        
        w_res = requests.get(weather_url, params=params, timeout=REQUEST_TIMEOUT).json()
        
        daily = w_res.get("daily", {})
        times = daily.get("time", [])
        temps_max = daily.get("temperature_2m_max", [])
        temps_min = daily.get("temperature_2m_min", [])
        rain_probs = daily.get("precipitation_probability_max", [])
        rain_amounts = daily.get("precipitation_sum", [])
        wind_speeds = daily.get("windspeed_10m_max", [])
        humidity = daily.get("humidity_2m_max", [])
        weather_codes = daily.get("weathercode", [])
        
        forecast_report = f"🌍 Detailed Weather Forecast for {city}:\n\n"
        for i in range(min(5, len(times))):
            weather_desc = interpret_weather_code(weather_codes[i]) if i < len(weather_codes) else "Unknown"
            forecast_report += f"📅 {times[i]}:\n"
            forecast_report += f"  🌡️ Temperature: {temps_max[i]}°C (min: {temps_min[i]}°C)\n"
            forecast_report += f"  💧 Humidity: {humidity[i] if i < len(humidity) else 'N/A'}%\n"
            forecast_report += f"  💨 Wind Speed: {wind_speeds[i] if i < len(wind_speeds) else 'N/A'} km/h\n"
            forecast_report += f"  🌧️ Rain Probability: {rain_probs[i]}%\n"
            forecast_report += f"  📏 Rainfall: {rain_amounts[i] if i < len(rain_amounts) else 'N/A'} mm\n"
            forecast_report += f"  {weather_desc}\n"
            
            # Add warning for bad weather
            if weather_codes[i] in [95, 96, 99]:  # Thunderstorm codes
                forecast_report += f"  ⚠️ WARNING: Severe thunderstorm expected! Not recommended for outdoor activities.\n"
            elif rain_probs[i] > 80:
                forecast_report += f"  ⚠️ WARNING: High chance of heavy rain. Plan indoor activities.\n"
            elif wind_speeds[i] > 40 if i < len(wind_speeds) else False:
                forecast_report += f"  ⚠️ WARNING: Strong winds expected. Be cautious with outdoor plans.\n"
            
            forecast_report += "\n"
            
        return forecast_report

    except Exception as e:
        return f"Error fetching weather: {str(e)}"

@tool
def google_places_search(query: str, location: str = None):
    """
    Searches for places, restaurants, hidden gems, or tourist spots using Google Places API.
    'query' should be what to look for (e.g., "Italian restaurants", "Hidden gems").
    'location' is the city or area name.
    """
    if not GOOGLE_API_KEY:
        return "Error: Google API Key not found."

    # Using the Text Search (New) API logic
    url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_API_KEY,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.rating,places.userRatingCount"
    }
    
    text_query = f"{query} in {location}" if location else query
    payload = {"textQuery": text_query}

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=REQUEST_TIMEOUT)
        data = response.json()
        
        places = data.get("places", [])
        if not places:
            return "No places found."
            
        result = f"Top results for '{text_query}':\n"
        for place in places[:5]:
            name = place.get("displayName", {}).get("text", "Unknown")
            address = place.get("formattedAddress", "No address")
            rating = place.get("rating", "N/A")
            result += f"- {name} (Rating: {rating}/5): {address}\n"
            
        return result
    except Exception as e:
        return f"Error connecting to Google Places: {e}"

@tool
def get_map_view(location: str, zoom: int = 14):
    """
    Generates a Google Maps Static API URL for a given location.
    Returns a URL that the user can click to see the map.
    """
    if not GOOGLE_API_KEY:
        return "Error: Google API Key not found."
    
    # URL Encode the location
    encoded_loc = quote(location)
    
    url = f"https://maps.googleapis.com/maps/api/staticmap?center={encoded_loc}&zoom={zoom}&size=600x400&maptype=roadmap&key={GOOGLE_API_KEY}"
    
    return f"Here is a map view of {location}: {url}"

@tool
def find_hotels(city: str):
    """
    Finds hotels in a specific city using the Amadeus API.
    """
    token = get_amadeus_token()
    if not token:
        return "Error: Could not authenticate with Amadeus API. Check API keys."

    try:
        # Step 1: Find the City IATA code
        city_url = "https://test.api.amadeus.com/v1/reference-data/locations"
        headers = {"Authorization": f"Bearer {token}"}
        city_params = {"subType": "CITY", "keyword": city}
        
        city_res = requests.get(city_url, headers=headers, params=city_params, timeout=REQUEST_TIMEOUT).json()
        
        if not city_res.get("data"):
            return f"Could not find IATA code for city: {city}"
            
        iata_code = city_res["data"][0]["iataCode"]
        
        # Step 2: Search for hotels in that city
        hotel_url = f"https://test.api.amadeus.com/v1/reference-data/locations/hotels/by-city"
        hotel_params = {"cityCode": iata_code}
        
        hotel_res = requests.get(hotel_url, headers=headers, params=hotel_params, timeout=REQUEST_TIMEOUT).json()
        
        hotels = hotel_res.get("data", [])
        if not hotels:
            return f"No hotels found in {city} ({iata_code})."
            
        output = f"Hotels found in {city} ({iata_code}):\n"
        for hotel in hotels[:5]:
            name = hotel.get("name", "Unknown Hotel")
            hotel_id = hotel.get("hotelId", "")
            output += f"- {name} (ID: {hotel_id})\n"
            
        return output

    except Exception as e:
        return f"Error querying Amadeus: {e}"

@tool
def get_destination_photo(query: str):
    """
    Fetches a famous travel photo for a location using Unsplash API.
    Prioritizes well-liked, popular photos from famous photographers.
    """
    if not UNSPLASH_ACCESS_KEY:
        source_url = _build_unsplash_source_url(query)
        return f"![Travel photo]({source_url})\n*Unsplash source image for: {query}*"

    clean_query = (query or "").strip()
    if not clean_query:
        return "Please provide a valid destination or location query."
    
    try:
        best_photo = _find_best_unsplash_photo(clean_query)
        if not best_photo:
            source_url = _build_unsplash_source_url(clean_query)
            return f"![Travel photo]({source_url})\n*Unsplash source image for: {clean_query}*"
        
        desc = best_photo.get("description") or best_photo.get("alt_description") or "Famous travel photo"
        image_url = _extract_unsplash_image_url(best_photo)
        if not image_url:
            return "No valid photo URL found for this location."

        _set_cached_unsplash_image(clean_query, image_url)

        credit = best_photo.get("user", {}).get("name") or "Unknown Photographer"
        likes = best_photo.get("likes", 0)
        
        return f"![{desc}]({image_url})\n*Popular photo (⭐ {likes} likes) by {credit} on Unsplash*"
    except Exception as e:
        source_url = _build_unsplash_source_url(clean_query)
        return f"![Travel photo]({source_url})\n*Unsplash source image for: {clean_query}*"

@tool
def get_current_date():
    """
    Returns the current date and the date for next week.
    Useful when the user asks for 'next week' or 'upcoming' events.
    """
    now = datetime.now()
    next_week = now + timedelta(days=7)
    return f"Today is {now.strftime('%Y-%m-%d')}. One week from now is {next_week.strftime('%Y-%m-%d')}."

@tool
def generate_trip_plan(destination: str, duration_days: int):
    """
    Generates a full, structured travel itinerary in JSON format for a specific destination and duration.
    Use this tool when the user asks for a 'trip plan', 'itinerary', or 'hitlist' and expects a structured result.
    It returns a JSON string with daily schedules, categories with emojis, and photo placeholders filled.
    """
    
    # 1. Initialize a specific LLM instance for structured output (use faster model)
    structured_llm = ChatOpenAI(model="gpt-4-turbo", temperature=0.7).with_structured_output(TripPlan)
    
    # 2. Prompt for the plan
    prompt = f"""
    Create a {duration_days}-day travel itinerary for {destination}.
    Be specific with restaurant names, tourist spots, and activities.
    Include exactly 3 categories with emojis like '🏖️ Beach', '🌲 Nature', '🍽️ Food' or similar relevant categories.
    Populate the 'tour_spots' list with the major places visited.
    Ensure the 'image_url' fields are left as 'PLACEHOLDER' so the tool can fill them.
    """
    
    try:
        # 3. Generate the Plan Object
        plan: TripPlan = structured_llm.invoke(prompt)
        
        # 4. Add emojis to categories if not already present
        category_emoji_map = {
            "Beach": "🏖️",
            "Nature": "🌲",
            "Food": "🍽️",
            "Culture": "🏛️",
            "Art": "🎨",
            "Adventure": "⛰️",
            "Historical": "🏰",
            "Urban": "🏙️",
            "Nightlife": "🌙",
            "Shopping": "🛍️",
            "Sports": "⚽",
            "Photography": "📸",
            "Wildlife": "🦁",
            "Water": "🌊",
            "Mountains": "⛰️",
            "Desert": "🏜️",
            "Forest": "🌳",
            "Hiking": "🥾",
            "Yoga": "🧘",
            "Wellness": "💆",
            "Museums": "🏛️",
            "Gardens": "🌸",
            "Temples": "🛕",
            "Beaches": "🏖️",
            "Islands": "🏝️"
        }
        
        # Add emojis to categories
        enhanced_categories = []
        for category in plan.trip.categories[:3]:  # Limit to 3 categories
            # Check if emoji is already present
            if any(char in category for char in "🏖️🌲🍽️🏛️🎨⛰️🏰🏙️🌙🛍️⚽📸🦁🌊🏜️🌳🥾🧘💆🌸🛕🏝️"):
                enhanced_categories.append(category)
            else:
                # Find matching emoji
                emoji = ""
                for key, val in category_emoji_map.items():
                    if key.lower() in category.lower():
                        emoji = val
                        break
                if emoji:
                    enhanced_categories.append(f"{emoji} {category}")
                else:
                    enhanced_categories.append(f"✨ {category}")
        
        plan.trip.categories = enhanced_categories
        
        # 5. Enhance with Real Images from Unsplash (PARALLEL FETCHING)
        try:
            # Build list of image queries
            image_queries = [
                f"{destination} travel scenery",  # Cover image
                *[f"{destination} {day.title}" for day in plan.details.days]  # Daily images
            ]
            
            # Use ThreadPoolExecutor for parallel Unsplash requests
            with ThreadPoolExecutor(max_workers=min(5, len(image_queries))) as executor:
                image_urls = list(executor.map(fetch_unsplash_image, image_queries))
            
            # Assign fetched images
            plan.trip.image_url = image_urls[0]
            for idx, day in enumerate(plan.details.days):
                day.image_url = image_urls[idx + 1]
        except Exception as e:
            print(f"Warning: Parallel image fetching failed: {e}, using sequential fallback")
            # Fallback to sequential if parallel fails
            plan.trip.image_url = fetch_unsplash_image(f"{destination} travel scenery")
            for day in plan.details.days:
                day.image_url = fetch_unsplash_image(f"{destination} {day.title}")
        
        # Static Map Image (Using Google Static Maps API)
        if GOOGLE_API_KEY:
            encoded_dest = quote(destination)
            # Default to showing the destination city area
            plan.details.static_map.image_url = f"https://maps.googleapis.com/maps/api/staticmap?center={encoded_dest}&zoom=12&size=600x400&maptype=roadmap&key={GOOGLE_API_KEY}"
        else:
            plan.details.static_map.image_url = "https://example.com/static_map_placeholder.png"
            
        # 5. Return JSON string
        return plan.model_dump_json(indent=2)
        
    except Exception as e:
        return f"Error generating trip plan: {e}"

# --- LangGraph Setup ---

# List of tools the agent can use
tools = [
    check_weather, 
    google_places_search, 
    get_map_view, 
    find_hotels, 
    get_destination_photo, 
    get_current_date,
    generate_trip_plan
]

# Initialize the LLM (Synchronous)
llm = ChatOpenAI(model="gpt-4.1", temperature=0.5)

# Initialize Async LLM
async_llm = AsyncOpenAI(api_key=OPENAI_API_KEY)

# Bind tools to the LLM
llm_with_tools = llm.bind_tools(tools)

# Define State
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]

# Define the System Message
sys_msg = SystemMessage(content="""You are an expert AI Travel Agent. 
Your goal is to help users plan amazing trips by checking weather, finding hotels, discovering local spots, and providing map views.

IMPORTANT: 
- If the user asks for a "Trip Plan", "Hitlist", "Itinerary getaway", or "Itinerary", YOU MUST USE the 'generate_trip_plan' tool.
- CRITICAL: When the 'generate_trip_plan' tool returns the JSON output, YOU MUST output that exact JSON content as your final response. You may wrap it in a markdown code block (```json), but DO NOT summarize the content into a chatty message. The user needs the raw JSON data.
- For all other travel suggestions (e.g., specific places, weather, hotels) or general chat, return a helpful plain text response.

General Tools:
- Use 'check_weather' for forecasts.
- Use 'google_places_search' for finding specific spots.
- Use 'get_map_view' for maps.
- Use 'get_destination_photo' for photos.
- Use 'generate_trip_plan' for full structured itineraries.

Be enthusiastic and helpful!""")

# Define the Agent Node
def agent_node(state: AgentState):
    messages = [sys_msg] + state["messages"]
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}

# Build the Graph
workflow = StateGraph(AgentState)
workflow.add_node("agent", agent_node)
workflow.add_node("tools", ToolNode(tools))
workflow.add_edge(START, "agent")
workflow.add_conditional_edges("agent", tools_condition)
workflow.add_edge("tools", "agent")

# Compile
app = workflow.compile(checkpointer=MemorySaver())

# --- FastAPI Setup ---
fastapi_app = FastAPI(
    title="AI Travel Agent API",
    description="Chat and travel planning API powered by LangGraph",
    version="1.0.0"
)

# Add CORS middleware
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for API
class ChatRequest(BaseModel):
    prompt: str = Field(..., description="User's prompt/message")
    session_id: str = Field(default=DEFAULT_SESSION_ID, description="Session ID for conversation continuity (auto-generated at startup)")

def chat_agent(prompt: str, session_id: str) -> dict:
    """
    Process a user prompt through the LangGraph travel agent.
    
    Returns:
        dict with format:
        - {"type": "json", "data": {...}} for structured trip plans
        - {"type": "text", "data": "message"} for text responses
    """
    try:
        user_message = HumanMessage(content=prompt)
        config = {"configurable": {"thread_id": session_id}}

        # Stream events from the LangGraph app
        events = app.stream(
            {"messages": [user_message]},
            config=config,
            stream_mode="values"
        )

        final_message = None
        for event in events:
            if "messages" in event:
                final_message = event["messages"][-1]

        if not final_message or not final_message.content:
            return {
                "type": "text",
                "data": "Sorry, I couldn't process your request."
            }

        response_text = final_message.content.strip()
        
        # Check if response is JSON (trip plan wrapped in markdown code block)
        if response_text.startswith("```json"):
            try:
                # Extract and parse JSON from markdown code block
                json_str = response_text.replace("```json", "").replace("```", "").strip()
                json_data = json.loads(json_str)
                return {
                    "type": "json",
                    "data": json_data
                }
            except json.JSONDecodeError:
                # If JSON parsing fails, return as text
                return {
                    "type": "text",
                    "data": response_text
                }
        else:
            # Regular text response
            return {
                "type": "text",
                "data": response_text
            }

    except Exception as e:
        return {
            "type": "text",
            "data": f"Error processing request: {str(e)}"
        }

@fastapi_app.get("/")
async def root():
    """Root endpoint - API information"""
    return {
        "message": "🌍 AI Travel Agent API",
        "version": "1.0.0",
        "endpoints": {
            "chat": "POST /chat",
            "health": "GET /health",
            "docs": "/docs"
        }
    }

@fastapi_app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "API is running"}

@fastapi_app.post("/chat")
async def chat(request: ChatRequest):
    """
    Main chat endpoint for the AI Travel Agent.
    
    Accepts a prompt and returns either:
    - JSON response for structured data (trip plans, etc.)
    - Plain text response for messages and advice
    
    Args:
        request: ChatRequest containing 'prompt' (required) and 'session_id' (optional)
    
    Returns:
        JSONResponse: For type=json responses
        PlainTextResponse: For type=text responses
    """
    try:
        # Get response from agent
        result = chat_agent(request.prompt, request.session_id)
        
        # Return appropriate response type
        if result["type"] == "json":
            return JSONResponse(
                content=result["data"],
                status_code=200
            )
        else:  # type == "text"
            return PlainTextResponse(
                content=result["data"],
                status_code=200
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing chat request: {str(e)}"
        )

# --- Main Execution Loop ---
if __name__ == "__main__":
    uvicorn.run(fastapi_app, host="10.10.7.114", port=8000)
