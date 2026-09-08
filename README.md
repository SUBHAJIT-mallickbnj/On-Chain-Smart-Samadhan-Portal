# On-Chain Smart Samadhan Portal

A production-ready civic complaint portal that combines department-aware AI classification, MongoDB persistence, authority workflows, citizen tracking, activity history, and optional Sepolia blockchain verification.

**Live application:** https://on-chain-smart-samadhan-portal.onrender.com  
**GitHub repository:** https://github.com/SUBHAJIT-mallickbnj/On-Chain-Smart-Samadhan-Portal

> MongoDB is the primary application database. Render environment variables are used for production secrets; credentials are never stored in this repository.

## What It Does

- Connects citizens through a validated Ethereum wallet address.
- Accepts complaint details, media, address, contact information, and department choice.
- Detects the most appropriate department from complaint text.
- Saves complaints to MongoDB using non-destructive upserts.
- Submits complaint hashes to the configured Sepolia contract when blockchain access is available.
- Keeps complaint records visible even when blockchain or MongoDB has a temporary outage.
- Lets citizens track complaints, review history, mark complaints solved, and raise disputes.
- Lets Super Admin review complaints, filter records, discard complaints, mark them solved, add resolution notes, and manage admins.
- Records status changes and authority messages in an activity history.
- Provides a `/health` endpoint for deployment monitoring.

## Skills and Engineering Practices Used

- Flask backend and server-side HTML template integration.
- REST endpoint design, session authentication, input validation, and error handling.
- MongoDB schema design, indexes, connection pooling, reconnect logic, and non-destructive persistence.
- Data migration from legacy CSV/JSON files into MongoDB.
- Machine-learning inference with multilingual complaint text normalization and department classification.
- Web3 wallet validation, smart-contract reads, transaction submission, gas estimation, and blockchain fallback behavior.
- Admin workflow design for status changes, notes, disputes, filtering, and activity auditing.
- Render production deployment with Gunicorn, environment secrets, Python runtime pinning, and health checks.
- Reliability testing for database outages, blockchain timeouts, cold starts, invalid input, and response-time limits.
- Git/GitHub release workflow with secret exclusion and deployable repository hygiene.

## Technology Stack

| Area | Technology |
| --- | --- |
| Web application | Flask 3.1 |
| Production server | Gunicorn |
| Main database | MongoDB Atlas with PyMongo |
| Data processing | pandas |
| Department model | scikit-learn `SGDClassifier` with trained `complaint_model.pkl` |
| Optional semantic fallback | Sentence Transformers, loaded only when installed and needed |
| Blockchain | Web3.py, Ethereum Sepolia, Solidity contract |
| Authentication | Flask sessions, wallet validation, Super Admin password hashes |
| Media | Local temporary storage with optional Cloudinary upload |
| Hosting | Render Web Service |
| Runtime | Python 3.12, pinned by `.python-version` |

## Department Detection

Classification uses a layered process:

1. Unicode normalization and case folding make multilingual text comparisons consistent.
2. High-priority phrases handle specific complaint patterns first.
3. Department keyword scoring handles common complaint language, including Bengali and Hindi terms.
4. The trained scikit-learn model handles unmatched text when its required embedding path is available.
5. If no model path is available, the application safely returns `General` instead of crashing.

Examples covered by the live application include Water Supply, Electricity, Public Lighting, Waste Management, Drainage, Road Maintenance, Sanitation, Public Health, Traffic, and other configured departments.

## Data and Reliability Design

MongoDB stores the durable application records:

- `complaints`: complaint details, status, blockchain hashes, authority notes, and dispute state.
- `admins`: hashed Super Admin and department-admin accounts.
- `activities`: append-only complaint events.

Important safeguards:

- Complaint writes use targeted `UpdateOne(..., upsert=True)` operations.
- Existing complaint records are not replaced with destructive collection deletion.
- Activity events are inserted individually and mirrored to a local JSON fallback.
- MongoDB connections use bounded timeouts and reconnect after transient failures.
- Legacy CSV and JSON data can be imported into MongoDB on first use.
- A temporary MongoDB outage does not make requests hang indefinitely.
- Render local files are only a fallback, not the production source of truth.

## Run Locally in VS Code

### 1. Clone the repository

```powershell
git clone https://github.com/SUBHAJIT-mallickbnj/On-Chain-Smart-Samadhan-Portal.git
cd On-Chain-Smart-Samadhan-Portal
code .
```

### 2. Create a virtual environment

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configure environment variables

Copy the safe template:

```powershell
Copy-Item .env.example .env
```

Set the values in `.env` locally. At minimum:

```dotenv
MONGODB_URI=mongodb+srv://USER:PASSWORD@CLUSTER.mongodb.net/?retryWrites=true&w=majority
MONGODB_DATABASE=complaint_classifier
FLASK_SECRET_KEY=replace-with-a-long-random-secret
BLOCKCHAIN_NETWORK=https://sepolia.infura.io/v3/YOUR_PROJECT_ID
PRIVATE_KEY=your-development-wallet-private-key
INFURA_PROJECT_ID=your-project-id
```

Never commit `.env`, private keys, database passwords, or API secrets. The repository `.gitignore` already excludes local secrets and runtime files.

### 4. Start the application

```powershell
python app.py
```

Open:

- Public portal: http://127.0.0.1:5000/
- Health check: http://127.0.0.1:5000/health
- Super Admin: http://127.0.0.1:5000/admin/login

The default development admin is created only when no admin exists:

```text
Admin ID: superadmin
Password: Admin@123
```

Change this password before production use.

### 5. Run with Gunicorn

For a production-like local run:

```powershell
$env:PORT=5000
gunicorn --bind 0.0.0.0:$env:PORT app:app
```

## Test the Project

Syntax and diagnostics:

```powershell
python -m py_compile app.py mongo_store.py activity_log.py admin_manager.py blockchain_manager.py
```

Blockchain and contract checks:

```powershell
python test_blockchain.py
python testnet_setup_checker.py
```

Live health check:

```powershell
python -c "import requests; print(requests.get('http://127.0.0.1:5000/health', timeout=10).json())"
```

The recommended acceptance flow is:

1. Open the public portal.
2. Connect a valid wallet address.
3. Submit a complaint through Preview and Confirm.
4. Verify the complaint reference in MongoDB.
5. Open Super Admin and confirm the complaint is visible.
6. Mark it solved with an authority note.
7. Track the updated status as the citizen.
8. Raise a dispute and confirm the complaint reopens.
9. Confirm activity events and MongoDB data remain intact.

## Render Deployment

The repository includes `render.yaml` with:

```yaml
buildCommand: pip install -r requirements.txt
startCommand: gunicorn --bind 0.0.0.0:$PORT app:app
```

To deploy from Render:

1. Create a Render **Web Service** from the GitHub repository.
2. Select branch `main`, runtime `Python 3`, and the free or paid plan you need.
3. Use Python 3.12, as specified by `.python-version`.
4. Set these Render environment variables:

```text
MONGODB_URI            Secret MongoDB Atlas connection string
MONGODB_DATABASE       complaint_classifier
FLASK_SECRET_KEY       Long random secret
BLOCKCHAIN_NETWORK     Sepolia RPC URL
PRIVATE_KEY            Server wallet private key for blockchain submissions
INFURA_PROJECT_ID      Infura project ID
GAS_LIMIT              1200000
GAS_PRICE              3
```

5. Deploy and wait for the service to report **Live**.
6. Verify:

```text
https://YOUR-SERVICE.onrender.com/health
```

Expected response:

```json
{"database":"mongodb","status":"ok"}
```

Render Free instances can sleep after inactivity, so the first request may be slow. MongoDB Atlas remains the persistent database; do not rely on Render's local filesystem for permanent data.

## MongoDB Atlas Checklist

- Create a database named `complaint_classifier`.
- Add the Render outbound IP policy required by your Atlas setup. For development, Atlas may use `0.0.0.0/0`, but restrict access where possible.
- Create a least-privilege database user.
- Confirm the connection string includes the correct username, password, cluster, and database permissions.
- Monitor storage before the cluster reaches its limit.
- Upgrade the Atlas tier or archive old records before storage is exhausted.
- Export periodic backups; Google Drive is appropriate for backups, not as the primary database.

## Project Layout

```text
app.py                    Flask routes and complaint workflows
mongo_store.py            MongoDB connection and complaint persistence
activity_log.py           Activity history with outage fallback
admin_manager.py          Admin authentication and management
blockchain_manager.py     Web3 connection and contract operations
config.py                 Environment-backed configuration
contracts/                Solidity contract and deployment helper
embedding_model/          Optional local embedding model metadata
complaint_model.pkl       Trained department classifier
contract_info.json        Deployed contract address and ABI
static/                   CSS, JavaScript, and upload paths
templates/                Flask HTML templates
render.yaml               Render service configuration
.env.example              Safe environment-variable template
```

## Security Notes

- Do not commit `.env` or secrets.
- Rotate any credential that has been exposed in chat, logs, screenshots, or source history.
- Use a dedicated server wallet with limited funds for Sepolia testing.
- Use a strong `FLASK_SECRET_KEY` in Render.
- Change the default admin password before production launch.
- Keep MongoDB users least-privileged and monitor Atlas access logs.

## Current Deployment

The application is deployed from GitHub `main` to Render and uses MongoDB Atlas as its primary database. The deployment has been live-tested for complaint creation, department detection, MongoDB persistence, Super Admin visibility, authority message/status updates, citizen tracking, dispute reopening, activity history, and health monitoring.
