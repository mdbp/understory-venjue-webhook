#!/usr/bin/env python3
"""
Test Webhook Integration
=========================
Simulerer en Understory webhook for at teste integrationen
"""

import requests
import json
from datetime import datetime, timedelta

# Webhook server URL (kører lokalt)
WEBHOOK_URL = "http://localhost:5000/webhook/understory"

# Mock webhook data der ligner Understory's format
def create_mock_event_webhook():
    """Opret mock webhook payload for "Musik Bingo i Pakhuset" event"""
    
    # Event dato (om 2 uger)
    event_date = datetime.now() + timedelta(days=14)
    event_datetime = event_date.replace(hour=18, minute=0, second=0, microsecond=0)
    
    # Mock webhook payload
    webhook_payload = {
        "id": "webhook_test_001",
        "type": "v1.event.created",
        "createdAt": datetime.now().isoformat() + "Z",
        "data": {
            "id": "evt_musikbingo_001",
            "experienceId": "exp_musikbingo",
            "title": "Musik Bingo i Pakhuset",
            "startTime": event_datetime.isoformat() + "Z",
            "endTime": (event_datetime + timedelta(hours=3)).isoformat() + "Z",
            "capacity": 50,
            "bookedSpots": 0,
            "status": "published"
        }
    }
    
    return webhook_payload


def create_mock_event_updated_webhook(event_id="evt_musikbingo_001", sold_spots=25):
    """Opret mock webhook payload for event opdatering"""
    
    # Event dato (om 2 uger)
    event_date = datetime.now() + timedelta(days=14)
    event_datetime = event_date.replace(hour=18, minute=0, second=0, microsecond=0)
    
    # Mock webhook payload for UPDATE
    webhook_payload = {
        "id": "webhook_update_001",
        "type": "v1.event.updated",
        "createdAt": datetime.now().isoformat() + "Z",
        "data": {
            "id": event_id,
            "experienceId": "exp_musikbingo",
            "title": "Musik Bingo i Pakhuset",
            "startTime": event_datetime.isoformat() + "Z",
            "endTime": (event_datetime + timedelta(hours=3)).isoformat() + "Z",
            "capacity": 50,
            "bookedSpots": sold_spots,  # VIGTIGT: Antal solgte pladser
            "status": "published" if sold_spots < 50 else "sold_out"
        }
    }
    
    return webhook_payload


def send_test_webhook():
    """Send test webhook til serveren"""
    
    print("=" * 60)
    print("TEST WEBHOOK - Musik Bingo i Pakhuset")
    print("=" * 60)
    print()
    print("⚠️  REAL-TIME SYNC AKTIVERET:")
    print("   ✅ Event oprettelse → Opret booking")
    print("   ✅ Event opdatering → Opdater antal solgte")
    print()
    
    # Opret mock payload
    payload = create_mock_event_webhook()
    
    print("Sender webhook payload (CREATE):")
    print(json.dumps(payload, indent=2))
    print()
    
    try:
        # Send POST request
        print(f"Sender til: {WEBHOOK_URL}")
        response = requests.post(
            WEBHOOK_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        print(f"Status: {response.status_code}")
        print()
        
        if response.status_code == 200:
            result = response.json()
            print("✓ WEBHOOK HÅNDTERET SUCCESFULDT!")
            print()
            print("Response:")
            print(json.dumps(result, indent=2))
        else:
            print(f"✗ Fejl: {response.status_code}")
            print(response.text)
        
    except requests.exceptions.ConnectionError:
        print("✗ Kan ikke forbinde til webhook server")
        print("   Er serveren startet? Kør: python webhook_server.py")
    except Exception as e:
        print(f"✗ Fejl: {e}")
    
    print()
    print("=" * 60)


def send_test_update_webhook():
    """Test opdatering af event med flere solgte pladser"""
    
    print("=" * 60)
    print("TEST EVENT UPDATE - Musik Bingo")
    print("=" * 60)
    print()
    
    # Simuler forskellige opdateringer
    scenarios = [
        {"sold": 10, "desc": "10 pladser solgt"},
        {"sold": 25, "desc": "25 pladser solgt (halvvejs)"},
        {"sold": 45, "desc": "45 pladser solgt (næsten udsolgt)"},
        {"sold": 50, "desc": "50 pladser solgt (UDSOLGT!)"}
    ]
    
    print("SCENARIER:")
    for i, s in enumerate(scenarios, 1):
        print(f"{i}. {s['desc']}")
    print()
    
    choice = input("Vælg scenario (1-4) eller ENTER for #2: ").strip() or "2"
    
    try:
        idx = int(choice) - 1
        scenario = scenarios[idx]
    except:
        scenario = scenarios[1]  # Default til scenario 2
    
    print()
    print(f"Sender opdatering: {scenario['desc']}")
    print()
    
    # Opret update payload
    payload = create_mock_event_updated_webhook(sold_spots=scenario['sold'])
    
    print("Webhook payload (UPDATE):")
    print(json.dumps(payload, indent=2))
    print()
    
    try:
        response = requests.post(
            WEBHOOK_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        print(f"Status: {response.status_code}")
        print()
        
        if response.status_code == 200:
            result = response.json()
            print("✓ OPDATERING HÅNDTERET!")
            print()
            print(f"Solgt: {result.get('sold_spots', 'N/A')}/{result.get('capacity', 'N/A')}")
            print(f"Ledige: {result.get('available', 'N/A')}")
            print(f"Status: {result.get('event_status', 'N/A')}")
            print()
            print("Full response:")
            print(json.dumps(result, indent=2))
        else:
            print(f"✗ Fejl: {response.status_code}")
            print(response.text)
        
    except requests.exceptions.ConnectionError:
        print("✗ Kan ikke forbinde til webhook server")
    except Exception as e:
        print(f"✗ Fejl: {e}")
    
    print()
    print("=" * 60)


def test_venjue_direct():
    """Test direkte oprettelse i Venjue"""
    
    print("=" * 60)
    print("TEST DIREKTE VENJUE OPRETTELSE")
    print("=" * 60)
    print()
    
    test_url = "http://localhost:5000/test/venjue"
    
    test_data = {
        "date": (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d"),
        "time": "18:00",
        "title": "Musik Bingo i Pakhuset",
        "pax": 50
    }
    
    print("Test data:")
    print(json.dumps(test_data, indent=2))
    print()
    
    try:
        response = requests.post(
            test_url,
            json=test_data,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        print(f"Status: {response.status_code}")
        print()
        
        if response.status_code == 200:
            result = response.json()
            print("✓ BOOKING OPRETTET!")
            print()
            print("Response:")
            print(json.dumps(result, indent=2))
            
            # Vis booking URL
            booking_url = result.get("result", {}).get("booking", {}).get("url")
            if booking_url:
                print()
                print(f"📋 Åbn booking i Venjue: {booking_url}")
        else:
            print(f"✗ Fejl: {response.status_code}")
            print(response.text)
        
    except requests.exceptions.ConnectionError:
        print("✗ Kan ikke forbinde til server")
        print("   Er serveren startet? Kør: python webhook_server.py")
    except Exception as e:
        print(f"✗ Fejl: {e}")
    
    print()
    print("=" * 60)


def health_check():
    """Tjek om webhook server kører"""
    
    print("Tjekker webhook server...")
    
    try:
        response = requests.get("http://localhost:5000/health", timeout=5)
        
        if response.status_code == 200:
            print("✓ Server kører")
            print(f"  {response.json()}")
            return True
        else:
            print(f"✗ Server svarede med status {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("✗ Server kører ikke")
        print("  Start serveren først: python webhook_server.py")
        return False
    except Exception as e:
        print(f"✗ Fejl: {e}")
        return False


def main():
    """Hovedmenu"""
    
    print("=" * 60)
    print("WEBHOOK INTEGRATION TEST (Real-time Sync)")
    print("=" * 60)
    print()
    
    # Health check
    if not health_check():
        print()
        print("Start webhook serveren først og prøv igen.")
        return
    
    print()
    print("VÆLG TEST:")
    print("1. Send test webhook (CREATE - nyt event)")
    print("2. Send test webhook (UPDATE - solgte pladser)")
    print("3. Test direkte Venjue oprettelse")
    print("4. Afslut")
    print()
    
    choice = input("Vælg (1-4): ").strip()
    
    print()
    
    if choice == "1":
        send_test_webhook()
    elif choice == "2":
        send_test_update_webhook()
    elif choice == "3":
        test_venjue_direct()
    else:
        print("Afslutter...")


if __name__ == "__main__":
    main()
