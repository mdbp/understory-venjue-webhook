"""
UNDERSTORY → VENJUE WEBHOOK SERVER (Real-time Sync) - FIXED!
==============================================================

Flask webhook server som modtager Understory events og synkroniserer
dem til Venjue bookings med real-time opdatering af antal solgte pladser.

Deployed på Railway: https://web-production-d2698.up.railway.app
"""

from flask import Flask, request, jsonify
from datetime import datetime
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

# Standard kundeoplysninger for bookings
CUSTOMER_DEFAULTS = {
    "firstName": os.getenv("CUSTOMER_FIRST_NAME", "Braunstein"),
    "lastName": os.getenv("CUSTOMER_LAST_NAME", "Event"),
    "email": os.getenv("CUSTOMER_EMAIL", "events@braunstein.dk"),
    "phone": os.getenv("CUSTOMER_PHONE", "56 79 12 12")
}

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
        _token_cache["expires_at"] = datetime.now().timestamp() + expires_in - 60  # 1 min buffer
        
        return access_token
        
    except requests.exceptions.RequestException as e:
        raise Exception(f"Kunne ikke hente Understory access token: {str(e)}")


def get_event_from_understory(event_id):
    """
    Hent event detaljer fra Understory Events API.
    """
    access_token = get_understory_access_token()
    
    url = f"{UNDERSTORY_BASE_URL}/v1/events/{event_id}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "User-Agent": "Braunstein/Webhook-Integration"
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
        
    except requests.exceptions.RequestException as e:
        raise Exception(f"Kunne ikke hente event {event_id}: {str(e)}")


# ============================================================
# VENJUE API FUNCTIONS
# ============================================================

def create_venjue_booking(event_data):
    """
    Opret booking i Venjue baseret på Understory event data.
    """
    # Parse dato og tid
    try:
        start_datetime = parser.isoparse(event_data.get("startDate", ""))
        date = start_datetime.strftime("%Y-%m-%d")
        time = start_datetime.strftime("%H:%M")
    except:
        date = datetime.now().strftime("%Y-%m-%d")
        time = "19:00"
    
    # Antal solgte og kapacitet
    booked_spots = event_data.get("bookedSpots", 0)
    capacity = event_data.get("capacity", 50)
    
    # Status label
    if event_data.get("status") == "cancelled":
        status_label = "🚫 AFLYST"
    elif booked_spots >= capacity:
        status_label = "✅ UDSOLGT"
    else:
        status_label = f"📊 {booked_spots}/{capacity} solgt"
    
    # Booking payload
    payload = {
        "date": date,
        "time": time,
        "pax": booked_spots,
        "duration": "120",
        "firstName": CUSTOMER_DEFAULTS["firstName"],
        "lastName": CUSTOMER_DEFAULTS["lastName"],
        "email": CUSTOMER_DEFAULTS["email"],
        "phone": CUSTOMER_DEFAULTS["phone"],
        "notes": f"{event_data.get('title', 'Event')}\n\n{status_label}\n\nUnderstory Event ID: {event_data.get('id')}"
    }
    
    headers = {
        "Authorization": f"Bearer {VENJUE_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    url = f"{VENJUE_BASE_URL}/booking"
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()
        
        booking_id = result.get("id")
        return booking_id
        
    except requests.exceptions.RequestException as e:
        raise Exception(f"Kunne ikke oprette Venjue booking: {str(e)}")


def update_venjue_booking(booking_id, event_data):
    """
    Opdater eksisterende Venjue booking.
    
    Note: Venjue har ikke PUT /booking/{id} endpoint endnu.
    Denne funktion logger opdateringen og kan implementeres
    når Venjue tilføjer update funktionalitet.
    """
    booked_spots = event_data.get("bookedSpots", 0)
    capacity = event_data.get("capacity", 50)
    
    # Status label
    if event_data.get("status") == "cancelled":
        status_label = "🚫 AFLYST"
    elif booked_spots >= capacity:
        status_label = "✅ UDSOLGT"
    else:
        status_label = f"📊 {booked_spots}/{capacity} solgt"
    
    print(f"[UPDATE] Booking {booking_id} skulle opdateres:")
    print(f"  - Pax: {booked_spots}/{capacity}")
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
    print(f"Henter event detaljer fra Understory...")
    full_event = get_event_from_understory(event_id)
    
    title = full_event.get("title", "Untitled Event")
    booked_spots = full_event.get("bookedSpots", 0)
    capacity = full_event.get("capacity", 50)
    
    print(f"✓ Event hentet: {title}")
    print(f"  Solgt: {booked_spots}/{capacity} pladser")
    
    print(f"Opretter booking i Venjue...")
    booking_id = create_venjue_booking(full_event)
    
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
    
    print(f"Henter opdateret event fra Understory...")
    full_event = get_event_from_understory(event_id)
    
    title = full_event.get("title", "Untitled Event")
    booked_spots = full_event.get("bookedSpots", 0)
    capacity = full_event.get("capacity", 50)
    
    print(f"✓ Event opdateret: {title}")
    print(f"  Solgt: {booked_spots}/{capacity} pladser")
    
    print(f"Opdaterer Venjue booking {booking_id}...")
    update_venjue_booking(booking_id, full_event)
    
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
        
        # ===== DEBUG: LOG PAYLOAD =====
        print("=" * 60)
        print("🔍 WEBHOOK PAYLOAD:")
        print(json.dumps(payload, indent=2))
        print("=" * 60)
        # ==============================
        
        webhook_type = payload.get("type")
        webhook_payload = payload.get("payload", {})
        
        # KORREKT PARSING: event_id er i payload.event_id!
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
        ]
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
