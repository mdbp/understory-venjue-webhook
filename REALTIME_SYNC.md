# 🔄 Real-Time Sync: Understory → Venjue

**Live opdatering af antal solgte pladser, event ændringer og status**

---

## ⚡ Hvad er Real-Time Sync?

Når noget ændrer sig i Understory, opdateres det **automatisk** i Venjue:

```
UNDERSTORY                          VENJUE
──────────────────────────────────────────────

Event oprettet:                     📝 Booking oprettet:
• Musik Bingo                       • Musik Bingo
• Kapacitet: 50            →        • Pax: 0 (ingen solgt endnu)

[10 minutter senere]
Ole booker 2 billetter     →        🔄 Pax opdateret: 2

[30 minutter senere]
Anna booker 4 billetter    →        🔄 Pax opdateret: 6

[1 time senere]
15 flere bookings          →        🔄 Pax opdateret: 21

[2 timer senere]
Udsolgt! (50/50)          →        ✅ Pax opdateret: 50
                                    Status: UDSOLGT
```

---

## 📊 Hvad Opdateres i Real-Time?

| Data | Opdateres? | Hvordan? |
|------|-----------|----------|
| **Antal solgte pladser** | ✅ Ja | 0→10→20→50 live |
| **Event titel** | ✅ Ja | Hvis ændret i Understory |
| **Dato/tid** | ✅ Ja | Hvis event rykkes |
| **Status** | ✅ Ja | Aktiv/Udsolgt/Aflyst |
| | | |
| Individuelle deltagere | ❌ Nej | Håndteres i Understory |
| Betalinger | ❌ Nej | Håndteres i Understory |

---

## 🎯 Live Eksempel

**Scenario: Musik Bingo i Pakhuset**

### Trin 1: Event Oprettes (Mandag 08:00)
```
UNDERSTORY                          VENJUE
• Event: Musik Bingo       →        • Booking: Musik Bingo
• Fredag 18:00                      • Fredag 18:00
• Kapacitet: 50                     • Pax: 0/50
• Status: Åben                      • Status: 📊 0/50 solgt
```

### Trin 2: Første Bookings (Mandag 10:30)
```
Ole booker 2 billetter
Anna booker 4 billetter    →        🔄 Pax: 6/50
Maria booker 3 billetter            Status: 📊 6/50 solgt
```

### Trin 3: Middag Rush (Mandag 12:00-14:00)
```
15 nye bookings            →        🔄 Pax: 21/50
                                    Status: 📊 21/50 solgt
```

### Trin 4: Efter-arbejde (Mandag 17:00)
```
20 nye bookings            →        🔄 Pax: 41/50
                                    Status: 📊 41/50 solgt
```

### Trin 5: Udsolgt! (Mandag 19:30)
```
9 sidste pladser solgt     →        🔄 Pax: 50/50
                                    Status: ✅ UDSOLGT
```

---

## 🔧 Teknisk Implementation

### Webhooks Understøttet

```javascript
// 1. Event Created
{
  "type": "v1.event.created",
  "data": {
    "id": "evt_001",
    "title": "Musik Bingo",
    "capacity": 50,
    "bookedSpots": 0  // ← Starter på 0
  }
}
→ Opret booking i Venjue (Pax: 0)

// 2. Event Updated (hver gang nogen booker)
{
  "type": "v1.event.updated",
  "data": {
    "id": "evt_001",
    "title": "Musik Bingo",
    "capacity": 50,
    "bookedSpots": 25  // ← Opdateret til 25
  }
}
→ Opdater booking i Venjue (Pax: 25)
```

### Mapping Database

Systemet husker hvilke events der hører til hvilke bookings:

```
Event ID (Understory) → Booking ID (Venjue)
───────────────────────────────────────────
evt_musikbingo_001   → 12345
evt_whisky_002       → 12346
evt_beer_003         → 12347
```

Gemt i: `event_booking_mapping.db` (shelve database)

---

## 🚀 Kom I Gang

### 1. Start Webhook Server
```bash
python webhook_server.py
```

### 2. Registrer Begge Webhooks
```bash
python register_webhook.py

# Når spurgt om event types:
v1.event.created,v1.event.updated
```

### 3. Test Lokalt
```bash
python test_webhook.py

# Vælg option 1: Test CREATE
# Vælg option 2: Test UPDATE med forskellige antal solgte
```

---

## 📊 Se Mappings

Webhook serveren har et endpoint til at se alle mappings:

```bash
curl http://localhost:5000/mappings

# Response:
{
  "total": 3,
  "mappings": {
    "evt_001": {
      "booking_id": "12345",
      "created_at": "2026-03-10T10:30:00"
    },
    "evt_002": {
      "booking_id": "12346",
      "created_at": "2026-03-10T11:15:00"
    }
  }
}
```

---

## ⚠️ Venjue API Limitation

**VIGTIGT**: Venjue API har pt. ikke et UPDATE endpoint for bookings.

**Current Workaround:**
- System logger opdateringer
- Opdateret info vises i webhook response
- Note i booking viser status

**Future Solution:**
Når Venjue tilføjer `PUT /booking/{id}` endpoint, vil systemet automatisk opdatere:
- Pax (antal solgte)
- Titel
- Dato/tid
- Note med status

---

## 🎮 Test Scenarios

### Scenario 1: Gradvis Salg
```bash
python test_webhook.py
# Vælg option 2

# Vælg:
1. 10 pladser solgt
2. 25 pladser solgt (halvvejs)
3. 45 pladser solgt (næsten udsolgt)
4. 50 pladser solgt (UDSOLGT!)
```

### Scenario 2: Event Ændring
```
Titel ændret:
"Musik Bingo" → "SIDSTE CHANCE: Musik Bingo"

Dato ændret:
Fredag 18:00 → Lørdag 19:00

→ Webhook sendes automatisk
→ Venjue booking opdateres
```

---

## 📝 Venjue Booking Note Format

```
Event synkroniseret fra Understory (Real-time)
═══════════════════════════════════════════════
Event ID: evt_001
Experience ID: exp_musikbingo

STATUS: 📊 25/50 solgt
Solgte pladser: 25
Kapacitet: 50
Ledige pladser: 25

Senest opdateret: 2026-03-10 14:30:15
```

Status ændrer sig:
- `📊 10/50 solgt` - Aktiv salg
- `✅ UDSOLGT` - Alle pladser solgt
- `🚫 AFLYST` - Event annulleret

---

## 🔄 Workflow Diagram

```
┌─────────────────┐
│   UNDERSTORY    │
│                 │
│ Event Created   │
└────────┬────────┘
         │
         ↓ v1.event.created
┌─────────────────┐
│ Webhook Server  │
│                 │
│ • Create        │
│ • Map ID        │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│     VENJUE      │
│ Booking: Pax 0  │
└─────────────────┘

         ⋮
    [Tid går...]
         ⋮

┌─────────────────┐
│   UNDERSTORY    │
│                 │
│ Booking Added   │
│ (bookedSpots++) │
└────────┬────────┘
         │
         ↓ v1.event.updated
┌─────────────────┐
│ Webhook Server  │
│                 │
│ • Find mapping  │
│ • Update        │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│     VENJUE      │
│ Booking: Pax 25 │
└─────────────────┘
```

---

## 🎯 Use Cases

### ✅ PERFEKT TIL:

**Live Event Monitoring**
```
Dashboard i Venjue viser:
• Musik Bingo: 25/50 solgt
• Whisky Tasting: 18/20 solgt
• Beer Festival: 150/200 solgt
```

**Kapacitetsplanlægning**
```
Hvis <30 solgt → Book lille sal
Hvis 30-45 solgt → Book mellem sal
Hvis 45+ solgt → Book store sal
```

**Personale Scheduling**
```
0-20 solgt → 1 bartender
21-40 solgt → 2 bartendere
41+ solgt → 3 bartendere
```

**Marketing Decisions**
```
<25% solgt → Push marketing
25-75% solgt → Normal marketing
75%+ solgt → Stop marketing
100% solgt → Venteliste
```

---

## 🔐 Sikkerhed

**Mapping Database:**
- Lokal shelve database
- Ingen persondata
- Kun event ID ↔ booking ID
- Kan nulstilles uden tab af bookings

**Webhook Validering:**
- Tjek event type
- Verificer event ID eksisterer
- Håndter fejl gracefully

---

## 🐛 Troubleshooting

### Opdatering virker ikke
```bash
# Tjek mappings
curl http://localhost:5000/mappings

# Tjek logs
# Se webhook server output for fejl
```

### Event ID ikke fundet
```
→ Event blev oprettet før webhook var aktiv
→ System opretter ny booking automatisk
```

### Duplikerede bookings
```
→ Samme event ikke oprettet 2 gange
→ Mapping database forhindrer dette
```

---

## 📈 Fremtidige Features

Når Venjue API understøtter booking updates:

✅ **Direkte pax opdatering** (i stedet for note)
✅ **Titel/dato ændringer** direkte i booking
✅ **Custom status felter**
✅ **Historik over ændringer**

---

## 🎯 Quick Reference

**Start server:**
```bash
python webhook_server.py
```

**Registrer webhooks:**
```bash
python register_webhook.py
# Events: v1.event.created,v1.event.updated
```

**Test CREATE:**
```bash
python test_webhook.py → Option 1
```

**Test UPDATE:**
```bash
python test_webhook.py → Option 2
```

**Se mappings:**
```bash
curl http://localhost:5000/mappings
```

---

**🍺 Udviklet til Braunstein Capital / Bryghuset Braunstein**

*Real-time sync - se salget live!*
