# 🚀 QUICK START GUIDE

## Understory → Venjue Event Synkronisering

⚠️ **VIGTIGT**: Kun selve eventet synkroniseres (titel, dato, tid, samlet kapacitet). Individuelle deltager-bookings synkroniseres IKKE.

### ⚡ Kom i gang på 5 minutter

#### 1. Installer dependencies
```bash
pip install -r requirements.txt
```

#### 2. Start webhook serveren
```bash
python webhook_server.py
```

Serveren starter på `http://localhost:5000`

#### 3. Test lokalt (i ny terminal)
```bash
python test_webhook.py
```

Vælg option 1 for at simulere en "Musik Bingo i Pakhuset" webhook.

---

## 📋 Hvad Synkroniseres?

**✅ DET SYNKRONISERES:**
- Event titel (fx "Musik Bingo i Pakhuset")
- Event dato og tid
- Samlet kapacitet (antal personer)

**❌ DET SYNKRONISERES IKKE:**
- Individuelle deltager-bookings
- Deltagernavne
- Payment info

**Resultat i Venjue:**
- Én booking per event
- Kunde: "Braunstein Event"
- Pax: Samlet kapacitet fra eventet

---

## 📝 Credentials (allerede konfigureret)

✅ **Understory:**
- Client ID: `8850e110974049358f0f2d183c18d216-f6e21905913543a8a0798a39555a9b67`
- Secret: `-hlg-P~6SCAB3qeSGDg5zWd8E1`

✅ **Venjue:**
- Access Token: `70f6b33cc35f786c8ad82cf94ef1fc86`

✅ **Standard kunde:**
- Navn: Braunstein Event
- Email: events@braunstein.dk
- Telefon: 56 79 12 12

---

## 🌐 Gør serveren offentlig

### Med ngrok (anbefalet til test):
```bash
# Installer ngrok
brew install ngrok  # macOS
# eller download fra https://ngrok.com

# Start tunnel
ngrok http 5000

# Kopiér URL (fx https://abc123.ngrok.io)
```

### Registrer webhook hos Understory:
```bash
python register_webhook.py
```

Angiv din offentlige URL når du bliver spurgt:
```
https://abc123.ngrok.io/webhook/understory
```

---

## ✅ Test med rigtig Understory event

1. ✅ Serveren kører og er offentlig tilgængelig
2. ✅ Webhook er registreret hos Understory
3. 🎯 Opret et nyt event i Understory
4. ⚡ Webhook modtages automatisk
5. ✅ Booking oprettes i Venjue!

---

## 📊 Se hvad der sker

Serveren logger alt:

```
============================================================
WEBHOOK MODTAGET: v1.event.created
Event ID: evt_musikbingo_001
Timestamp: 2026-03-10T12:00:00
============================================================
Henter event detaljer fra Understory...
✓ Event hentet: Musik Bingo i Pakhuset
Opretter booking i Venjue...
✓ Booking oprettet i Venjue!
  ID: 12345
  URL: https://app.venjue.com/booking.php?eventId=12345
============================================================
```

---

## 🆘 Problemer?

**Serveren starter ikke:**
```bash
pip install -r requirements.txt --upgrade
```

**Webhook modtages ikke:**
- Tjek at ngrok tunnel kører
- Verificer webhook er registreret: `python register_webhook.py`
- Se server logs

**Venjue booking fejler:**
- Tjek access token er gyldigt
- Se detaljerede fejl i server logs

---

## 🎯 Produktionsklar deployment

Se `README_WEBHOOK.md` for:
- Deployment til Heroku/DigitalOcean
- HTTPS setup
- Environment variables
- Sikkerhed best practices
- Monitoring

---

## 📞 Support

**Understory API:** https://developer.understory.io/docs
**Venjue API:** https://venjue.com/docs/#article-api

---

**Integration udviklet til Braunstein Capital / Bryghuset Braunstein** 🍺
