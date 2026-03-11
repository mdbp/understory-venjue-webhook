"""
UNDERSTORY → VENJUE WEBHOOK SERVER - WORKAROUND VERSION!
==========================================================

VIGTIGT: Understory APIs virker ikke (404), så vi bruger defaults.

Flask webhook server som modtager Understory events og synkroniserer
dem til Venjue bookings.

WORKAROUND: Opretter bookings med default dato/tid uden at hente fra Understory.

Deployed på Railway: https://web-production-d2698.up.railway.app
"""

from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import requests
import shelve
import os
import json

app = Flask(__name__)

# ============================================================
# KONFIGURATION
# ============================================================

# Understory API credentials (bruges kun til OAuth2)
UNDERSTORY_CLIENT_ID = os.getenv("UNDERSTORY_CLIENT_ID", "8850e110974049358f0f2d183c18d216-e8703e5dba8d465e9eeb17807372b663")
UNDERSTORY_CLIENT_SECRET = os.getenv("UNDERSTORY_CLIENT_SECRET", "Ba5c1ld6oYXVolsPBlC1AKUeUB")

# Venjue API
VENJUE_ACCESS_TOKEN = os.getenv("VENJUE_ACCESS_TOKEN", "70f6b33cc35f786c8ad82cf94ef1fc86")

# API endpoints
VENJUE_BASE_URL = "https://app.venjue.com/api/v1"

# Mapping database - brug persistent storage hvis tilgængelig (Railway)
if os.path.exists("/app/data"):
    MAPPING_DB = "/app/data/event_booking_mapping.db"
else:
    MAPPING_DB = "event_booking_mapping.db"


# ============================================================
# VENJUE API FUNCTIONS
# ============================================================

def create_venjue_booking_direct(payload):
    """
    Opret booking direkte i Venjue med payload.
    
    Payload format: {"date": "2026-03-12", "time": "19:00", "pax": 0}
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
# WEBHOOK HANDLERS - WORKAROUND VERSION
# ============================================================

def handle_event_created(event_id):
    """
    Håndter v1.event.created webhook.
    
    WORKAROUND: Understory APIs virker ikke (404), så vi opretter
    booking med default værdier uden at hente fra Understory.
    """
    print(f"⚠️  WORKAROUND: Opretter booking uden Understory API data")
    print(f"   Reason: Understory APIs returnerer 404")
    
    # Default booking data
    tomorrow = datetime.now() + timedelta(days=1)
    
    payload = {
        "date": tomorrow.strftime("%Y-%m-%d"),
        "time": "19:00",
        "pax": 0  # Start med 0 bookede - skal opdateres manuelt
    }
    
    print(f"✓ Bruger defaults:")
    print(f"  Dato: {payload['date']}")
    print(f"  Tid: {payload['time']}")
    print(f"  Pax: {payload['pax']}")
    
    print(f"Opretter booking i Venjue...")
    booking_id = create_venjue_booking_direct(payload)
    
    print(f"✓ Booking oprettet!")
    print(f"  Booking ID: {booking_id}")
    print(f"  URL: {VENJUE_BASE_URL.replace('/api/v1', '')}/booking.php?eventId={booking_id}")
    print(f"  ⚠️  HUSK: Opdater dato/tid/pax manuelt i Venjue!")
    
    # Gem mapping
    save_mapping(event_id, booking_id)
    
    return {
        "status": "success",
        "message": "Booking created with defaults (Understory APIs unavailable)",
        "event_id": event_id,
        "booking_id": booking_id,
        "warning": "Update date/time/pax manually in Venjue"
    }

def handle_event_updated(event_id):
    """
    Håndter v1.event.updated webhook.
    
    WORKAROUND: Logger opdatering men kan ikke hente data fra Understory.
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
    
    print(f"⚠️  WORKAROUND: Event opdateret")
    print(f"   Event ID: {event_id}")
    print(f"   Booking ID: {booking_id}")
    print(f"   Note: Kan ikke hente opdateret data fra Understory (404)")
    print(f"   Action: Opdater booking manuelt i Venjue")
    
    return {
        "status": "success",
        "message": "Event updated - manual update required in Venjue",
        "event_id": event_id,
        "booking_id": booking_id,
        "warning": "Understory APIs unavailable - update manually"
    }


# ============================================================
# FLASK ROUTES
# ============================================================

@app.route('/webhook/understory', methods=['POST'])
def understory_webhook():
    """
    Hovedendpoint for Understory webhooks.
    
    WORKAROUND VERSION: Opretter bookings uden at kalde Understory APIs.
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
        "service": "Understory to Venjue Webhook (WORKAROUND)",
        "timestamp": datetime.now().isoformat(),
        "supported_webhooks": [
            "v1.event.created",
            "v1.event.updated"
        ],
        "warning": "Using defaults - Understory APIs return 404",
        "note": "Bookings created with tomorrow's date, 19:00, pax=0"
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
    print("UNDERSTORY → VENJUE WEBHOOK SERVER (WORKAROUND)")
    print("=" * 60)
    print()
    print(f"Database: {MAPPING_DB}")
    print(f"Webhook endpoint: /webhook/understory")
    print(f"Health check: /health")
    print(f"View mappings: /mappings")
    print()
    print("⚠️  WORKAROUND MODE:")
    print("   - Understory APIs returnerer 404")
    print("   - Bookings oprettes med defaults:")
    print("     * Dato: I morgen")
    print("     * Tid: 19:00")
    print("     * Pax: 0")
    print("   - HUSK at opdatere manuelt i Venjue!")
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
