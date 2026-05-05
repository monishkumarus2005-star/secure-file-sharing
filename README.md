# 🛡️ Secure File Sharing System

A robust, enterprise-grade file sharing application built with security, integrity, and scalability in mind. This system combines a **FastAPI** backend, a modern **React (Vite)** frontend, and **Blockchain-based file anchoring** to ensure end-to-end security and tamper-proof verification.

## 🚀 Key Features

- **Secure Authentication**: JWT-based authentication with token blacklisting for secure logout.
- **End-to-End Encryption**: Files are encrypted at rest using AES-256 (Fernet) to ensure data privacy.
- **Blockchain Verification**: File hashes are anchored to the Ethereum blockchain (using Hardhat/Smart Contracts) for immutable proof of integrity.
- **Time-Limited Sharing**: Generate secure, signed links with custom expiration times.
- **Anomaly Detection**: Integrated ML-based anomaly detection to monitor and flag suspicious access patterns.
- **Real-time Processing**: Asynchronous file processing (virus scanning, hash generation) using **Celery** and **Redis**.
- **Containerized Architecture**: Fully dockerized environment with Nginx reverse proxy and Certbot for SSL.
- **Comprehensive Audit Logs**: Every file access, upload, and sharing event is tracked for security auditing.

## 🛠️ Tech Stack

- **Backend**: Python, FastAPI, SQLAlchemy, PostgreSQL.
- **Frontend**: React, TypeScript, Vite, Tailwind CSS (Vanilla CSS).
- **Security**: Fernet Encryption, JWT, Rate Limiting (Slowapi).
- **Infrastructure**: Docker, Docker Compose, Nginx, Redis, Celery.
- **Blockchain**: Solidity, Hardhat, Ethers.js.
- **Testing**: Pytest, Selenium (Manual Verification Flows).

## 📦 Project Structure

```text
├── app/                  # FastAPI Backend Application
│   ├── routes/           # API Endpoints (Files, Auth, Users, Admin)
│   ├── services/         # Business Logic (File Validation, Blockchain)
│   ├── models.py         # SQLAlchemy Database Models
│   └── main.py           # Application Entry Point
├── frontend/             # React (Vite) Frontend Application
├── contracts/            # Solidity Smart Contracts
├── alembic/              # Database Migrations
├── docker-compose.yml    # Infrastructure Orchestration
└── nginx/                # Reverse Proxy Configuration
```

## ⚙️ Getting Started

1. **Clone the repository**:
   ```bash
   git clone https://github.com/monishkumarus2005-star/secure-file-sharing.git
   cd secure-file-sharing
   ```

2. **Setup Environment**:
   - Copy `.env.example` to `.env` and fill in the required secrets.

3. **Launch with Docker**:
   ```bash
   docker-compose up --build
   ```

4. **Access the App**:
   - Frontend: `http://localhost:3000`
   - API Docs: `http://localhost:8000/docs`

## 🔒 Security Policy

This project implements strict file validation (type, size, and magic numbers) and utilizes a dedicated storage service to prevent unauthorized directory traversal and injection attacks.

---
Created by [monishkumarus2005-star](https://github.com/monishkumarus2005-star)
