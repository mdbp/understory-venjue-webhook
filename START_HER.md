# 🎯 START HER

## Understory → Venjue Real-Time Sync

**Automatisk opdatering af antal solgte pladser, event ændringer og status**

---

## ⚡ Real-Time Sync - Hvad Betyder Det?

```
UNDERSTORY                          VENJUE
──────────                          ──────

Event oprettet:                     📝 Booking oprettet:
• Musik Bingo              →        • Pax: 0/50
• Kapacitet: 50

Ole booker 2 billetter     →        🔄 Pax: 2/50

Anna booker 4 billetter    →        🔄 Pax: 6/50

15 flere bookings          →        🔄 Pax: 21/50

Udsolgt!                   →        ✅ Pax: 50/50 (UDSOLGT)
```

**Hver gang nogen booker i Understory → Automatisk opdatering i Venjue!**

---

## ✅ Hvad Opdateres Live?

| Data | Real-Time? |
|------|-----------|
| **Antal solgte pladser** | ✅ Ja - live! |
| **Event titel** | ✅ Ja - hvis ændret |
| **Dato/tid** | ✅ Ja - hvis rykket |
| **Status (udsolgt/aflyst)** | ✅ Ja - automatisk |
| | |
| Individuelle deltagere | ❌ Nej (håndteres i Understory) |

---

## 🚀 Kom I Gang (3 Trin)

### Trin 1: Test Lokalt (5 minutter)

```bash
# Installer
pip install -r requirements.txt

# Start webhook server
python webhook_server.py

# Test (i ny terminal)
python test_webhook.py

# Vælg:
# 1 → Test event oprettelse (0 solgte)
# 2 → Test opdatering (vælg antal solgte: 10, 25, 45, 50)
```

**Resultat**: Du ser live hvordan antal solgte opdateres i real-time

---

### Trin 2: Læs Dokumentation

Start med én af disse:

📖 **`REALTIME_SYNC.md`** → Forstå real-time sync (START HER!)
📊 **`VISUAL_GUIDE.md`** → Se diagrammer og eksempler
⚡ **`QUICKSTART.md`** → Quick reference guide

---

### Trin 3: Deploy (Når du er klar)

📚 Se **`DEPLOYMENT.md`** for:
- Heroku deployment (nemmest)
- VPS setup (mere kontrol)  
- Docker deployment (containerized)

---

## 💡 Use Cases

### ✅ DET ER PERFEKT TIL:

**Live Event Monitoring:**
```
Dashboard i Venjue viser LIVE:
• Musik Bingo: 25/50 solgt (opdateres hver gang nogen booker)
• Whisky Tasting: 18/20 solgt (næsten udsolgt!)
• Beer Festival: 150/200 solgt
```

**Kapacitetsplanlægning:**
```
Se live hvor mange der har booket:
• <30 solgt → Book lille sal
• 30-45 solgt → Book mellem sal  
• 45+ solgt → Book store sal + ekstra personale
```

**Marketing Beslutninger:**
```
Real-time data driver marketing:
• <25% solgt → Boost Facebook ads
• 25-75% solgt → Normal marketing
• 75%+ solgt → Stop ads, spare penge
• 100% solgt → Opret venteliste
```

**Personale Scheduling:**
```
Baseret på live salg:
• 0-20 solgt → 1 bartender
• 21-40 solgt → 2 bartendere
• 41+ solgt → 3 bartendere
• Opdateres automatisk når flere booker
```

### ❌ DET ER IKKE TIL:

- Håndtere individuelle gæste-bookings
- Processer betalinger
- Administrere deltagerlister
- Check-in system

**Disse ting håndteres i Understory**

---

## 🎬 Real World Scenario

**Du planlægger "Musik Bingo" fredag d. 15. april:**

**Mandag 08:00 - Event Oprettet:**
```
I Understory:
✅ Opret event: Musik Bingo i Pakhuset
✅ Dato: Fredag 15/4 kl. 18:00
✅ Kapacitet: 50 personer

Automatisk i Venjue:
✅ Booking oprettet
✅ Pax: 0/50
✅ Du kan nu planlægge personale
```

**Mandag 10:30 - Første Bookings:**
```
I Understory:
• Ole booker 2 billetter
• Anna booker 4 billetter

Real-time i Venjue:
🔄 Pax opdateret: 6/50
📊 Status: 6/50 solgt
```

**Mandag 14:00 - Middag Rush:**
```
I Understory:
• 15 nye bookings

Real-time i Venjue:
🔄 Pax opdateret: 21/50
📊 Status: 21/50 solgt
→ Du beslutter: Book mellem sal (>20 solgt)
```

**Mandag 19:00 - Efter-arbejde:**
```
I Understory:
• 20 nye bookings

Real-time i Venjue:
🔄 Pax opdateret: 41/50
📊 Status: 41/50 solgt
→ Du beslutter: Book ekstra bartender (>40 solgt)
```

**Tirsdag 11:00 - Udsolgt!:**
```
I Understory:
• 9 sidste pladser solgt

Real-time i Venjue:
🔄 Pax opdateret: 50/50
✅ Status: UDSOLGT
→ Du ved præcis hvad du skal forberede
```

**Nu kan du i Venjue:**
- Se præcist hvor mange der kommer (50)
- Planlæg mad/drikkevarer for 50
- Book personale baseret på faktisk salg
- Se status uden at åbne Understory

---

## 🔑 Key Facts

1. **Real-Time Opdateringer**
   - Hver booking i Understory → Instant opdatering i Venjue
   - Se live hvor mange der har booket
   
2. **To Webhooks**
   - `event.created` → Opret booking (Pax: 0)
   - `event.updated` → Opdater antal solgte
   
3. **Live Status**
   - 📊 X/50 solgt (aktiv)
   - ✅ UDSOLGT (når alle pladser solgt)
   - 🚫 AFLYST (hvis annulleret)
   
4. **Smart Mapping**
   - System husker: Event ID → Booking ID
   - Samme event opdateres, ikke duplikeret

---

## 📊 Tech Stack

- **Python 3.7+** - Server sprog
- **Flask** - Webhook server
- **Understory API** - Event data source
- **Venjue API** - Booking destination

---

## 📞 Hjælp & Support

**Test virker ikke?**
→ Se `README_SYNC.md` troubleshooting sektion

**Deploy spørgsmål?**
→ Se `DEPLOYMENT.md` step-by-step guides

**API spørgsmål?**
- Understory: https://developer.understory.io/docs
- Venjue: https://venjue.com/docs/#article-api

---

## ✨ Credentials (Allerede Konfigureret)

Alt er sat op i `webhook_server.py`:

✅ Understory API credentials
✅ Venjue API token
✅ Standard kunde: Braunstein Event
✅ Email: events@braunstein.dk

**Du skal ikke konfigurere noget - bare kør!**

---

## 🎯 Next Steps

```
1. Kør lokal test → python webhook_server.py
2. Se visual guide → VISUAL_GUIDE.md
3. Når du er klar → Deploy med DEPLOYMENT.md
4. Registrer webhook → python register_webhook.py
5. Opret test event i Understory
6. Se det dukke op i Venjue! 🎉
```

---

**🍺 Udviklet til Braunstein Capital / Bryghuset Braunstein**

*Simple event sync - kun det du skal bruge*
