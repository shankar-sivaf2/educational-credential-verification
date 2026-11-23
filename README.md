# An Efficient Blockchain-Based Approach to Educational Credential Verification

Final-year B.Tech CSE project. Institutions issue certificates, students keep them, and
employers verify them against a blockchain record without contacting the institution.

## How it works in one minute
1. The institution enters a certificate. The backend builds a canonical JSON form, adds a
   random 256-bit salt, and computes a SHA-256 commitment.
2. Only the commitment and the issuer's address go to the `CertificateRegistry` smart contract.
   Names, grades and other details never go on-chain.
3. The student receives a certificate file (the fields plus the salt) and a QR code.
4. An employer uploads the file. The backend recomputes the commitment and compares it with
   the blockchain record, then checks that the issuer is authorised and the certificate is
   not revoked.

A "valid" result means the data is unchanged since an authorised institution registered it
and it has not been revoked. It does not prove the qualification was earned.

## Tech stack
Python 3 + FastAPI, SQLite + SQLAlchemy, Solidity 0.8.24 + Hardhat + OpenZeppelin v5,
Web3.py, React 18 + Vite, Pytest.

## Folder layout
```
backend/      FastAPI app, crypto, blockchain client, tests
blockchain/   Solidity contract, Hardhat scripts and tests
frontend/     React web app
scripts/      PowerShell helpers, demo data, benchmark
storage/      SQLite database and demo files (git-ignored)
docs/         Design, API, security, test and benchmark documents
```

## Quick start (Windows, PowerShell)

### Prerequisites
- Python 3.11 or later
- Node.js 18 or later (Node.js 20 LTS recommended)
- Git

### Step 1: Open the project folder

Open PowerShell and navigate to the project root:

```powershell
cd "C:\Users\DELL\OneDrive\Desktop\educational-credential-verification"
```

If your project is stored elsewhere, use its actual folder path.

### Step 2: Install dependencies and configure the project

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\setup.ps1
```

Run this once during initial setup.

The setup script:
- Creates the project-root `.venv313` Python virtual environment if it does not exist.
- Installs backend dependencies.
- Installs blockchain dependencies and compiles smart contracts.
- Installs frontend dependencies.
- Creates `backend\.env` from `backend\.env.example` if it does not already exist.

### Step 3: Start the local blockchain

Open **PowerShell Window 1**, navigate to the project root, and run:

```powershell
cd "C:\Users\DELL\OneDrive\Desktop\educational-credential-verification"
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\start-blockchain.ps1
```

Wait until the local Hardhat blockchain is running. Keep this window open.

### Step 4: Deploy the smart contract

Open **PowerShell Window 2**, navigate to the project root, and run:

```powershell
cd "C:\Users\DELL\OneDrive\Desktop\educational-credential-verification"
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\deploy-contract.ps1
```

Run this only after the blockchain is running. Wait for deployment to complete.

### Step 5: Start the backend API

Open **PowerShell Window 3**, navigate to the project root, and run:

```powershell
cd "C:\Users\DELL\OneDrive\Desktop\educational-credential-verification"
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\start-backend.ps1
```

Keep this window open.

### Step 6: Start the frontend

Open **PowerShell Window 4**, navigate to the project root, and run:

```powershell
cd "C:\Users\DELL\OneDrive\Desktop\educational-credential-verification"
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\start-frontend.ps1
```

Keep this window open.

### Step 7: Access the application

Open these addresses in your browser:

- **Web application:** http://localhost:5173
- **Backend API documentation:** http://127.0.0.1:8000/docs

**Default demo admin credentials:**
- Username: `admin`
- Password: `ChangeMe@123`

Change the default password in `backend\.env` before using the application beyond a local demonstration.

### Important note

The local blockchain resets whenever its node is restarted. After restarting it, deploy the smart contract again and restart the backend. Certificates issued before the reset may appear as unknown.

## Netlify deployment

Netlify installs the locked dependencies (including Vite) and builds from `frontend/`, then publishes `frontend/dist/`.
The root Python requirements and the Hardhat project are not part of this build.
This deploy hosts only the frontend. To enable System Status and Admin Login:

1. Run the existing FastAPI app (`uvicorn main:app` from `backend/`) on a publicly reachable HTTPS endpoint. Configure its database and blockchain RPC and contract as required by the existing backend; keep all credentials on the backend.
2. Set the backend's `FRONTEND_ORIGIN` to the exact frontend origin for the deployment you are connecting so the browser can make cross-origin requests. The backend currently accepts one configured frontend origin, so a preview on a different origin is not automatically allowed.
3. Set `VITE_API_BASE_URL` in the Netlify build environment for each applicable deploy context, using the public backend URL, for example `https://backend.example.com/api`. Redeploy after changing it. Do not use a localhost or relative URL for a deployed frontend.

System Status calls `GET /api/health`, and Admin Login calls `POST /api/auth/login` on that backend. The Netlify page rewrites do not handle `/api` requests. Local Vite development and preview still proxy `/api` to `127.0.0.1:8000` when the variable is unset.

## Demo
```powershell
python scripts\seed-demo-data.py --count 5
```
Certificate files and access codes are saved in `storage\certificates\demo\`.

## Tests and benchmark
```powershell
.\scripts\run-all-tests.ps1
cd blockchain; npm run gas; cd ..
python scripts\benchmark.py --certs 20 --rounds 5
```
Results are written to `docs\benchmark-results.md`.

## Known limitations
- Runs on a local test chain. It has not been deployed to a public network.
- One institution (one issuer account) in the demo. The contract supports several issuers.
- Rate limiting is in memory and resets when the backend restarts.
- Demo credentials in `.env.example` are for local development only.
- All data is synthetic. Do not enter real student data.
