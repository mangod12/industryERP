# Steel ERP - Local Deployment Guide (Windows)

## Option 1: Docker Deployment (Recommended for Windows)

### Prerequisites
1. Install Docker Desktop for Windows: https://www.docker.com/products/docker-desktop
2. Enable WSL 2 backend in Docker Desktop settings

### Quick Start

1. **Start the services**:
```bash
docker-compose up -d
```

2. **Access the application**:
- ERPNext: http://localhost:8000
- Default credentials: Administrator / admin

3. **Install Steel ERP app**:
```bash
docker exec -it steel-erpnext-1 bench --site frontend install-app steel_erp
docker exec -it steel-erpnext-1 bench --site frontend migrate
```

### Stop the services
```bash
docker-compose down
```

---

## Option 2: Direct Python Deployment (Development Mode)

Since you have Python and the existing backend, we can run a hybrid setup:

### Step 1: Install dependencies
```bash
cd C:\Users\ansha\Downloads\next_project
pip install -r requirements.txt
```

### Step 2: Start existing FastAPI backend
```bash
cd backend_core
python -m uvicorn app.main:app --reload --port 8001
```

### Step 3: Serve frontend
```bash
cd kumar_frontend
python -m http.server 5500
```

### Step 4: Access applications
- Frontend: http://localhost:5500
- API: http://localhost:8001/docs

---

## Option 3: Full ERPNext Installation (Linux/WSL Required)

### On Windows with WSL2:

1. **Install WSL2**:
```powershell
wsl --install
```

2. **Inside WSL2 Ubuntu**:
```bash
# Install dependencies
sudo apt-get update
sudo apt-get install -y python3-dev python3-pip python3-setuptools redis-server
sudo apt-get install -y mariadb-server mariadb-client libmysqlclient-dev
sudo apt-get install -y nodejs npm
sudo npm install -g yarn

# Install bench
sudo pip3 install frappe-bench

# Create bench
bench init frappe-bench --frappe-branch version-15
cd frappe-bench

# Create site
bench new-site steel.local --admin-password admin

# Get ERPNext
bench get-app erpnext --branch version-15

# Install ERPNext
bench --site steel.local install-app erpnext

# Copy steel_erp app
cp -r /mnt/c/Users/ansha/Downloads/next_project/steel_erp apps/

# Install steel_erp
bench --site steel.local install-app steel_erp

# Start
bench start
```

3. **Access**: http://localhost:8000

---

## Recommended: Use Existing System for Now

Since you already have a working FastAPI + SQLite system, I recommend:

### Quick Deploy Current System

**Terminal 1 - Start Backend**:
```bash
cd C:\Users\ansha\Downloads\next_project\backend_core
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

**Terminal 2 - Start Frontend**:
```bash
cd C:\Users\ansha\Downloads\next_project\kumar_frontend
python -m http.server 5500
```

**Access**:
- Frontend: http://localhost:5500
- API Docs: http://localhost:8001/docs
- Dashboard: http://localhost:5500/index.html

The steel_erp folder contains the ERPNext customization that can be deployed when you're ready to migrate to ERPNext.
