# Copyright 2026 Google LLC
# Firestore tools for Wanderlust AI

import base64
import json
import os
import urllib.parse
import urllib.request
import uuid
from typing import Any, Optional
from dotenv import load_dotenv
import google.auth
from google import genai
from google.adk.tools import ToolContext
from google.cloud import firestore, storage
from google.genai import types

load_dotenv()

# Hardcode project ID and Cloud Storage bucket as literal strings to prevent lookup issues on Agent Platform
FIRESTORE_PROJECT = "qwiklabs-gcp-02-a4ec6fc6c34a"
GCS_BUCKET_NAME = "wanderlust-ai-media-qwiklabs02"


def get_db_client() -> firestore.Client:
    """Returns an authenticated Firestore client for the hardcoded GCP project."""
    creds, _ = google.auth.default()
    if hasattr(creds, "with_scopes"):
        creds = creds.with_scopes(["https://www.googleapis.com/auth/cloud-platform"])
    return firestore.Client(project=FIRESTORE_PROJECT, credentials=creds)


def search_destinations(
    vibe: Optional[str] = None,
    budget_level: Optional[str] = None,
    country: Optional[str] = None,
) -> str:
    """Searches the travel destination database in Firestore by vibe, budget level, or country.

    Args:
        vibe: Filter by trip vibe (e.g. 'culture', 'adventure', 'relaxation', 'luxury').
        budget_level: Filter by budget tier (e.g. 'budget', 'moderate', 'luxury').
        country: Filter by destination country (e.g. 'Japan', 'Greece', 'Canada', 'Costa Rica', 'Iceland').

    Returns:
        JSON string containing matching destination objects.
    """
    db = get_db_client()
    query_ref = db.collection("destinations")

    if vibe:
        query_ref = query_ref.where("vibe", "==", vibe.lower().strip())
    if budget_level:
        query_ref = query_ref.where("budget_level", "==", budget_level.lower().strip())

    results = []
    for doc in query_ref.stream():
        data = doc.to_dict()
        data["id"] = doc.id
        # Client-side country filter if country was requested (case-insensitive substring match)
        if country and country.lower() not in data.get("country", "").lower():
            continue
        results.append(data)

    if not results:
        return json.dumps({"message": "No destinations found matching the specified criteria."})

    return json.dumps({"count": len(results), "destinations": results}, indent=2)


def get_destination_details(destination_id: str) -> str:
    """Retrieves full details for a specific travel destination from Firestore.

    Args:
        destination_id: The unique ID of the destination (e.g. 'kyoto-japan', 'santorini-greece', 'banff-canada').

    Returns:
        JSON string with destination details or an error message if not found.
    """
    db = get_db_client()
    doc_ref = db.collection("destinations").document(destination_id.strip())
    doc = doc_ref.get()

    if not doc.exists:
        return json.dumps({"error": f"Destination with ID '{destination_id}' was not found in Firestore."})

    data = doc.to_dict()
    data["id"] = doc.id
    return json.dumps(data, indent=2)


def add_destination(
    destination_id: str,
    name: str,
    country: str,
    vibe: str,
    budget_level: str,
    description: str,
    rating: float = 4.5,
    popular_activities: Optional[list[str]] = None,
    best_season: str = "All Year",
) -> str:
    """Adds a new travel destination to the Firestore database.

    Args:
        destination_id: Unique string slug ID for the destination (e.g. 'paris-france', 'bali-indonesia').
        name: Name of the destination city or region.
        country: Country where the destination is located.
        vibe: Primary vibe ('culture', 'adventure', 'relaxation', 'luxury').
        budget_level: Budget category ('budget', 'moderate', 'luxury').
        description: A compelling summary of what makes this destination special.
        rating: Average rating score out of 5.0 (default: 4.5).
        popular_activities: List of top activities or attractions at this destination.
        best_season: Best time of year to visit.

    Returns:
        Confirmation message with document details.
    """
    db = get_db_client()
    doc_id = destination_id.lower().strip().replace(" ", "-")
    doc_ref = db.collection("destinations").document(doc_id)

    dest_data = {
        "id": doc_id,
        "name": name.strip(),
        "country": country.strip(),
        "vibe": vibe.lower().strip(),
        "budget_level": budget_level.lower().strip(),
        "description": description.strip(),
        "rating": float(rating),
        "popular_activities": popular_activities or [],
        "best_season": best_season.strip(),
    }

    doc_ref.set(dest_data)
    return json.dumps({"status": "success", "message": f"Successfully saved destination '{name}' to Firestore.", "destination": dest_data}, indent=2)


def calculate_trip_budget(
    destination_name: str,
    duration_days: int,
    num_travelers: int = 1,
    budget_tier: str = "moderate",
) -> str:
    """Calculates an itemized estimated trip budget breakdown for a destination.

    Args:
        destination_name: Name of the destination (e.g. 'Kyoto', 'Paris', 'Santorini').
        duration_days: Length of the trip in days.
        num_travelers: Number of people traveling.
        budget_tier: Budget tier ('budget', 'moderate', 'luxury').

    Returns:
        JSON string containing itemized costs and total budget summary.
    """
    duration = max(1, int(duration_days))
    travelers = max(1, int(num_travelers))
    tier = budget_tier.lower().strip()

    rates = {
        "budget": {"lodging": 60, "food": 35, "activities": 25, "transport": 15},
        "moderate": {"lodging": 150, "food": 75, "activities": 55, "transport": 35},
        "luxury": {"lodging": 450, "food": 180, "activities": 130, "transport": 80},
    }.get(tier, {"lodging": 150, "food": 75, "activities": 55, "transport": 35})

    rooms = (travelers + 1) // 2
    lodging_total = rates["lodging"] * duration * rooms
    food_total = rates["food"] * duration * travelers
    activities_total = rates["activities"] * duration * travelers
    transport_total = rates["transport"] * duration * travelers
    subtotal = lodging_total + food_total + activities_total + transport_total
    emergency_buffer = round(subtotal * 0.10, 2)
    grand_total = subtotal + emergency_buffer
    per_person = round(grand_total / travelers, 2)

    result = {
        "destination": destination_name.strip(),
        "duration_days": duration,
        "num_travelers": travelers,
        "budget_tier": tier,
        "breakdown": {
            "lodging_total_usd": lodging_total,
            "food_total_usd": food_total,
            "activities_total_usd": activities_total,
            "transport_total_usd": transport_total,
            "emergency_buffer_usd": emergency_buffer,
        },
        "grand_total_usd": grand_total,
        "cost_per_person_usd": per_person,
    }
    return json.dumps(result, indent=2)


def get_live_destination_weather(city_name: str) -> str:
    """Fetches real-time live weather conditions for any travel destination using the Open-Meteo public API.

    Args:
        city_name: Name of the city or destination (e.g. 'Kyoto', 'Paris', 'Santorini', 'San Francisco', 'Banff').

    Returns:
        JSON string containing live weather conditions, temperature (°C and °F), windspeed, and location info.
    """
    try:
        encoded_city = urllib.parse.quote(city_name.strip())
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={encoded_city}&count=1"

        req = urllib.request.Request(geo_url, headers={"User-Agent": "WanderlustAI/1.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            geo_data = json.loads(response.read().decode())

        results = geo_data.get("results")
        if not results:
            return json.dumps({"error": f"Could not find coordinates for city '{city_name}'."})

        location = results[0]
        lat = location["latitude"]
        lon = location["longitude"]
        name = location.get("name", city_name)
        country = location.get("country", "")

        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        req_w = urllib.request.Request(weather_url, headers={"User-Agent": "WanderlustAI/1.0"})
        with urllib.request.urlopen(req_w, timeout=5) as resp_w:
            w_data = json.loads(resp_w.read().decode())

        current = w_data.get("current_weather", {})
        temp_c = current.get("temperature", 0.0)
        temp_f = round(temp_c * 9 / 5 + 32, 1)
        windspeed_kmh = current.get("windspeed", 0.0)
        weather_code = current.get("weathercode", 0)

        code_descriptions = {
            0: "Clear sky",
            1: "Mainly clear",
            2: "Partly cloudy",
            3: "Overcast",
            45: "Fog",
            48: "Depositing rime fog",
            51: "Light drizzle",
            53: "Moderate drizzle",
            55: "Dense drizzle",
            61: "Slight rain",
            63: "Moderate rain",
            65: "Heavy rain",
            71: "Slight snow fall",
            73: "Moderate snow fall",
            75: "Heavy snow fall",
            80: "Slight rain showers",
            81: "Moderate rain showers",
            82: "Violent rain showers",
            95: "Thunderstorm",
        }
        condition = code_descriptions.get(weather_code, "Partly cloudy")

        return json.dumps(
            {
                "destination": name,
                "country": country,
                "coordinates": {"latitude": lat, "longitude": lon},
                "condition": condition,
                "temperature_celsius": temp_c,
                "temperature_fahrenheit": temp_f,
                "windspeed_kmh": windspeed_kmh,
                "data_source": "Open-Meteo Free Public API",
            },
            indent=2,
        )
    except Exception as e:
        return json.dumps({"error": f"Failed to fetch live weather data: {str(e)}"})


def geocode_address(address: str) -> str:
    """Uses the Google Maps Geocoding REST API to convert an address or place name into geographic coordinates.

    Args:
        address: Location address or place name (e.g. '1600 Amphitheatre Pkwy, Mountain View, CA' or 'Kyoto Station').

    Returns:
        JSON string containing the name, formatted address, location coordinates (latitude, longitude), and place ID.
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return json.dumps({"error": "GOOGLE_MAPS_API_KEY environment variable is not set."})

    try:
        encoded_address = urllib.parse.quote(address.strip())
        url = f"https://maps.googleapis.com/maps/api/geocode/json?address={encoded_address}&key={api_key}"

        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())

        if data.get("status") != "OK" or not data.get("results"):
            return json.dumps({"error": f"Geocoding failed for address '{address}': {data.get('status', 'No results found')}"})

        first_result = data["results"][0]
        location = first_result.get("geometry", {}).get("location", {})
        formatted_address = first_result.get("formatted_address", "")
        place_id = first_result.get("place_id", "")

        return json.dumps(
            {
                "name": address.strip(),
                "address": formatted_address,
                "location": {
                    "latitude": location.get("lat"),
                    "longitude": location.get("lng"),
                },
                "place_id": place_id,
            },
            indent=2,
        )
    except Exception as e:
        return json.dumps({"error": f"Failed to geocode address: {str(e)}"})


def find_nearby_places(
    latitude: float,
    longitude: float,
    place_type: str = "tourist_attraction",
    radius_meters: float = 2000.0,
) -> str:
    """Uses the Google Places API (New) searchNearby REST endpoint to find nearby places of a given type around coordinates.

    Args:
        latitude: Center latitude coordinate.
        longitude: Center longitude coordinate.
        place_type: Type of place to search for (e.g. 'tourist_attraction', 'restaurant', 'cafe', 'museum', 'park').
        radius_meters: Search radius in meters (default: 2000.0).

    Returns:
        JSON string containing list of nearby places with name, formatted address, and location coordinates.
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return json.dumps({"error": "GOOGLE_MAPS_API_KEY environment variable is not set."})

    try:
        url = "https://places.googleapis.com/v1/places:searchNearby"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location",
        }
        payload = {
            "includedTypes": [place_type.strip().lower()],
            "maxResultCount": 10,
            "locationRestriction": {
                "circle": {
                    "center": {
                        "latitude": float(latitude),
                        "longitude": float(longitude),
                    },
                    "radius": float(radius_meters),
                }
            },
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())

        raw_places = data.get("places", [])
        results = []
        for p in raw_places:
            display_name = p.get("displayName", {}).get("text", "")
            formatted_address = p.get("formattedAddress", "")
            loc = p.get("location", {})
            results.append({
                "name": display_name,
                "address": formatted_address,
                "location": {
                    "latitude": loc.get("latitude"),
                    "longitude": loc.get("longitude"),
                },
            })

        return json.dumps(
            {
                "count": len(results),
                "search_center": {"latitude": latitude, "longitude": longitude},
                "place_type": place_type,
                "places": results,
            },
            indent=2,
        )
    except Exception as e:
        return json.dumps({"error": f"Failed to search nearby places: {str(e)}"})


def generate_destination_artwork(
    prompt: str,
    tool_context: ToolContext,
) -> str:
    """Generates scenic travel artwork or a postcard image for a destination using Gemini image generation, saves it as an artifact, uploads it to Cloud Storage, and returns its public URL.

    Args:
        prompt: Detailed description of the travel destination artwork to generate (e.g. 'A vibrant postcard of Kyoto Japan during cherry blossom season').
        tool_context: Injected ADK ToolContext used to save artifacts.

    Returns:
        JSON string containing the public https URL of the uploaded image and artifact details.
    """
    try:
        client = genai.Client(vertexai=True, project=FIRESTORE_PROJECT, location="global")
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite-image",
            contents=prompt.strip(),
        )

        image_bytes = None
        mime_type = "image/jpeg"
        if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if getattr(part, "inline_data", None) and part.inline_data.data:
                    image_bytes = part.inline_data.data
                    mime_type = part.inline_data.mime_type or "image/jpeg"
                    break

        if not image_bytes:
            return json.dumps({"error": "No image data returned from model."})

        ext = "jpg" if "jpeg" in mime_type.lower() else "png"
        filename = f"destination_artwork_{uuid.uuid4().hex[:8]}.{ext}"

        # 1. Save as artifact in Playground via tool_context
        artifact_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
        tool_context.save_artifact(filename=filename, artifact=artifact_part)

        # 2. Upload image bytes directly to public Cloud Storage bucket
        creds, _ = google.auth.default()
        if hasattr(creds, "with_scopes"):
            creds = creds.with_scopes(["https://www.googleapis.com/auth/cloud-platform"])
        storage_client = storage.Client(project=FIRESTORE_PROJECT, credentials=creds)
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(filename)
        blob.upload_from_string(image_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{filename}"

        return json.dumps(
            {
                "status": "success",
                "message": "Image generated, saved as artifact, and uploaded to Cloud Storage successfully.",
                "image_url": public_url,
                "artifact_filename": filename,
            },
            indent=2,
        )
    except Exception as e:
        return json.dumps({"error": f"Failed to generate destination artwork: {str(e)}"})


def generate_destination_video(
    prompt: str,
    tool_context: ToolContext,
) -> str:
    """Generates a short video clip for a travel destination or activity using Google's Omni model (gemini-omni-flash-preview) in the global region, saves it as an artifact, uploads it to Cloud Storage, and returns its public URL.

    Args:
        prompt: Detailed description of the travel destination video clip to generate (e.g. 'A 3-second scenic clip of Kyoto Japan cherry blossoms falling').
        tool_context: Injected ADK ToolContext used to save artifacts.

    Returns:
        JSON string containing the public https URL of the uploaded video and artifact details.
    """
    try:
        client = genai.Client(vertexai=True, project=FIRESTORE_PROJECT, location="global")
        
        # Generate video using gemini-omni-flash-preview in the global region
        res = client.interactions.create(
            model="gemini-omni-flash-preview",
            input=prompt.strip(),
        )

        video_bytes = None
        mime_type = "video/mp4"

        if hasattr(res, "output_video") and res.output_video and getattr(res.output_video, "data", None):
            data = res.output_video.data
            video_bytes = base64.b64decode(data) if isinstance(data, str) else bytes(data)
            if getattr(res.output_video, "mime_type", None):
                mime_type = res.output_video.mime_type
        
        if not video_bytes and hasattr(res, "candidates") and res.candidates and res.candidates[0].content:
            for part in res.candidates[0].content.parts:
                if getattr(part, "inline_data", None) and part.inline_data.data:
                    video_bytes = part.inline_data.data
                    mime_type = part.inline_data.mime_type or "video/mp4"
                    break

        if not video_bytes:
            return json.dumps({"error": "No video data returned from gemini-omni-flash-preview model."})

        ext = "mp4" if "mp4" in mime_type.lower() else "webm"
        filename = f"destination_video_{uuid.uuid4().hex[:8]}.{ext}"

        # 1. Save video with tool_context.save_artifact so it shows up in Playground Artifacts panel
        artifact_part = types.Part.from_bytes(data=video_bytes, mime_type=mime_type)
        tool_context.save_artifact(filename=filename, artifact=artifact_part)

        # 2. Upload video bytes directly to public Cloud Storage bucket
        creds, _ = google.auth.default()
        if hasattr(creds, "with_scopes"):
            creds = creds.with_scopes(["https://www.googleapis.com/auth/cloud-platform"])
        storage_client = storage.Client(project=FIRESTORE_PROJECT, credentials=creds)
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(filename)
        blob.upload_from_string(video_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{filename}"

        return json.dumps(
            {
                "status": "success",
                "message": "Video generated with gemini-omni-flash-preview, saved as artifact, and uploaded to Cloud Storage successfully.",
                "video_url": public_url,
                "artifact_filename": filename,
            },
            indent=2,
        )
    except Exception as e:
        return json.dumps({"error": f"Failed to generate destination video: {str(e)}"})





