#!/usr/bin/env python3
"""
Registrer Webhook hos Understory
=================================
Script til at registrere webhook endpoint hos Understory API
"""

import requests
from datetime import datetime, timedelta
import json

# KONFIGURATION
UNDERSTORY_CLIENT_ID = "8850e110974049358f0f2d183c18d216-f6e21905913543a8a0798a39555a9b67"
UNDERSTORY_CLIENT_SECRET = "-hlg-P~6SCAB3qeSGDg5zWd8E1"
UNDERSTORY_BASE_URL = "https://api.understory.io"

# Din webhook URL (skal være offentligt tilgængelig)
# For lokal udvikling: brug ngrok eller lignende
WEBHOOK_URL = "https://your-server.com/webhook/understory"


def get_access_token():
    """Hent Understory access token"""
    url = f"{UNDERSTORY_BASE_URL}/oauth2/token"
    
    data = {
        "grant_type": "client_credentials",
        "client_id": UNDERSTORY_CLIENT_ID,
        "client_secret": UNDERSTORY_CLIENT_SECRET,
        "scope": "webhook.write webhook.read"
    }
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    response = requests.post(url, data=data, headers=headers)
    response.raise_for_status()
    
    token_data = response.json()
    return token_data["access_token"]


def list_webhooks(access_token):
    """Vis alle registrerede webhooks"""
    url = f"{UNDERSTORY_BASE_URL}/v1/webhook-subscriptions"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "User-Agent": "Venjue-Integration/1.0"
    }
    
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    data = response.json()
    webhooks = data.get("webhookSubscriptions", [])
    
    print("\nEKSISTERENDE WEBHOOKS:")
    print("-" * 60)
    
    if not webhooks:
        print("Ingen webhooks registreret")
    else:
        for webhook in webhooks:
            print(f"ID: {webhook.get('id')}")
            print(f"URL: {webhook.get('url')}")
            print(f"Events: {', '.join(webhook.get('eventTypes', []))}")
            print(f"Status: {webhook.get('status')}")
            print("-" * 60)
    
    return webhooks


def create_webhook(access_token, webhook_url, event_types):
    """Opret ny webhook subscription"""
    url = f"{UNDERSTORY_BASE_URL}/v1/webhook-subscriptions"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "Venjue-Integration/1.0"
    }
    
    data = {
        "url": webhook_url,
        "eventTypes": event_types,
        "description": "Venjue integration - Event created webhook"
    }
    
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    
    return response.json()


def delete_webhook(access_token, subscription_id):
    """Slet webhook subscription"""
    url = f"{UNDERSTORY_BASE_URL}/v1/webhook-subscriptions/{subscription_id}"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "User-Agent": "Venjue-Integration/1.0"
    }
    
    response = requests.delete(url, headers=headers)
    response.raise_for_status()
    
    print(f"✓ Webhook {subscription_id} slettet")


def main():
    print("=" * 60)
    print("UNDERSTORY WEBHOOK REGISTRERING")
    print("=" * 60)
    print()
    
    # Hent access token
    print("Autentificerer med Understory...")
    try:
        access_token = get_access_token()
        print("✓ Autentificeret")
    except Exception as e:
        print(f"✗ Fejl ved autentificering: {e}")
        return
    
    # Vis eksisterende webhooks
    try:
        existing_webhooks = list_webhooks(access_token)
    except Exception as e:
        print(f"✗ Kunne ikke hente webhooks: {e}")
        return
    
    print()
    print("MULIGHEDER:")
    print("1. Opret ny webhook")
    print("2. Slet eksisterende webhook")
    print("3. Afslut")
    print()
    
    choice = input("Vælg (1-3): ").strip()
    
    if choice == "1":
        # Opret ny webhook
        print()
        webhook_url = input(f"Webhook URL [{WEBHOOK_URL}]: ").strip() or WEBHOOK_URL
        
        print()
        print("Tilgængelige event types:")
        print("- v1.event.created (når event oprettes)")
        print("- v1.event.updated (når event opdateres - REAL-TIME SYNC)")
        print("- v1.event.cancelled")
        print("- v1.event.completed")
        print("- v1.booking.created")
        print("- v1.booking.updated")
        print()
        
        event_types_input = input("Event types (kommasepareret) [v1.event.created,v1.event.updated]: ").strip()
        event_types = [e.strip() for e in event_types_input.split(",")] if event_types_input else ["v1.event.created", "v1.event.updated"]
        
        print()
        print(f"Opretter webhook...")
        print(f"  URL: {webhook_url}")
        print(f"  Events: {', '.join(event_types)}")
        
        try:
            result = create_webhook(access_token, webhook_url, event_types)
            print()
            print("✓ WEBHOOK OPRETTET!")
            print(f"  ID: {result.get('webhookSubscription', {}).get('id')}")
            print(f"  Status: {result.get('webhookSubscription', {}).get('status')}")
        except Exception as e:
            print(f"✗ Fejl: {e}")
            if hasattr(e, 'response') and e.response:
                print(f"Response: {e.response.text}")
    
    elif choice == "2":
        # Slet webhook
        if not existing_webhooks:
            print("Ingen webhooks at slette")
            return
        
        print()
        subscription_id = input("Webhook ID at slette: ").strip()
        
        confirm = input(f"Er du sikker på du vil slette webhook {subscription_id}? (ja/nej): ").strip().lower()
        
        if confirm == "ja":
            try:
                delete_webhook(access_token, subscription_id)
            except Exception as e:
                print(f"✗ Fejl: {e}")
    
    print()
    print("=" * 60)


if __name__ == "__main__":
    main()
