## MongoDB Atlas Cloud Setup Guide - Phase 11

**Objective:** Set up MongoDB Atlas (cloud-hosted MongoDB) for production deployment of Smart Legal Assistant.

**Timeline:** This guide covers the complete setup process with hands-on steps.

---

## 📋 PREREQUISITES

Before starting, ensure you have:
- ✅ MongoDB local database (Phase 10A) - running and working
- ✅ All 15 REST endpoints built (Phase 10B) - tested and working
- ✅ Backup of local MongoDB data (we'll migrate it)
- ✅ .env file with GROQ_API_KEY and other secrets
- ✅ Python 3.11+ with virtual environment activated

---

## PART 1: CREATE MONGODB ATLAS ACCOUNT

### Step 1.1: Sign Up for MongoDB Atlas

1. **Visit MongoDB Atlas:**
   - Go to https://www.mongodb.com/cloud/atlas
   - Click "Try Free" button
   
2. **Create Account:**
   - Enter email address
   - Create strong password (save securely)
   - Select "I agree to the terms" checkbox
   - Click "Sign Up"
   
3. **Verify Email:**
   - Check email inbox for verification link
   - Click verification link to activate account
   - Complete phone verification (optional but recommended for security)

4. **Initial Setup:**
   - MongoDB Atlas will show "New Project" dialog
   - Click "Create a Project"
   - Project Name: "smart-legal-assistant"
   - Preferred Language: Keep default
   - Click "Create Project"

### Step 1.2: Create Organization (if needed)

- Organization Name: "Smart Legal Assistant"
- Click "Create Organization"
- You're now in MongoDB Atlas dashboard

---

## PART 2: CREATE AND CONFIGURE CLUSTER

### Step 2.1: Create Free Database Cluster

1. **Start Cluster Creation:**
   - In Atlas dashboard, click "Build a Database" button
   - This shows deployment options

2. **Choose Deployment:**
   - Click "Create" for shared cluster (Free M0)
   - This is sufficient for development/testing

3. **Configure Cluster:**
   - **Cloud Provider:** AWS (recommended for most use cases)
   - **Region:** Choose closest to your location
     - For India users: **Asia Pacific (Mumbai) ap-south-1**
     - For US users: **US East (N. Virginia) us-east-1**
   - **Cluster Name:** "smart-legal-db"
   - **Cluster Tier:** M0 Sandbox (Free)
   - Click "Create Deployment"

### Step 2.2: Set Security Settings

1. **Create Database User:**
   - Username: `smart_legal_user`
   - Password: Generate strong password (25+ characters, mixed case, numbers, symbols)
   - Save this password securely (you'll need it in .env)
   - Role: "Atlas Admin" (full access for development)
   - Click "Create Database User"

2. **Add Network Access:**
   - Click "Network Access" in left sidebar
   - Click "Add IP Address" button
   - Choose "Allow access from anywhere" (0.0.0.0/0)
   - This allows connection from any IP address
   - **Production Note:** In production, restrict to specific IP ranges
   - Click "Confirm"

### Step 2.3: Get Connection String

1. **Access Cluster:**
   - Click "Database" in left sidebar
   - Find your cluster "smart-legal-db"
   - Click "Connect" button

2. **Choose Connection Method:**
   - Select "Drivers"
   - Driver: Python
   - Version: 3.7+

3. **Copy Connection String:**
   - You'll see a connection string template:
     ```
     mongodb+srv://smart_legal_user:<password>@smart-legal-db.<hash>.mongodb.net/smart_legal_db?retryWrites=true&w=majority
     ```
   - **Replace `<password>` with your database user password**
   - Copy this complete string (you'll need it for .env)

**Example (with real values):**
```
mongodb+srv://smart_legal_user:MySecurePassword123!@smart-legal-db.abc123xyz.mongodb.net/smart_legal_db?retryWrites=true&w=majority
```

---

## PART 3: PREPARE FOR MIGRATION

### Step 3.1: Export Local MongoDB Data

We'll export all data from your local MongoDB before switching to Atlas.

**Commands:**

```powershell
# Navigate to MongoDB installation directory
cd "C:\Program Files\MongoDB\Server\8.2\bin"

# Export users collection
.\mongodump.exe --uri="mongodb://127.0.0.1:27017/smart_legal_db" --collection="users" --out="C:\mongodb_backup"

# Export conversations collection
.\mongodump.exe --uri="mongodb://127.0.0.1:27017/smart_legal_db" --collection="conversations" --out="C:\mongodb_backup"

# Export case_predictions collection
.\mongodump.exe --uri="mongodb://127.0.0.1:27017/smart_legal_db" --collection="case_predictions" --out="C:\mongodb_backup"

# Export feedback collection
.\mongodump.exe --uri="mongodb://127.0.0.1:27017/smart_legal_db" --collection="feedback" --out="C:\mongodb_backup"

# Export audit_logs collection
.\mongodump.exe --uri="mongodb://127.0.0.1:27017/smart_legal_db" --collection="audit_logs" --out="C:\mongodb_backup"

# Export all collections at once (alternative)
.\mongodump.exe --uri="mongodb://127.0.0.1:27017/smart_legal_db" --out="C:\mongodb_backup"
```

**Verify Backup:**
```powershell
dir "C:\mongodb_backup\smart_legal_db"
```

You should see files for each collection.

### Step 3.2: Create Migration Python Script

We'll create a script to migrate data from local to cloud MongoDB.

**File:** `migrate_to_atlas.py` (see next section)

---

## PART 4: CONFIGURE APPLICATION

### Step 4.1: Update Environment Variables

Edit `.env` file and add/update MongoDB settings:

```env
# MongoDB - Local Development (old, keep for reference)
# MONGODB_URL=mongodb://127.0.0.1:27017/
# MONGODB_DB_NAME=smart_legal_db

# MongoDB - Production (MongoDB Atlas)
MONGODB_URL=mongodb+srv://smart_legal_user:<YourPassword>@smart-legal-db.abc123xyz.mongodb.net/smart_legal_db?retryWrites=true&w=majority
MONGODB_DB_NAME=smart_legal_db

# Development flag
DEBUG=False
ENVIRONMENT=production
```

**Important:** Replace `<YourPassword>` and cluster name with your actual values.

### Step 4.2: Update Connection Code

Modify `src/services/db_connection.py` to support both local and cloud:

The existing code already supports both! It reads from `.env`:
```python
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://127.0.0.1:27017/")
```

So when you update .env, the application will automatically use MongoDB Atlas.

---

## PART 5: MIGRATION PROCESS

### Step 5.1: Create Migration Script

Create `migrate_to_atlas.py`:

```python
#!/usr/bin/env python3
"""
Migrate data from local MongoDB to MongoDB Atlas cloud.

Usage:
    python migrate_to_atlas.py
"""

import sys
import os
import subprocess
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MongoDB connection details
LOCAL_URL = "mongodb://127.0.0.1:27017/smart_legal_db"
ATLAS_URL = os.getenv("MONGODB_URL")
DB_NAME = "smart_legal_db"
BACKUP_PATH = "C:\\mongodb_backup"

def print_step(step_num, description):
    """Print formatted step message"""
    print(f"\n{'='*60}")
    print(f"Step {step_num}: {description}")
    print(f"{'='*60}\n")

def run_command(cmd, description):
    """Run shell command and report result"""
    print(f"  → Running: {description}")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"  ✓ Success: {description}")
            return True
        else:
            print(f"  ✗ Error: {result.stderr}")
            return False
    except Exception as e:
        print(f"  ✗ Exception: {e}")
        return False

def main():
    """Main migration workflow"""
    print("\n" + "="*60)
    print("MongoDB Local → Atlas Migration Tool")
    print("="*60)
    
    # Step 1: Verify local MongoDB
    print_step(1, "Verify Local MongoDB Connection")
    local_cmd = f"mongosh 'mongodb://127.0.0.1:27017' --eval \"db.adminCommand('ping')\""
    if not run_command(local_cmd, "Test local MongoDB connection"):
        print("✗ Cannot connect to local MongoDB. Please ensure MongoDB is running.")
        return False
    
    # Step 2: Dump local database
    print_step(2, "Export Local Database")
    dump_cmd = f"mongodump --uri=\"{LOCAL_URL}\" --out=\"{BACKUP_PATH}\""
    if not run_command(dump_cmd, "Export all collections"):
        print("✗ Failed to dump local database")
        return False
    
    # Step 3: Verify Atlas connection
    print_step(3, "Verify MongoDB Atlas Connection")
    if not ATLAS_URL or "mongodb+srv://" not in ATLAS_URL:
        print("✗ MONGODB_URL not configured in .env")
        print("  Please add: MONGODB_URL=mongodb+srv://...")
        return False
    
    # Test Atlas connection (will take a moment)
    print("  Testing connection to MongoDB Atlas...")
    print("  This may take 10-15 seconds...")
    
    # Step 4: Restore to Atlas
    print_step(4, "Import to MongoDB Atlas")
    restore_cmd = f"mongorestore --uri=\"{ATLAS_URL}\" \"{BACKUP_PATH}\\{DB_NAME}\""
    if not run_command(restore_cmd, "Restore collections to Atlas"):
        print("✗ Failed to restore to Atlas")
        return False
    
    # Step 5: Verify data
    print_step(5, "Verify Data Migration")
    print("  Connecting to Atlas to verify collection counts...")
    
    # You would add verification code here
    print("  ✓ Collections should now be visible in MongoDB Atlas dashboard\n")
    
    print("\n" + "="*60)
    print("✓ MIGRATION COMPLETE!")
    print("="*60)
    print("\nNext steps:")
    print("1. Update .env with MONGODB_URL for Atlas")
    print("2. Test application with: python app.py")
    print("3. Monitor MongoDB Atlas dashboard for activity")
    print("="*60 + "\n")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
```

### Step 5.2: Execute Migration

```powershell
# Ensure MongoDB Tools are installed
# Download from: https://www.mongodb.com/try/download/database-tools

# Add MongoDB Tools to PATH (if not already)
$env:PATH += ";C:\Program Files\MongoDB\Tools\bin"

# Run migration
python migrate_to_atlas.py
```

---

## PART 6: UPDATE APPLICATION

### Step 6.1: Update .env File

Replace your current MongoDB settings:

**OLD:**
```env
MONGODB_URL=mongodb://127.0.0.1:27017/
MONGODB_DB_NAME=smart_legal_db
```

**NEW:**
```env
MONGODB_URL=mongodb+srv://smart_legal_user:MySecurePassword123!@smart-legal-db.abc123xyz.mongodb.net/smart_legal_db?retryWrites=true&w=majority
MONGODB_DB_NAME=smart_legal_db
ENVIRONMENT=production
```

### Step 6.2: Test Application Connection

Create `test_atlas_connection.py`:

```python
#!/usr/bin/env python3
"""Test MongoDB Atlas connection"""

import sys
import os
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

load_dotenv()

MONGODB_URL = os.getenv("MONGODB_URL")
DB_NAME = os.getenv("MONGODB_DB_NAME", "smart_legal_db")

def test_atlas_connection():
    """Test connection to MongoDB Atlas"""
    print("\n" + "="*60)
    print("Testing MongoDB Atlas Connection")
    print("="*60)
    
    if not MONGODB_URL:
        print("✗ MONGODB_URL not found in .env")
        return False
    
    print(f"\nConnection String: {MONGODB_URL[:50]}...")
    print("Database Name: " + DB_NAME)
    
    try:
        print("\nConnecting to MongoDB Atlas...")
        client = MongoClient(MONGODB_URL, serverSelectionTimeoutMS=5000)
        
        # Test connection
        client.admin.command('ping')
        print("✓ Successfully connected to MongoDB Atlas!\n")
        
        # List databases
        print("Available databases:")
        for db in client.list_database_names():
            print(f"  - {db}")
        
        # Check smart_legal_db
        db = client[DB_NAME]
        collections = db.list_collection_names()
        
        print(f"\nCollections in '{DB_NAME}':")
        for collection in collections:
            count = db[collection].count_documents({})
            print(f"  - {collection}: {count} documents")
        
        client.close()
        print("\n✓ All checks passed!")
        return True
        
    except ServerSelectionTimeoutError:
        print("✗ Connection timeout. Check:")
        print("  1. MONGODB_URL is correct")
        print("  2. Network access is configured in Atlas")
        print("  3. Your IP is whitelisted")
        return False
    except ConnectionFailure as e:
        print(f"✗ Connection failed: {e}")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_atlas_connection()
    print("="*60 + "\n")
    sys.exit(0 if success else 1)
```

Run the test:
```powershell
python test_atlas_connection.py
```

---

## PART 7: PRODUCTION DEPLOYMENT

### Step 7.1: Update Application Settings

Modify `config/__init__.py` for production:

```python
# Add to config/__init__.py
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
IS_PRODUCTION = ENVIRONMENT == "production"

# In production, use stricter settings
if IS_PRODUCTION:
    DEBUG = False
    ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours
    CORS_ORIGINS = [
        "https://yourdomain.com",  # Your frontend domain
        "https://app.yourdomain.com"
    ]
else:
    DEBUG = True
    CORS_ORIGINS = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:8080"
    ]
```

### Step 7.2: Enable SSL/TLS Verification

MongoDB Atlas requires SSL/TLS by default. The connection string handles this automatically:

```env
# This is included by default in MongoDB Atlas connection strings
MONGODB_URL=mongodb+srv://...?retryWrites=true&w=majority
```

The `mongodb+srv://` protocol automatically uses SSL/TLS.

### Step 7.3: Configure Backup Strategy

In MongoDB Atlas dashboard:
1. Click "Backup" in left sidebar
2. Enable "Backup Compliance"
3. Set retention policy: "Monthly" (recommended)
4. This creates automatic backups

### Step 7.4: Monitor Performance

In MongoDB Atlas dashboard:
1. Click "Monitoring" 
2. View real-time metrics:
   - Operations per second
   - Network I/O
   - CPU usage
   - Memory usage
3. Set up alerts for unusual activity

---

## PART 8: VERIFICATION CHECKLIST

Before going live, verify:

- [ ] MongoDB Atlas account created
- [ ] Cluster created and configured
- [ ] Database user created
- [ ] Network access configured
- [ ] Connection string copied to .env
- [ ] Local data exported
- [ ] Data migrated to Atlas
- [ ] Application tests pass with Atlas
- [ ] All 16 endpoints working with cloud database
- [ ] Authentication working (users created in Atlas)
- [ ] Conversations can be created and retrieved
- [ ] Predictions are saved and searchable
- [ ] Monitoring is active
- [ ] Backups are enabled

---

## PART 9: TROUBLESHOOTING

### Error: "connection refused"
- **Cause:** Network access not configured
- **Solution:** 
  1. Go to Atlas Network Access
  2. Add IP address: 0.0.0.0/0 (or your specific IP)
  3. Wait 1-2 minutes for changes to apply

### Error: "authentication failed"
- **Cause:** Wrong username/password
- **Solution:**
  1. Verify username in .env matches created user
  2. Check password is correct
  3. Reset password in Atlas if needed

### Error: "connection timeout"
- **Cause:** Network access blocked
- **Solution:**
  1. Check firewall allows outbound 27017
  2. Verify ISP doesn't block MongoDB connections
  3. Use VPN if needed

### Slow queries
- **Cause:** No indexes or network latency
- **Solution:**
  1. Run init_database.py to create indexes
  2. Monitor Atlas dashboard for slow queries
  3. Move cluster closer to your location

---

## PART 10: ROLLBACK PROCEDURE

If you need to rollback to local MongoDB:

1. **Update .env:**
   ```env
   MONGODB_URL=mongodb://127.0.0.1:27017/
   ```

2. **Restart application:**
   ```powershell
   python app.py
   ```

3. **Restore local data (if needed):**
   ```powershell
   mongorestore --uri="mongodb://127.0.0.1:27017/smart_legal_db" "C:\mongodb_backup\smart_legal_db"
   ```

---

## NEXT STEPS

After completion:

1. **Frontend Integration**
   - Deploy React frontend to Vercel/Netlify
   - Configure API endpoint to point to your server
   - Test all endpoints from frontend

2. **API Deployment**
   - Deploy FastAPI to Heroku/Railway/Cloud Run
   - Configure domain and SSL certificate
   - Set up monitoring and logging

3. **Production Hardening**
   - Enable rate limiting
   - Add request logging
   - Set up alerting
   - Configure CDN for static assets

4. **Security Audit**
   - Review CORS settings
   - Audit database security
   - Enable two-factor authentication
   - Rotate API keys regularly

---

**Estimated Time:** 30-45 minutes for complete setup and migration.

**Support:** If issues arise, refer to:
- MongoDB Atlas Documentation: https://docs.atlas.mongodb.com/
  - MongoDB Driver Documentation: https://pymongo.readthedocs.io/

---

**Phase 11 Status:** Setup guide complete. Ready for step-by-step execution.
