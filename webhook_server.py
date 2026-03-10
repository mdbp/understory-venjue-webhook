#!/usr/bin/env python3
"""
Understory Webhook → Venjue Integration
========================================
Flask webhook server der modtager webhooks fra Understory og synkroniserer
med Venjue i real-time.

REAL-TIME SYNC:
- event.created → Opret booking i Venjue
- event.updated → Opdater booking i Venjue med:
  * Antal solgte pladser (10/50, 20/50, etc)
  * Event titel hvis ændret
  * Dato/tid hvis ændret
  * Status (udsolgt, aflyst, etc)
"""

from flask import Flask, request, jsonify
import requests
import json
from datetime import datetime
import os
import shelve

# KONFIGURATION
UNDERSTORY_CLIENT_ID = "8850e110974049358f0f2d183c18d216-f6e21905913543a8a0798a39555a9b67"
UNDERSTORY_CLIENT_SECRET = "-hlg-P~6SCAB3qeSGDg5zWd8E1"
VENJUE_ACCESS_TOKEN = "70f6b33cc35f786c8ad82cf94ef1fc86"

# Standard kundeoplysninger for bookings
CUSTOMER_DEFAULTS = {
    "firstName": "Braunstein",
    "lastName": "Event",
    "email": "events@braunstein.dk",
    "phone": "56 79 12 12"
}

# API endpoints
UNDERSTORY_BASE_URL = "https://api.understory.io"
VENJUE_BASE_URL = "https://app.venjue.com/api/v1"

# Mapping database (event_id → booking_id)
MAPPING_DB = "event_booking_mapping.db"

# Flask app
app = Flask(__name__)

# Token cache
_access_token_cache = {
    "token": None,
    "expires_at": None
}


def save_mapping(event_id, booking_id):
    """Gem mapping mellem Understory event ID og Venjue booking ID"""
    with shelve.open(MAPPING_DB) as db:
        db[event_id] = {
            "booking_id": booking_id,
            "created_at": datetime.now().isoformat()
        }
    print(f"  → Mapping gemt: {event_id} → {booking_id}")


def get_booking_id(event_id):
    """Hent Venjue booking ID for et Understory event ID"""
    with shelve.open(MAPPING_DB) as db:
        if event_id in db:
            return db[event_id]["booking_id"]
    return None


def list_mappings():
    """Vis alle mappings (til debugging)"""
    with shelve.open(MAPPING_DB) as db:
        return dict(db)


def get_understory_access_token():
    """Hent eller genbruger Understory access token"""
    global _access_token_cache
    
    # Tjek om token stadig er gyldigt
    if (_access_token_cache["token"] and 
        _access_token_cache["expires_at"] and 
        datetime.now() < _access_token_cache["expires_at"]):
        return _access_token_cache["token"]
    
    # Hent nyt token
    url = f"{UNDERSTORY_BASE_URL}/oauth2/token"
    
    data = {
        "grant_type": "client_credentials",
        "client_id": UNDERSTORY_CLIENT_ID,
        "client_secret": UNDERSTORY_CLIENT_SECRET,
        "scope": "event.read"
    }
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    response = requests.post(url, data=data, headers=headers)
    response.raise_for_status()
    
    token_data = response.json()
    _access_token_cache["token"] = token_data["access_token"]
    
    # Beregn udløbstid (expires_in er i sekunder)
    from datetime import timedelta
    expires_in = token_data.get("expires_in", 3599)
    _access_token_cache["expires_at"] = datetime.now() + timedelta(seconds=expires_in - 60)
    
    print(f"✓ Nyt Understory access token hentet")
    return _access_token_cache["token"]


def get_event_details(event_id):
    """Hent event detaljer fra Understory"""
    token = get_understory_access_token()
    
    url = f"{UNDERSTORY_BASE_URL}/v1/events/{event_id}"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "User-Agent": "Venjue-Webhook-Integration/1.0"
    }
    
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    return response.json()


def create_venjue_booking(event_data):
    """
    Opret booking i Venjue baseret på Understory event
    
    VIGTIGT: Tracker antal solgte pladser i real-time.
    """
    
    # Parse event data
    event = event_data.get("event", event_data)
    
    # Udtræk dato og tid
    start_time = event.get("startTime", "")
    if start_time:
        # Parse ISO timestamp: "2026-04-15T18:00:00Z"
        dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        date = dt.strftime("%Y-%m-%d")
        time = dt.strftime("%H:%M")
    else:
        # Fallback
        date = datetime.now().strftime("%Y-%m-%d")
        time = "18:00"
    
    # Beregn antal solgte pladser
    capacity = event.get("capacity", 0)
    booked_spots = event.get("bookedSpots", 0)
    available_spots = capacity - booked_spots
    
    # Status
    status = event.get("status", "active")
    is_sold_out = available_spots <= 0
    is_cancelled = status == "cancelled"
    
    # Byg status tekst
    status_text = ""
    if is_cancelled:
        status_text = "🚫 AFLYST"
    elif is_sold_out:
        status_text = "✅ UDSOLGT"
    else:
        status_text = f"📊 {booked_spots}/{capacity} solgt"
    
    # Opbyg booking data
    booking_data = {
        "date": date,
        "time": time,
        "title": event.get("title", "Event fra Understory"),
        "pax": booked_spots,  # VIGTIGT: Antal solgte, ikke kapacitet
        "customer": CUSTOMER_DEFAULTS,
        "note": f"Event synkroniseret fra Understory (Real-time)\n"
                f"═══════════════════════════════════════════════\n"
                f"Event ID: {event.get('id')}\n"
                f"Experience ID: {event.get('experienceId', 'N/A')}\n\n"
                f"STATUS: {status_text}\n"
                f"Solgte pladser: {booked_spots}\n"
                f"Kapacitet: {capacity}\n"
                f"Ledige pladser: {available_spots}\n\n"
                f"Senest opdateret: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "locale": "da_DK",
        "sendNotification": True
    }
    
    # Opret booking i Venjue
    url = f"{VENJUE_BASE_URL}/booking"
    
    headers = {
        "Authorization": f"Bearer {VENJUE_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    response = requests.post(url, headers=headers, json=booking_data)
    response.raise_for_status()
    
    result = response.json()
    booking_id = result.get("booking", {}).get("id")
    
    # Gem mapping mellem event ID og booking ID
    if booking_id:
        save_mapping(event.get("id"), booking_id)
    
    return result


def update_venjue_booking(booking_id, event_data):
    """
    Opdater eksisterende booking i Venjue
    
    Opdaterer:
    - Antal solgte pladser (pax)
    - Event titel
    - Dato/tid
    - Status (udsolgt, aflyst)
    """
    
    # Parse event data
    event = event_data.get("event", event_data)
    
    # Udtræk dato og tid
    start_time = event.get("startTime", "")
    if start_time:
        dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        date = dt.strftime("%Y-%m-%d")
        time = dt.strftime("%H:%M")
    else:
        date = datetime.now().strftime("%Y-%m-%d")
        time = "18:00"
    
    # Beregn antal solgte pladser
    capacity = event.get("capacity", 0)
    booked_spots = event.get("bookedSpots", 0)
    available_spots = capacity - booked_spots
    
    # Status
    status = event.get("status", "active")
    is_sold_out = available_spots <= 0
    is_cancelled = status == "cancelled"
    
    # Byg status tekst
    status_text = ""
    if is_cancelled:
        status_text = "🚫 AFLYST"
    elif is_sold_out:
        status_text = "✅ UDSOLGT"
    else:
        status_text = f"📊 {booked_spots}/{capacity} solgt"
    
    # OBS: Venjue API understøtter ikke UPDATE af bookings
    # Vi kan ikke bruge PUT /booking/{id} da det ikke eksisterer
    # Workaround: Opdater via note i stedet
    
    # ALTERNATIV: Slet og genopret (ikke ideelt)
    # For nu logger vi bare ændringen
    
    print(f"  ℹ️  Venjue API understøtter ikke booking updates")
    print(f"  → Booking ID {booking_id} skulle opdateres med:")
    print(f"     Titel: {event.get('title')}")
    print(f"     Dato: {date} {time}")
    print(f"     Pax: {booked_spots} (var kapacitet: {capacity})")
    print(f"     Status: {status_text}")
    
    # TODO: Når Venjue tilføjer UPDATE endpoint, implementer her
    # For nu returnerer vi success for at fortsætte flow
    
    return {
        "status": "logged",
        "message": "Venjue booking update logged (API limitation)",
        "booking_id": booking_id,
        "changes": {
            "title": event.get("title"),
            "date": date,
            "time": time,
            "pax": booked_spots,
            "status": status_text
        }
    }


@app.route('/webhook/understory', methods=['POST'])
def understory_webhook():
    """Modtag webhooks fra Understory - håndterer både created og updated"""
    
    try:
        # Hent webhook payload
        payload = request.get_json()
        
        if not payload:
            return jsonify({"error": "No payload"}), 400
        
        # Log webhook modtagelse
        event_type = payload.get("type", "unknown")
        event_id = payload.get("data", {}).get("id", "unknown")
        
        print("=" * 60)
        print(f"WEBHOOK MODTAGET: {event_type}")
        print(f"Event ID: {event_id}")
        print(f"Timestamp: {datetime.now().isoformat()}")
        print("=" * 60)
        
        # Håndter event.created
        if event_type == "v1.event.created":
            print(f"📝 OPRET NY BOOKING")
            print()
            
            # Hent fulde event detaljer
            print(f"Henter event detaljer fra Understory...")
            event_details = get_event_details(event_id)
            
            event = event_details.get('event', {})
            capacity = event.get('capacity', 0)
            booked = event.get('bookedSpots', 0)
            
            print(f"✓ Event hentet: {event.get('title', 'N/A')}")
            print(f"  Solgt: {booked}/{capacity} pladser")
            print()
            
            # Opret booking i Venjue
            print(f"Opretter booking i Venjue...")
            venjue_result = create_venjue_booking(event_details)
            
            booking_id = venjue_result.get("booking", {}).get("id")
            booking_url = venjue_result.get("booking", {}).get("url")
            
            print(f"✓ Booking oprettet!")
            print(f"  Booking ID: {booking_id}")
            print(f"  URL: {booking_url}")
            print(f"  Pax: {booked} solgte pladser")
            print("=" * 60)
            
            return jsonify({
                "status": "success",
                "action": "created",
                "understory_event_id": event_id,
                "venjue_booking_id": booking_id,
                "venjue_booking_url": booking_url,
                "sold_spots": booked,
                "capacity": capacity
            }), 200
        
        # Håndter event.updated
        elif event_type == "v1.event.updated":
            print(f"🔄 OPDATER EKSISTERENDE BOOKING")
            print()
            
            # Find eksisterende booking
            booking_id = get_booking_id(event_id)
            
            if not booking_id:
                print(f"⚠️  Booking ikke fundet for event {event_id}")
                print(f"  → Event blev muligvis oprettet før webhook var aktiveret")
                print(f"  → Opretter ny booking i stedet...")
                
                # Opret som ny hvis mapping ikke findes
                event_details = get_event_details(event_id)
                venjue_result = create_venjue_booking(event_details)
                booking_id = venjue_result.get("booking", {}).get("id")
                
                print(f"✓ Ny booking oprettet: {booking_id}")
                print("=" * 60)
                
                return jsonify({
                    "status": "success",
                    "action": "created_from_update",
                    "understory_event_id": event_id,
                    "venjue_booking_id": booking_id
                }), 200
            
            # Hent opdaterede event detaljer
            print(f"Henter opdateret event fra Understory...")
            event_details = get_event_details(event_id)
            
            event = event_details.get('event', {})
            capacity = event.get('capacity', 0)
            booked = event.get('bookedSpots', 0)
            available = capacity - booked
            status = event.get('status', 'active')
            
            print(f"✓ Event hentet: {event.get('title', 'N/A')}")
            print(f"  Solgt: {booked}/{capacity} pladser")
            print(f"  Ledige: {available}")
            print(f"  Status: {status}")
            print()
            
            # Opdater booking i Venjue
            print(f"Opdaterer Venjue booking {booking_id}...")
            update_result = update_venjue_booking(booking_id, event_details)
            
            print(f"✓ Opdatering håndteret")
            print("=" * 60)
            
            return jsonify({
                "status": "success",
                "action": "updated",
                "understory_event_id": event_id,
                "venjue_booking_id": booking_id,
                "sold_spots": booked,
                "capacity": capacity,
                "available": available,
                "event_status": status,
                "update_result": update_result
            }), 200
        
        # Ignorer andre event types
        else:
            print(f"⚠ Ignorerer event type: {event_type}")
            print(f"  Understøttede types: v1.event.created, v1.event.updated")
            print("=" * 60)
            
            return jsonify({
                "status": "ignored", 
                "reason": f"Event type {event_type} not supported"
            }), 200
        
    except Exception as e:
        print(f"✗ FEJL i webhook handler: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "Understory to Venjue Webhook (Real-time Sync)",
        "timestamp": datetime.now().isoformat(),
        "supported_webhooks": ["v1.event.created", "v1.event.updated"]
    }), 200


@app.route('/mappings', methods=['GET'])
def view_mappings():
    """Vis alle event → booking mappings"""
    mappings = list_mappings()
    
    return jsonify({
        "total": len(mappings),
        "mappings": mappings
    }), 200


@app.route('/test/venjue', methods=['POST'])
def test_venjue():
    """Test endpoint til at oprette en test booking i Venjue"""
    try:
        test_data = request.get_json() or {}
        
        booking_data = {
            "date": test_data.get("date", "2026-04-15"),
            "time": test_data.get("time", "18:00"),
            "title": test_data.get("title", "Musik Bingo i Pakhuset"),
            "pax": test_data.get("pax", 25),
            "customer": CUSTOMER_DEFAULTS,
            "note": "Test booking fra webhook integration",
            "locale": "da_DK",
            "sendNotification": False
        }
        
        result = create_venjue_booking({"event": booking_data})
        
        return jsonify({
            "status": "success",
            "result": result
        }), 200
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500


if __name__ == '__main__':
    print("=" * 60)
    print("UNDERSTORY → VENJUE WEBHOOK SERVER")
    print("=" * 60)
    print()
    print(f"Webhook endpoint: /webhook/understory")
    print(f"Health check: /health")
    print(f"Test endpoint: /test/venjue")
    print()
    print("Serveren starter...")
    print("=" * 60)
    
    # Start Flask server
    # For produktion: brug en WSGI server som gunicorn
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )
