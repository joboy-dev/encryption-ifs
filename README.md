# NIMC Identity Encryption & Blockchain Verification System

A proof-of-concept application that demonstrates secure identity data management using **ECC encryption**, **IPFS** decentralized storage, and **Hyperledger Fabric** blockchain verification. Built with **FastAPI** (Python) and server-rendered **Jinja2** templates.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [How It Works](#how-it-works)
- [Prerequisites](#prerequisites)
- [Project Setup](#project-setup)
  - [1. Clone the Repository](#1-clone-the-repository)
  - [2. Python Environment](#2-python-environment)
  - [3. Environment Variables](#3-environment-variables)
  - [4. Database Setup](#4-database-setup)
  - [5. IPFS Setup](#5-ipfs-setup)
  - [6. Hyperledger Fabric Setup (Linux)](#6-hyperledger-fabric-setup-linux)
  - [7. Running the Application](#7-running-the-application)
- [API Endpoints](#api-endpoints)
- [Project Structure](#project-structure)
- [Troubleshooting](#troubleshooting)

---

## Overview

This system provides a three-layer security model for identity data:

1. **Encryption** — Identity data is encrypted using AES-256-GCM with keys derived from an ECC (Elliptic Curve Cryptography) key pair via ECDH + HKDF.
2. **Decentralized Storage** — Encrypted data is uploaded to IPFS and referenced by its content identifier (CID).
3. **Blockchain Integrity** — A SHA-256 hash of the encrypted data, along with the CID and user ID, is recorded on a Hyperledger Fabric blockchain ledger. During verification, the hash is recalculated and compared against the blockchain record to detect any tampering.

---

## Architecture

```
┌──────────────┐       ┌──────────────┐       ┌──────────────────────┐
│   Frontend   │──────▶│   FastAPI     │──────▶│   SQLite Database    │
│  (Jinja2)    │       │   Backend     │       │   (User records)     │
└──────────────┘       └──────┬───────┘       └──────────────────────┘
                              │
                    ┌─────────┼─────────┐
                    ▼                   ▼
           ┌──────────────┐    ┌──────────────────┐
           │     IPFS      │    │  Hyperledger      │
           │  (Encrypted   │    │  Fabric Blockchain │
           │   data store) │    │  (Hash + CID log)  │
           └──────────────┘    └──────────────────┘
```

---

## How It Works

### Encryption Flow (`POST /encrypt`)

1. User submits identity data (email, full name, ID number, etc.).
2. Data is encrypted with AES-256-GCM (key derived from ECC via ECDH + HKDF).
3. A SHA-256 hash of the encrypted payload is computed.
4. Encrypted data is uploaded to IPFS → returns a CID.
5. The user ID, hash, and CID are recorded on the Hyperledger Fabric blockchain.
6. User record (email, CID, hash) is stored in the local SQLite database.
7. The CID is returned to the user for future verification.

### Verification Flow (`POST /verify`)

1. User submits the CID they received during encryption.
2. Encrypted data is retrieved from IPFS using the CID.
3. The SHA-256 hash is recalculated from the retrieved data.
4. The original hash is fetched from the blockchain using the user's ID.
5. If the recalculated hash matches the blockchain hash → **data integrity confirmed**.
6. The encrypted data is decrypted and returned.

---

## Prerequisites

| Requirement | Version | Purpose |
|---|---|---|
| **Python** | 3.10+ | Application runtime |
| **Go** | 1.20+ | Required by Hyperledger Fabric chaincode |
| **Docker & Docker Compose** | Latest | Runs the Fabric network containers |
| **IPFS (Kubo)** | 0.24.x or compatible | Decentralized file storage |
| **Git** | Latest | Cloning repos |
| **curl** | Latest | Downloading Fabric binaries |

---

## Project Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd encryption-verification-nimc
```

### 2. Python Environment

You can use `pyenv`, `venv`, or `conda`. Below uses `pyenv` as an example:

```bash
# Create a virtual environment
pyenv virtualenv 3.10 encrypt_env

# Activate the environment
pyenv shell encrypt_env

# Install dependencies
pip install -r requirements.txt
```

**Or with standard venv:**

```bash
python3 -m venv venv
source venv/bin/activate      # Linux/macOS
pip install -r requirements.txt
```

### 3. Environment Variables

Copy the sample environment file and fill in your values:

```bash
cp .env.sample .env
```

Edit `.env` with the following variables:

```dotenv
# Application
PYTHON_ENV=dev
PORT=7001
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=600
REFRESH_TOKEN_EXPIRE_MINUTES=30

# Database
DB_TYPE=sqlite
DB_NAME=enc.db
DB_URL=sqlite:///enc.db

# Mail (for notifications, if applicable)
MAIL_USERNAME=your-email@example.com
MAIL_PASSWORD=your-email-password
MAIL_FROM=your-email@example.com
MAIL_PORT=587
MAIL_SERVER=smtp.example.com
MAIL_FROM_NAME=NIMC Verification

# File storage
FILESTORAGE=filestorage

# Hyperledger Fabric
FABRIC_PATH=/path/to/fabric-samples        # Path to your fabric-samples directory (NOT test-network)
CHANNEL_NAME=mychannel                      # The channel name you created (e.g., mychannel or mychannel2)
```

> **Important:** `FABRIC_PATH` should point to the root `fabric-samples` directory, **not** `fabric-samples/test-network`. The application constructs the test-network path internally.

### 4. Database Setup

The application uses SQLite by default. The database file (`enc.db`) is created automatically when the app starts. To run Alembic migrations:

```bash
# Generate a migration (after model changes)
alembic revision --autogenerate -m "description of changes"

# Apply migrations
alembic upgrade head
```

### 5. IPFS Setup

The application requires a running IPFS daemon to store and retrieve encrypted data.

#### Preferred Method — Install from the bundled tar.gz (Recommended)

This project includes **go-ipfs v0.5.0** as a tar.gz file in the repository root. This is the recommended version because it is compatible with the Python `ipfshttpclient` package. Using a different IPFS version may cause API incompatibilities.

```bash
# From the project root directory
tar xzvf go-ipfs_v0.5.0_linux-arm64.tar.gz

# Install system-wide
cd go-ipfs
sudo bash install.sh

# Verify
ipfs --version
# Should output: ipfs version 0.5.0
```

> **Note:** The bundled file is for **linux-arm64**. If you're on a different architecture (e.g., linux-amd64), download the correct build from https://dist.ipfs.tech/go-ipfs/v0.5.0/ and follow the same steps.

#### Alternative — Install Kubo (newer IPFS)

> **Warning:** Newer Kubo versions may have API incompatibilities with `ipfshttpclient`. Use the bundled go-ipfs v0.5.0 above unless you have a specific reason not to.

**Linux:**

```bash
wget https://dist.ipfs.tech/kubo/v0.24.0/kubo_v0.24.0_linux-amd64.tar.gz
tar xzvf kubo_v0.24.0_linux-amd64.tar.gz
cd kubo
sudo bash install.sh
ipfs --version
```

**macOS (using Homebrew):**

```bash
brew install ipfs
```

**Manual download:**
- https://dist.ipfs.tech/kubo/v0.24.0/
- https://github.com/ipfs/ipfs-desktop/releases

#### Initialize and Run IPFS

```bash
# Initialize IPFS (first time only)
ipfs init

# Start the IPFS daemon (keep this running in a separate terminal)
ipfs daemon
```

> **Note:** The IPFS daemon must be running before you start the application. The app checks for IPFS connectivity on startup and will fail if it cannot connect.

### 6. Hyperledger Fabric Setup (Linux)

This section walks you through setting up a Hyperledger Fabric test-network from scratch on Linux. The test-network provides two peer organizations and an orderer, which the application uses to record and verify identity data on a blockchain ledger.

#### 6.1 Install Go

Hyperledger Fabric chaincode (smart contracts) is written in Go.

```bash
# Update packages
sudo apt update

# Install Go
sudo apt install golang-go -y

# Verify installation
go version
```

Add Go to your PATH by appending these lines to `~/.bashrc` (or `~/.zshrc`):

```bash
export GOPATH=$HOME/go
export PATH=$PATH:/usr/local/go/bin:$GOPATH/bin
```

Reload your shell:

```bash
source ~/.bashrc
```

#### 6.2 Install Docker & Docker Compose

Fabric runs its peers, orderers, and CAs inside Docker containers.

```bash
# Install Docker
sudo apt install docker.io docker-compose -y

# Add your user to the docker group (avoids needing sudo for docker commands)
sudo usermod -aG docker $USER

# Log out and log back in for group changes to take effect, then verify:
docker --version
docker-compose --version
```

#### 6.3 Install Fabric Samples, Binaries, and Docker Images

```bash
# Create a directory for Fabric
mkdir -p ~/fabric-samples && cd ~

# Download Fabric samples, binaries, and Docker images
curl -sSLO https://raw.githubusercontent.com/hyperledger/fabric/main/scripts/install-fabric.sh
chmod +x install-fabric.sh
./install-fabric.sh

# This creates ~/fabric-samples/ with:
#   - bin/          (peer, orderer, configtxgen, etc.)
#   - config/       (core.yaml, orderer.yaml, etc.)
#   - test-network/ (scripts to bring up a test network)
```

> **Reference:** https://hyperledger-fabric.readthedocs.io/en/release-2.5/install.html

#### 6.4 Update Your Hosts File

The Fabric network's Docker containers use internal hostnames. You need to map them to `127.0.0.1` on your host machine so the `peer` CLI can reach them:

```bash
sudo nano /etc/hosts
```

Add these lines at the bottom:

```
127.0.0.1   orderer.example.com
127.0.0.1   peer0.org1.example.com
127.0.0.1   peer0.org2.example.com
```

Save and exit (`Ctrl+O`, `Enter`, `Ctrl+X`).

**Verify it works:**

```bash
ping -c 2 orderer.example.com
# Should show replies from 127.0.0.1
```

> **Why is this needed?** The `peer` CLI resolves hostnames like `orderer.example.com` from the channel configuration. Without host entries, your machine tries to look them up on the public internet and fails.

#### 6.5 Bring Up the Test Network

```bash
cd ~/fabric-samples/test-network

# Bring up the network with a channel and Certificate Authorities
./network.sh up createChannel -c mychannel -ca
```

This command:
- Starts Docker containers for `orderer.example.com`, `peer0.org1.example.com`, and `peer0.org2.example.com`.
- Creates a channel named `mychannel` (use `-c <name>` to customize).
- Generates cryptographic material (MSP certificates) for both organizations.

**Verify the containers are running:**

```bash
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

You should see:

| Container | Ports |
|---|---|
| `orderer.example.com` | 7050 |
| `peer0.org1.example.com` | 7051 |
| `peer0.org2.example.com` | 9051 |

#### 6.6 Deploy the Chaincode (Smart Contract)

The application uses the `asset-transfer-basic` chaincode that comes with Fabric samples:

```bash
cd ~/fabric-samples/test-network

# Deploy the Go chaincode to the channel
./network.sh deployCC -ccn basic -ccp ../asset-transfer-basic/chaincode-go -ccl go -c mychannel
```

> **Note:** Replace `mychannel` with your channel name if you used a different one. Make sure the channel name matches the `CHANNEL_NAME` variable in your `.env` file.

**Verify the chaincode is deployed:**

```bash
export FABRIC_CFG_PATH=~/fabric-samples/config/
export CORE_PEER_TLS_ENABLED=true
export CORE_PEER_LOCALMSPID="Org1MSP"
export CORE_PEER_MSPCONFIGPATH=~/fabric-samples/test-network/organizations/peerOrganizations/org1.example.com/users/Admin@org1.example.com/msp
export CORE_PEER_TLS_ROOTCERT_FILE=~/fabric-samples/test-network/organizations/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/tls/ca.crt
export CORE_PEER_ADDRESS=localhost:7051

# Query all assets (should return an empty array or pre-seeded assets)
~/fabric-samples/bin/peer chaincode query \
  -C mychannel -n basic \
  -c '{"Args":["GetAllAssets"]}'
```

#### 6.7 Update Your `.env` File

Set `FABRIC_PATH` to point to your `fabric-samples` directory:

```dotenv
FABRIC_PATH=/home/your-username/fabric-samples
CHANNEL_NAME=mychannel
```

#### 6.8 Managing the Fabric Network

**Tear down and restart (clean slate):**

```bash
cd ~/fabric-samples/test-network

# Bring down the network completely
./network.sh down

# Remove all Docker artifacts
docker rm -f $(docker ps -aq) 2>/dev/null
docker volume prune -f
docker network prune -f

# Remove generated crypto material
sudo rm -rf organizations/peerOrganizations
sudo rm -rf organizations/ordererOrganizations
sudo rm -rf channel-artifacts

# Bring the network back up
./network.sh up createChannel -c mychannel -ca

# Redeploy chaincode (required after a full teardown)
./network.sh deployCC -ccn basic -ccp ../asset-transfer-basic/chaincode-go -ccl go -c mychannel
```

> **Important:** After tearing down the network, all ledger data is lost. You must redeploy the chaincode and any previously recorded assets will no longer exist.

### 7. Running the Application

Make sure the following services are running before starting the app:

1. **IPFS daemon** — `ipfs daemon` (in a separate terminal)
2. **Fabric network** — Docker containers for orderer and peers
3. **Python environment** — activated with all dependencies installed

```bash
# Start the FastAPI application
python main.py
```

The application starts on `http://localhost:7001` (or the next available port if 7001 is in use).

**Using tmux (recommended for managing multiple services):**

```bash
# Start a tmux session
tmux new -s nimc

# Pane 1: IPFS daemon
ipfs daemon

# Split pane (Ctrl+B, then %): Application
python main.py
```

| tmux Action | Shortcut |
|---|---|
| Split vertically | `Ctrl+B` → `%` |
| Split horizontally | `Ctrl+B` → `"` |
| Switch panes | `Ctrl+B` → Arrow keys |
| Close pane | `Ctrl+B` → `X` |
| Detach session | `Ctrl+B` → `D` |

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Landing page |
| `GET` | `/app` | Main application interface |
| `POST` | `/encrypt` | Encrypt identity data, store on IPFS and blockchain |
| `POST` | `/verify` | Verify data integrity using CID |
| `POST` | `/get-cid` | Retrieve stored CID by email |
| `GET` | `/logs` | Stream application logs |

### POST /encrypt

**Form fields:**
- `email` (required) — User's email address
- `full_name` — Full name
- `id_number` — National ID number

**Response:**
```json
{
  "success": true,
  "message": "Encryption complete",
  "cid": "QmeM2NiKLr9PZYL13XGDWgUb3yDPgeAovDFTaPtR6fSyFw"
}
```

### POST /verify

**Form fields:**
- `cid` (required) — The CID returned during encryption

**Response:**
```json
{
  "success": true,
  "message": "Verification complete",
  "decrypted_data": {
    "email": "user@example.com",
    "full_name": "John Doe",
    "id_number": "12345678901"
  }
}
```

### POST /get-cid

**Form fields:**
- `email` (required) — Email used during encryption

**Response:**
```json
{
  "success": true,
  "message": "Fetch complete",
  "cid": "QmeM2NiKLr9PZYL13XGDWgUb3yDPgeAovDFTaPtR6fSyFw"
}
```

---

## Project Structure

```
encryption-verification-nimc/
├── main.py                          # FastAPI application entry point
├── check_ipfs.py                    # IPFS connectivity checker
├── requirements.txt                 # Python dependencies
├── alembic.ini                      # Alembic migration config
├── .env.sample                      # Environment variable template
├── ecc_private.pem                  # Auto-generated ECC private key (gitignored)
│
├── api/
│   ├── core/
│   │   ├── base/
│   │   │   └── base_model.py        # Base SQLAlchemy model (UUID IDs, timestamps, CRUD)
│   │   └── dependencies/
│   │       ├── context.py           # Jinja2 template context decorator
│   │       ├── flash_messages.py    # Flash message system
│   │       └── form_builder.py      # Form utilities
│   ├── db/
│   │   └── database.py             # SQLite database engine and session management
│   ├── utils/
│   │   ├── settings.py             # Pydantic settings (reads .env)
│   │   ├── loggers.py              # Logging configuration
│   │   ├── responses.py            # Response helpers
│   │   └── ...                     # Other utilities
│   └── v1/
│       ├── models/
│       │   └── user.py             # User model (email, CID, hash)
│       ├── routes/
│       │   ├── index.py            # Main routes (/encrypt, /verify, /get-cid)
│       │   └── errors.py           # Error page routes (404, 500)
│       └── services/
│           └── nimc.py             # Core service: ECC encryption, IPFS, Fabric blockchain
│
├── frontend/
│   ├── app/
│   │   ├── components/             # Reusable Jinja2 components (navbar, footer, etc.)
│   │   └── pages/                  # Page templates (index, app, register, verify)
│   └── static/
│       └── images/                 # Static assets
│
├── alembic/                        # Database migration scripts
├── scripts/
│   └── create_api_module.sh        # Scaffolding script for new API modules
├── logs/                           # Application log files
├── tmp/media/                      # Temporary media storage
└── filestorage/                    # Uploaded file storage
```

---

## Troubleshooting

### IPFS daemon not running

```
Exception: IPFS is not running
```

**Fix:** Start the IPFS daemon in a separate terminal:

```bash
ipfs daemon
```

### Blockchain "context deadline exceeded"

```
orderer client failed to connect to orderer.example.com:7050: context deadline exceeded
```

**Causes and fixes:**

1. **Fabric network is not running.** Start it:
   ```bash
   cd ~/fabric-samples/test-network
   ./network.sh up createChannel -c mychannel -ca
   ./network.sh deployCC -ccn basic -ccp ../asset-transfer-basic/chaincode-go -ccl go -c mychannel
   ```

2. **Hosts file not updated.** Add the entries described in [section 6.4](#64-update-your-hosts-file).

3. **Ports not accessible.** Verify:
   ```bash
   nc -zv localhost 7050    # Orderer
   nc -zv localhost 7051    # Peer0 Org1
   nc -zv localhost 9051    # Peer0 Org2
   ```

### Blockchain query returns "asset not found"

This typically means the `record_on_blockchain` invoke transaction was not properly committed. Ensure the invoke command includes **both peer endorsers** (Org1 on port 7051 and Org2 on port 9051) to satisfy the default endorsement policy. The `--waitForEvent` flag should also be used to confirm the transaction is committed before returning success.

### Verify TLS certificates exist

```bash
# Orderer TLS CA
ls -la ~/fabric-samples/test-network/organizations/ordererOrganizations/example.com/orderers/orderer.example.com/msp/tlscacerts/tlsca.example.com-cert.pem

# Peer0 Org1 TLS cert
ls -la ~/fabric-samples/test-network/organizations/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/tls/ca.crt

# Admin MSP
ls -la ~/fabric-samples/test-network/organizations/peerOrganizations/org1.example.com/users/Admin@org1.example.com/msp/
```

If any are missing, tear down and bring the network back up (see [section 6.8](#68-managing-the-fabric-network)).

### Quick blockchain smoke test

Run a manual query from the command line to determine if the problem is in the code or the infrastructure:

```bash
export FABRIC_CFG_PATH=~/fabric-samples/config/
export CORE_PEER_TLS_ENABLED=true
export CORE_PEER_LOCALMSPID="Org1MSP"
export CORE_PEER_MSPCONFIGPATH=~/fabric-samples/test-network/organizations/peerOrganizations/org1.example.com/users/Admin@org1.example.com/msp
export CORE_PEER_TLS_ROOTCERT_FILE=~/fabric-samples/test-network/organizations/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/tls/ca.crt
export CORE_PEER_ADDRESS=localhost:7051

~/fabric-samples/bin/peer chaincode query \
  -C mychannel -n basic \
  -c '{"Args":["GetAllAssets"]}'
```

- If this **succeeds** → the network is fine; the issue is in your application code or `.env` configuration.
- If this **fails** → the Fabric network needs to be restarted or redeployed.

---

## License

This project is a proof-of-concept for academic/demonstration purposes.