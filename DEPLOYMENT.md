# 🚀 Production Deployment Guide

## Deploy Understory → Venjue Webhook til Produktion

### Option 1: Linux VPS (DigitalOcean, Linode, Hetzner)

#### 1. Forbered server
```bash
# SSH til server
ssh root@your-server.com

# Opdater system
apt update && apt upgrade -y

# Installer Python og dependencies
apt install -y python3 python3-pip python3-venv nginx
```

#### 2. Opret deployment directory
```bash
# Opret directory
mkdir -p /opt/understory-venjue-webhook
cd /opt/understory-venjue-webhook

# Upload filer (fra din lokale maskine)
scp webhook_server.py requirements.txt .env root@your-server:/opt/understory-venjue-webhook/
```

#### 3. Setup Python environment
```bash
# Opret virtual environment
python3 -m venv venv
source venv/bin/activate

# Installer dependencies
pip install -r requirements.txt
pip install gunicorn
```

#### 4. Konfigurer environment
```bash
# Rediger .env fil
nano .env

# Tilføj credentials (se .env.example)
```

#### 5. Setup systemd service
```bash
# Kopiér service fil
cp understory-webhook.service /etc/systemd/system/

# Reload systemd
systemctl daemon-reload

# Enable og start service
systemctl enable understory-webhook
systemctl start understory-webhook

# Tjek status
systemctl status understory-webhook
```

#### 6. Setup Nginx reverse proxy
```bash
# Opret Nginx config
nano /etc/nginx/sites-available/webhook

# Tilføj:
```

```nginx
server {
    listen 80;
    server_name webhook.braunstein.dk;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# Enable site
ln -s /etc/nginx/sites-available/webhook /etc/nginx/sites-enabled/

# Test config
nginx -t

# Reload Nginx
systemctl reload nginx
```

#### 7. Setup SSL med Let's Encrypt
```bash
# Installer certbot
apt install -y certbot python3-certbot-nginx

# Få SSL certifikat
certbot --nginx -d webhook.braunstein.dk

# Auto-renewal er setup automatisk
```

#### 8. Registrer webhook hos Understory
```bash
# Fra din lokale maskine
python register_webhook.py

# Angiv URL: https://webhook.braunstein.dk/webhook/understory
```

---

### Option 2: Heroku

#### 1. Forbered
```bash
# Installer Heroku CLI
brew install heroku  # macOS

# Login
heroku login
```

#### 2. Opret Procfile
```bash
echo "web: gunicorn webhook_server:app" > Procfile
```

#### 3. Deploy
```bash
# Opret app
heroku create braunstein-webhook

# Sæt environment variables
heroku config:set UNDERSTORY_CLIENT_ID="8850e110974049358f0f2d183c18d216-f6e21905913543a8a0798a39555a9b67"
heroku config:set UNDERSTORY_CLIENT_SECRET="-hlg-P~6SCAB3qeSGDg5zWd8E1"
heroku config:set VENJUE_ACCESS_TOKEN="70f6b33cc35f786c8ad82cf94ef1fc86"

# Deploy
git init
git add .
git commit -m "Initial deployment"
git push heroku main

# Se logs
heroku logs --tail
```

#### 4. Registrer webhook
```bash
# Heroku URL: https://braunstein-webhook.herokuapp.com
python register_webhook.py

# Angiv: https://braunstein-webhook.herokuapp.com/webhook/understory
```

---

### Option 3: Docker

#### 1. Opret Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY webhook_server.py .

EXPOSE 5000

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "webhook_server:app"]
```

#### 2. Opret docker-compose.yml
```yaml
version: '3.8'

services:
  webhook:
    build: .
    ports:
      - "5000:5000"
    environment:
      - UNDERSTORY_CLIENT_ID=8850e110974049358f0f2d183c18d216-f6e21905913543a8a0798a39555a9b67
      - UNDERSTORY_CLIENT_SECRET=-hlg-P~6SCAB3qeSGDg5zWd8E1
      - VENJUE_ACCESS_TOKEN=70f6b33cc35f786c8ad82cf94ef1fc86
    restart: unless-stopped
```

#### 3. Deploy
```bash
# Build og start
docker-compose up -d

# Se logs
docker-compose logs -f
```

---

## 🔒 Sikkerhed Best Practices

### 1. Environment Variables
✅ **Aldrig** commit credentials til git
✅ Brug `.env` filer eller cloud secrets
✅ Brug separate credentials til test/produktion

### 2. HTTPS
✅ **Altid** brug HTTPS i produktion
✅ Let's Encrypt SSL certificates er gratis
✅ Understory kræver HTTPS for webhooks

### 3. Firewall
```bash
# UFW (Ubuntu)
ufw allow 22/tcp   # SSH
ufw allow 80/tcp   # HTTP
ufw allow 443/tcp  # HTTPS
ufw enable
```

### 4. Monitoring
```bash
# Tjek service status
systemctl status understory-webhook

# Se logs
journalctl -u understory-webhook -f

# Nginx logs
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

---

## 📊 Health Checks

### Uptime monitoring
Setup monitor hos:
- UptimeRobot (gratis)
- Pingdom
- StatusCake

Monitor URL: `https://webhook.braunstein.dk/health`

### Alerting
Setup alerts til:
- Service down
- High error rate
- Slow response times

---

## 🔄 Updates og Vedligeholdelse

### Pull nye ændringer
```bash
cd /opt/understory-venjue-webhook
git pull origin main
systemctl restart understory-webhook
```

### Backup
```bash
# Backup credentials
cp .env .env.backup

# Backup logs (valgfrit)
journalctl -u understory-webhook > webhook.log
```

---

## 🐛 Troubleshooting

### Service fejler at starte
```bash
# Tjek logs
journalctl -u understory-webhook -n 50

# Test manuelt
cd /opt/understory-venjue-webhook
source venv/bin/activate
python webhook_server.py
```

### Webhooks modtages ikke
```bash
# Tjek Nginx logs
tail -f /var/log/nginx/error.log

# Test endpoint direkte
curl https://webhook.braunstein.dk/health

# Tjek webhook registrering
python register_webhook.py
```

### High memory usage
```bash
# Reducer workers i systemd service
# Rediger: /etc/systemd/system/understory-webhook.service
# Ændr: gunicorn -w 2 ...  (fra -w 4)

systemctl daemon-reload
systemctl restart understory-webhook
```

---

## 📈 Skalering

### Lodret skalering (større server)
- Øg RAM/CPU på serveren
- Øg antal gunicorn workers

### Horisontal skalering (flere servere)
- Load balancer (Nginx, HAProxy)
- Flere webhook servers
- Shared Redis cache for tokens

---

## 🎯 Done!

Din webhook integration kører nu 24/7 i produktion! 🎉

Events fra Understory bliver automatisk til bookings i Venjue.
