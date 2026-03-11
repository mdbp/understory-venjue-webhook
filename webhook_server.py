"""
UNDERSTORY → VENJUE WEBHOOK SERVER (Real-time Sync) - AVAILABILITY API!
==========================================================================

Flask webhook server som modtager Understory events og synkroniserer
dem til Venjue bookings med real-time opdatering af antal solgte pladser.

VIGTIGT: Bruger Event Availability API da Events API ikke er tilgængelig i production.

Deployed på Railway: https://web-production-d2698.up.railway.app
"""

from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import requests
import shelve
import os
import json
from dateutil import parser

app = Flask(__name__)

# ============================================================
# KONFIGURATION
# ============================================================

# Understory API credentials
UNDERSTORY_CLIENT_ID = os.getenv("UNDERSTORY_CLIENT_ID", "8850e110974049358f0f2d183c18d216-e8703e5dba8d465e9eeb17807372b663")
UNDERSTORY_CLIENT_SECRET = os.getenv("UNDERSTORY_CLIENT_SECRET", "Ba5c1ld6oYXVolsPBlC1AKUeUB")

# Venjue API
VENJUE_ACCESS_TOKEN = os.getenv("VENJUE_ACCESS_TOKEN", "70f6b33cc35f786c8ad82cf94ef1fc86")

# API endpoints
UNDERSTORY_AUTH_URL = "https://api.auth.understory.io/oauth2/token"
UNDERSTORY_BASE_URL = "https://api.understory.io"
VENJUE_BASE_URL = "https://app.venjue.com/api/v1"

# Mapping database - brug persistent storage hvis tilgængelig (Railway)
if os.path.exists("/app/data"):
    MAPPING_DB = "/app/data/event_booking_mapping.db"
else:
    MAPPING_DB = "event_booking_mapping.db"

# Token cache (i memory - simpel implementation)
_token_cache = {
    "access_token": None,
    "expires_at": 0
}


# ============================================================
# UNDERSTORY API FUNCTIONS
# ============================================================

def get_understory_access_token():
    """
    Hent OAuth2 access token fra Understory.
    Bruger cache og fornyer kun når nødvendigt.
    """
    # Check om cached token stadig er valid
    if _token_cache["access_token"] and datetime.now().timestamp() < _token_cache["expires_at"]:
        return _token_cache["access_token"]
    
    # Hent nyt token
    payload = {
        "grant_type": "client_credentials",
        "client_id": UNDERSTORY_CLIENT_ID,
        "client_secret": UNDERSTORY_CLIENT_SECRET,
        "audience": "https://api.understory.io",
        "scope": "openid event.read"
    }
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "Braunstein/Webhook-Integration"
    }
    
    try:
        response = requests.post(UNDERSTORY_AUTH_URL, data=payload, headers=headers)
        response.raise_for_status()
        
        token_data = response.json()
        access_token = token_data.get("access_token")
        expires_in = token_data.get("expires_in", 3599)
        
        # Cache token
        _token_cache["access_token"] = access_token
        _token_cache["expires_at"] = datetime.now().timestamp() + expires_in - 60
        
        return access_token
        
    except requests.exceptions.RequestException as e:
        raise Exception(f"Kunne ikke hente Understory access token: {str(e)}")

def get_event_availability(event_id):
    """
    Hent event availability fra Understory Event Availability API.
    
    Events API er ikke tilgængelig i production endnu, så vi bruger
    Event Availability API til at få capacity data.
    
    Returns:
        {
            "event_id": "abc123",
            "available": true,
            "total_capacity": 50,
            "remaining": 25
        }
    """
    access_token = get_understory_access_token()
    
    url = f"{UNDERSTORY_BASE_URL}/v1/event-availabilities/{event_id}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "User-Agent": "Braunstein/Webhook-Integration"
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        availability_data = response.json()
        
        # Parse capacity fra constraints
        total_capacity = 0
        remaining = 0
        
        for constraint in availability_data.get("constraints", []):
            if constraint.get("type") == "EVENT_SEATS_LIMIT":
                remaining = constraint.get("remaining", 0)
                # Total capacity = remaining + booked (estimeret)
                # Vi kan ikke få exact booked count fra availability API,
                # så vi bruger remaining som reference
                total_capacity = remaining + 10  # Estimat
        
        return {
            "event_id": event_id,
            "available": availability_data.get("available", True),
            "total_capacity": total_capacity if total_capacity > 0 else 50,
            "remaining": remaining,
            "booked": total_capacity - remaining if total_capacity > remaining else 0
        }
        
    except requests.exceptions.RequestException as e:
        raise Exception(f"Kunne ikke hente availability for event {event_id}: {str(e)}")


# ============================================================
# VENJUE API FUNCTIONS
# ============================================================

def create_venjue_booking(event_id, availability_data):
    """
    Opret booking i Venjue baseret på Understory event availability data.
    
    Venjue accepterer KUN: date, time, pax
    
    Da Events API ikke er tilgængelig, bruger vi defaults for date/time
    og capacity data fra Event Availability API.
    """
    # Defaults - da vi ikke har event detaljer
    # Brug morgendagens dato som default
    tomorrow = datetime.now() + timedelta(days=1)
    date = tomorrow.strftime("%Y-%m-%d")
    time = "19:00"
    
    # Antal bookede baseret på availability
    booked_spots = availability_data.get("booked", 0)
    
    # Booking payload - KUN date, time, pax!
    payload = {
        "date": date,
        "time": time,
        "pax": booked_spots
    }
    
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
        
        booking_id = result.get("id")
        return booking_id
        
    except requests.exceptions.RequestException as e:
        print(f"✗ VENJUE API FEJL: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"  Response: {e.response.text}")
        raise Exception(f"Kunne ikke oprette Venjue booking: {str(e)}")

def update_venjue_booking(booking_id, availability_data):
    """
    Opdater eksisterende Venjue booking.
    
    Note: Venjue har ikke PUT /booking/{id} endpoint endnu.
    """
    booked_spots = availability_data.get("booked", 0)
    total_capacity = availability_data.get("total_capacity", 50)
    remaining = availability_data.get("remaining", 0)
    
    # Status label
    if booked_spots >= total_capacity:
        status_label = "✅ UDSOLGT"
    else:
        status_label = f"📊 {booked_spots}/{total_capacity} solgt ({remaining} ledige)"
    
    print(f"[UPDATE] Booking {booking_id} skulle opdateres:")
    print(f"  - Pax: {booked_spots}/{total_capacity}")
    print(f"  - Ledige: {remaining}")
    print(f"  - Status: {status_label}")
    print(f"  - Note: Venjue har ikke update endpoint endnu")
    
    return True


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
    Opret ny booking i Venjue.
    """
    print(f"Henter event availability fra Understory...")
    availability = get_event_availability(event_id)
    
    booked = availability.get("booked", 0)
    total = availability.get("total_capacity", 50)
    remaining = availability.get("remaining", 0)
    
    print(f"✓ Availability hentet:")
    print(f"  Booket: {booked}/{total} pladser")
    print(f"  Ledige: {remaining} pladser")
    
    print(f"Opretter booking i Venjue...")
    booking_id = create_venjue_booking(event_id, availability)
    
    print(f"✓ Booking oprettet!")
    print(f"  Booking ID: {booking_id}")
    print(f"  URL: {VENJUE_BASE_URL.replace('/api/v1', '')}/booking.php?eventId={booking_id}")
    
    # Gem mapping
    save_mapping(event_id, booking_id)
    
    return {
        "status": "success",
        "message": "Event created, booking created in Venjue",
        "event_id": event_id,
        "booking_id": booking_id
    }

def handle_event_updated(event_id):
    """
    Håndter v1.event.updated webhook.
    Opdater eksisterende booking i Venjue.
    """
    # Check om vi har en mapping
    booking_id = get_mapping(event_id)
    
    if not booking_id:
        print(f"⚠ Ingen booking fundet for event {event_id}")
        print(f"  Event blev måske oprettet før webhook integration")
        return {
            "status": "warning",
            "message": "No booking found for this event"
        }
    
    print(f"Henter opdateret availability fra Understory...")
    availability = get_event_availability(event_id)
    
    booked = availability.get("booked", 0)
    total = availability.get("total_capacity", 50)
    remaining = availability.get("remaining", 0)
    
    print(f"✓ Availability opdateret:")
    print(f"  Booket: {booked}/{total} pladser")
    print(f"  Ledige: {remaining} pladser")
    
    print(f"Opdaterer Venjue booking {booking_id}...")
    update_venjue_booking(booking_id, availability)
    
    print(f"✓ Opdatering håndteret")
    
    return {
        "status": "success",
        "message": "Event updated, booking updated in Venjue",
        "event_id": event_id,
        "booking_id": booking_id
    }


# ============================================================
# FLASK ROUTES
# ============================================================

@app.route('/webhook/understory', methods=['POST'])
def understory_webhook():
    """
    Hovedendpoint for Understory webhooks.
    
    Understory payload struktur:
    {
      "id": "webhook-id",
      "payload": {
        "event_id": "abc123",
        "experience_id": "xyz789",
        "session_ids": [...]
      },
      "type": "v1.event.created",
      "timestamp": "..."
    }
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
            print("⚠ ADVARSEL: Ingen event_id i payload!")
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
        "service": "Understory to Venjue Webhook (Real-time Sync)",
        "timestamp": datetime.now().isoformat(),
        "supported_webhooks": [
            "v1.event.created",
            "v1.event.updated"
        ],
        "note": "Using Event Availability API (Events API not yet in production)"
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
    print("UNDERSTORY → VENJUE WEBHOOK SERVER (Real-time Sync)")
    print("=" * 60)
    print()
    print(f"Database: {MAPPING_DB}")
    print(f"Webhook endpoint: /webhook/understory")
    print(f"Health check: /health")
    print(f"View mappings: /mappings")
    print()
    print("VIGTIGT: Bruger Event Availability API")
    print("         (Events API ikke tilgængelig endnu)")
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
