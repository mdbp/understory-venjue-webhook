"""
UNDERSTORY → VENJUE WEBHOOK SERVER - PRODUCTION VERSION
========================================================

Flask webhook server der modtager Understory events og synkroniserer
dem til Venjue bookings.

KORREKT IMPLEMENTATION baseret på Understory API dokumentation:
- OAuth scope: event.read
- Required headers: Accept, User-Agent
- Sessions parsing: start_time/end_time (local time, no timezone)
- Capacity: total - reserved

Deployed på Railway: https://web-production-d2698.up.railway.app
"""

from flask import Flask, request, jsonify
from datetime import datetime
import requests
import shelve
import os
import json

app = Flask(__name__)

# ============================================================
# KONFIGURATION
# ============================================================

# Understory API credentials
UNDERSTORY_CLIENT_ID = os.getenv("UNDERSTORY_CLIENT_ID", "8850e110974049358f0f2d183c18d216-e8703e5dba8d465e9eeb17807372b663")
UNDERSTORY_CLIENT_SECRET = os.getenv("UNDERSTORY_CLIENT_SECRET", "Ba5c1ld6oYXVolsPBlC1AKUeUB")

# Venjue API
VENJUE_ACCESS_TOKEN = os.getenv("VENJUE_ACCESS_TOKEN", "70f6b33cc35f786c8ad82cf94ef1fc86")
VENJUE_BASE_URL = "https://app.venjue.com/api/v1"

# Default customer info
CUSTOMER_EMAIL = os.getenv("CUSTOMER_EMAIL", "events@braunstein.dk")

# Mapping database - brug persistent storage hvis tilgængelig (Railway)
if os.path.exists("/app/data"):
    MAPPING_DB = "/app/data/event_booking_mapping.db"
else:
    MAPPING_DB = "event_booking_mapping.db"


# ============================================================
# UNDERSTORY API FUNCTIONS
# ============================================================

def get_understory_token():
    """
    Hent OAuth2 access token fra Understory.
    
    KORREKT IMPLEMENTATION ifølge docs:
    - Scope: event.read (UDEN openid)
    - User-Agent header REQUIRED
    """
    auth_url = "https://api.auth.understory.io/oauth2/token"
    
    data = {
        "grant_type": "client_credentials",
        "client_id": UNDERSTORY_CLIENT_ID,
        "client_secret": UNDERSTORY_CLIENT_SECRET,
        "audience": "https://api.understory.io",
        "scope": "event.read"  # ← Korrekt scope ifølge docs
    }
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "Braunstein-Venjue-Integration/1.0"  # ← REQUIRED!
    }
    
    response = requests.post(auth_url, data=data, headers=headers)
    response.raise_for_status()
    
    token_data = response.json()
    return token_data["access_token"]


def get_event_data(event_id):
    """
    Hent event data fra Understory API.
    
    KORREKT IMPLEMENTATION ifølge docs:
    - Accept header REQUIRED
    - User-Agent header REQUIRED
    - Returns event med sessions array
    """
    # Get fresh token
    access_token = get_understory_token()
    
    # API endpoint
    api_url = f"https://api.understory.io/v1/events/{event_id}"
    
    # Headers - ALLE required ifølge docs!
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",  # ← REQUIRED!
        "User-Agent": "Braunstein-Venjue-Integration/1.0"  # ← REQUIRED!
    }
    
    print(f"  → Kalder Understory API: {api_url}")
    
    # Make request
    response = requests.get(api_url, headers=headers)
    
    # Handle specific errors
    if response.status_code == 403:
        raise Exception("Forbidden - check OAuth scopes and permissions")
    elif response.status_code == 404:
        # Check if it's a deleted event
        try:
            error_data = response.json()
            if "deleted" in error_data.get("message", "").lower():
                raise Exception(f"Event {event_id} has been deleted in Understory")
        except:
            pass
        raise Exception(f"Event {event_id} not found")
    
    response.raise_for_status()
    
    return response.json()


def extract_venjue_data(event_data):
    """
    Extract date, time, pax fra Understory event data.
    
    KORREKT PARSING ifølge docs:
    - sessions[0].start_time: "2024-01-15T10:00:00" (LOCAL time, no timezone)
    - capacity.total - capacity.reserved = available seats
    
    Args:
        event_data: Response from GET /v1/events/{eventId}
        
    Returns:
        dict: {date, time, pax} for Venjue API
    """
    # Get first session (der er altid præcis én session ifølge Michael)
    if not event_data.get("sessions"):
        raise Exception("Event has no sessions")
    
    session = event_data["sessions"][0]
    
    # Parse start_time (LOCAL time uden timezone!)
    # Format fra API: "2024-01-15T10:00:00"
    start_time = session["start_time"]  # String: "YYYY-MM-DDTHH:MM:SS"
    
    # Split til date og time
    date_part, time_part = start_time.split("T")  # "DD-MM-YYYY" Danish format, "10:00:00"
    
    # Extract time without seconds
    time_hh_mm = time_part[:5]  # "10:00"

    
    # Get capacity (available seats = total - reserved)
    capacity_total = event_data["capacity"]["total"]
    capacity_reserved = event_data["capacity"]["reserved"]
    available_seats = capacity_total - capacity_reserved
    
    return {
        "date": date_part,      # "DD-MM-YYYY" Danish format
        "time": time_hh_mm,     # "10:00"
        "pax": available_seats,  # integer
        "title": "Braunstein Event",
        "customer": {"email": CUSTOMER_EMAIL, "phone": "56791212", "firstName": "Braunstein", "lastName": "Event"}
    }


# ============================================================
# VENJUE API FUNCTIONS
# ============================================================

def create_venjue_booking(payload):
    """
    Opret booking i Venjue.
    
    Payload format: {"date": "2026-03-12", "time": "19:00", "pax": 20}
    """
    headers = {
        "Authorization": f"Bearer {VENJUE_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    url = f"{VENJUE_BASE_URL}/booking"
    
    print(f"  → Sender til Venjue: {payload}")
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()
        print(f"✓ Venjue response: {result}")
        
        booking_id = result.get("id")
        return booking_id
        
    except requests.exceptions.RequestException as e:
        print(f"✗ VENJUE API FEJL: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"  Response: {e.response.text}")
        raise Exception(f"Kunne ikke oprette Venjue booking: {str(e)}")


# ============================================================
# MAPPING DATABASE FUNCTIONS
# ============================================================

def save_mapping(event_id, booking_id):
    """Gem mapping mellem event_id og booking_id."""
    with shelve.open(MAPPING_DB) as db:
        db[event_id] = booking_id


def get_mapping(event_id):
    """Hent booking_id for et event_id."""
    with shelve.open(MAPPING_DB) as db:
        return db.get(event_id)


def get_all_mappings():
    """Hent alle mappings (til debug)."""
    with shelve.open(MAPPING_DB) as db:
        return dict(db)


# ============================================================
# WEBHOOK HANDLERS
# ============================================================

def handle_event_created(event_id):
    """
    Håndter v1.event.created webhook.
    
    KORREKT FLOW:
    1. Hent event data fra Understory API
    2. Extract date/time/pax fra sessions array
    3. Opret booking i Venjue
    4. Gem mapping
    """
    print(f"Henter event data for: {event_id}")
    
    try:
        # 1. Hent event data fra Understory
        event_data = get_event_data(event_id)
        print(f"✓ Event data hentet!")
        print(f"  State: {event_data['state']}")
        print(f"  Sessions: {len(event_data['sessions'])}")
        
        # 2. Extract Venjue data
        venjue_payload = extract_venjue_data(event_data)
        print(f"✓ Venjue payload: {venjue_payload}")
        
        # 3. Opret booking i Venjue
        print(f"Opretter booking i Venjue...")
        booking_id = create_venjue_booking(venjue_payload)
        
        print(f"✓ Booking oprettet!")
        print(f"  Booking ID: {booking_id}")
        print(f"  URL: {VENJUE_BASE_URL.replace('/api/v1', '')}/booking.php?eventId={booking_id}")
        
        # 4. Gem mapping
        save_mapping(event_id, booking_id)
        
        return {
            "status": "success",
            "message": "Booking created successfully",
            "event_id": event_id,
            "booking_id": booking_id,
            "venjue_data": venjue_payload
        }
        
    except Exception as e:
        print(f"✗ FEJL: {str(e)}")
        raise


def handle_event_updated(event_id):
    """
    Håndter v1.event.updated webhook.
    
    TODO: Implementer opdatering af eksisterende booking.
    For nu: logger opdatering.
    """
    # Check om vi har en mapping
    booking_id = get_mapping(event_id)
    
    if not booking_id:
        print(f"⚠️  Ingen booking fundet for event {event_id}")
        print(f"   Event blev måske oprettet før webhook integration")
        return {
            "status": "warning",
            "message": "No booking found for this event"
        }
    
    print(f"⚠️  Event opdateret")
    print(f"   Event ID: {event_id}")
    print(f"   Booking ID: {booking_id}")
    print(f"   Note: Opdatering af bookings er ikke implementeret endnu")
    
    return {
        "status": "success",
        "message": "Event updated - manual update required in Venjue",
        "event_id": event_id,
        "booking_id": booking_id,
        "warning": "Booking update not yet implemented"
    }


# ============================================================
# FLASK ROUTES
# ============================================================

@app.route('/webhook/understory', methods=['POST'])
def understory_webhook():
    """
    Hovedendpoint for Understory webhooks.
    
    PRODUCTION VERSION: Kalder Understory API med korrekte headers.
    """
    try:
        # Parse webhook payload
        payload = request.get_json()
        
        webhook_type = payload.get("type")
        webhook_payload = payload.get("payload", {})
        
        # event_id er i payload.event_id
        event_id = webhook_payload.get("event_id")
        
        print("=" * 60)
        print(f"WEBHOOK MODTAGET: {webhook_type}")
        print(f"Event ID: {event_id}")
        print("=" * 60)
        
        if not event_id:
            print("⚠️  ADVARSEL: Ingen event_id i payload!")
            return jsonify({
                "status": "error",
                "error": "Missing event_id in payload"
            }), 400
        
        # Route til korrekt handler
        if webhook_type == "v1.event.created":
            result = handle_event_created(event_id)
        elif webhook_type == "v1.event.updated":
            result = handle_event_updated(event_id)
        elif webhook_type == "v1.event.cancelled":
            result = handle_event_updated(event_id)
        else:
            result = {
                "status": "ignored",
                "message": f"Webhook type {webhook_type} not handled"
            }
        
        print("=" * 60)
        print()
        
        return jsonify(result), 200
        
    except Exception as e:
        print(f"✗ FEJL: {str(e)}")
        import traceback
        traceback.print_exc()
        print("=" * 60)
        print()
        
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "service": "Understory to Venjue Webhook - PRODUCTION",
        "timestamp": datetime.now().isoformat(),
        "supported_webhooks": [
            "v1.event.created",
            "v1.event.updated"
        ],
        "api_implementation": "Correct headers + scope (event.read)",
        "note": "Using Understory Events API with proper OAuth and headers"
    }), 200


@app.route('/mappings', methods=['GET'])
def mappings():
    """Se alle event → booking mappings (til debug)."""
    all_mappings = get_all_mappings()
    return jsonify({
        "count": len(all_mappings),
        "mappings": all_mappings
    }), 200


# ============================================================
# START SERVER
# ============================================================

if __name__ == '__main__':
    print("=" * 60)
    print("UNDERSTORY → VENJUE WEBHOOK SERVER - PRODUCTION")
    print("=" * 60)
    print()
    print(f"Database: {MAPPING_DB}")
    print(f"Webhook endpoint: /webhook/understory")
    print(f"Health check: /health")
    print(f"View mappings: /mappings")
    print()
    print("✓ OAuth scope: event.read")
    print("✓ Headers: Accept + User-Agent (REQUIRED)")
    print("✓ API: https://api.understory.io/v1/events/{eventId}")
    print()
    print("Serveren starter...")
    print("=" * 60)
    
    # Port: Brug Railway's PORT env var hvis den findes, ellers 5000
    port = int(os.getenv('PORT', 5000))
    
    # Start Flask server
    app.run(
        host='0.0.0.0',
        port=port,
        debug=os.getenv('DEBUG', 'False').lower() == 'true'
    )
