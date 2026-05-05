# Deployment Runbook (Ubuntu 22.04 VPS)

This runbook outlines the required steps to deploy the Secure Cloud File Sharing FastAPI system on a fresh Ubuntu 22.04 LTS VPS instance. 

> **Important**: This guide assumes you have root or `sudo` access to the Ubuntu 22.04 server and a registered domain name pointed to the server's public IP Address.

## 1. Initial Server Provisioning & Updates

Run the following commands as a user with `sudo` privileges:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl wget git build-essential ufw cron
```

## 2. Configure Firewall (UFW)

Ensure basic security before deploying services:

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow http
sudo ufw allow https
sudo ufw --force enable
```

## 3. Install Docker and Docker Compose

Install the latest Docker engine and standard Docker Compose plugin:

```bash
# Add Docker's official GPG key:
sudo apt-get update
sudo apt-get install ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

# Add the Docker repository to Apt sources:
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update

# Install Docker engine
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin -y

# Verify Installation
docker compose version
```

## 4. Clone Repository & Setup Environment

```bash
git clone <your-repository-url> /opt/secure-file-sharing
cd /opt/secure-file-sharing

# Generate secure cryptographic keys
openssl rand -hex 32 > jwt_secret_key.txt

# Create your .env file
cp .env.example .env

# Edit the .env file and set the JWT_SECRET_KEY, DOMAIN_NAME, Database Password, etc.
nano .env
```

## 5. Provision SSL Certificates (Let's Encrypt)

Before starting the web application container, provision SSL certificates to mount into your Nginx reverse proxy.

```bash
sudo apt install -y certbot

# Ensure port 80 is not currently active before running standalone mode
sudo certbot certonly --standalone -d your-domain.com -d www.your-domain.com --agree-tos -m your-email@example.com

# Copy certs to the Nginx certs folder specified in docker-compose.yml
sudo mkdir -p ./nginx/certs
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem ./nginx/certs/
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem ./nginx/certs/
sudo chown -R $USER:$USER ./nginx/certs
```

## 6. Build and Deploy The Application

Start all services securely using Docker Compose.

```bash
docker compose build --no-cache
docker compose up -d
```

Verify that all containers are active:
```bash
docker compose ps
```

## 7. Run Automatic Smoke Tests

Once everything is booted, verify stability utilizing the included smoke testing script:

```bash
chmod +x smoke_test.sh
TARGET_URL=https://your-domain.com ./smoke_test.sh
```

## 8. Final Configuration (PostgreSQL Backups)

Add a cron job to automatically trigger database backups if Celery scheduling ever fails:

```bash
# Optional redundant host-level cron for hitting the /admin/backup trigger via cURL
# Requires generating an admin token first, or using the Celery Beat system directly
```

The system includes Celery Beat which has been programmed to run backups automatically at 2:00 AM UTC. 

## Rollback Procedures

If an update breaks production, gracefully roll back to the previously built image:

```bash
docker compose down
git checkout <previous-stable-commit-hash>
docker compose up -d --build
```
