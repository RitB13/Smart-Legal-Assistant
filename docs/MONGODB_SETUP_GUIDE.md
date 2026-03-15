# MongoDB Setup Guide - Complete Step-by-Step

## Part 1: MongoDB Local Server Setup

### Step 1.1: Verify MongoDB Installation
MongoDB is already downloaded. Let's verify it's installed correctly.

**Do this:**
```powershell
mongod --version
```

**Expected output:**
```
db version v5.0.0  (or any version 5.0+)
Build Info: ...
```

If you see this, MongoDB is installed ✅

---

### Step 1.2: Create a Data Directory for MongoDB

MongoDB needs a folder to store its data. By default it looks for `C:\data\db`

**Do this:**
```powershell
# Create the directory
mkdir C:\data\db

# Verify it was created
dir C:\data\db
```

**Expected:** You should see an empty directory ✅

---

### Step 1.3: Start MongoDB Server

You need to start the MongoDB server in the background. This will keep running while you work.

**Option A: Simple Way (Recommended for First Time)**

```powershell
# Navigate to MongoDB bin folder (adjust path based on your version)
# Usually something like:
cd "C:\Program Files\MongoDB\Server\5.0\bin"

# Or if installed differently, find it:
where mongod

# Once you know the path, start the server:
mongod
```

**Expected output:**
```
[initandlisten] waiting for connections on port 27017
```

**This means MongoDB is running!** ✅

Keep this terminal open - don't close it. Open a NEW terminal for the next steps.

---

### Step 1.4: Connect to MongoDB (Verify It Works)

Open a **NEW PowerShell terminal** (keep the mongod one running):

```powershell
# Navigate to MongoDB bin folder
cd "C:\Program Files\MongoDB\Server\5.0\bin"

# Start the MongoDB shell
mongosh
```

**Expected:**
```
Current Mongosh Log ID: xxxxxxxxxxxxxx
Connecting to:          mongodb://127.0.0.1:27017/
...
test>
```

Great! You're now in MongoDB shell ✅

---

## Part 2: Create Database and Collections

Now you're in the MongoDB shell (`test>`). Let's create your database.

### Step 2.1: Create the Database

```javascript
// In the MongoDB shell, type:
use smart_legal_db
```

**Expected output:**
```
switched to db smart_legal_db
```

✅ Database created!

---

### Step 2.2: Create Collections (Tables)

In the MongoDB shell, run these commands **one by one**:

```javascript
// Create users collection
db.createCollection("users")

// Create conversations collection
db.createCollection("conversations")

// Create case_predictions collection
db.createCollection("case_predictions")

// Create feedback collection
db.createCollection("feedback")

// Create audit_logs collection
db.createCollection("audit_logs")
```

**Expected:** Each should return `{ ok: 1 }`

---

### Step 2.3: Verify Collections Were Created

```javascript
// In MongoDB shell, type:
show collections
```

**Expected output:**
```
audit_logs
case_predictions
conversations
feedback
users
```

✅ All 5 collections created!

---

### Step 2.4: Create Indexes (for faster queries)

```javascript
// Users index - email must be unique
db.users.createIndex({ "email": 1 }, { unique: true })

// Conversations indexes
db.conversations.createIndex({ "user_id": 1 })
db.conversations.createIndex({ "created_at": -1 })

// Case predictions indexes
db.case_predictions.createIndex({ "user_id": 1 })
db.case_predictions.createIndex({ "created_at": -1 })

// Feedback index
db.feedback.createIndex({ "prediction_id": 1 })

// Audit logs index
db.audit_logs.createIndex({ "user_id": 1 })
db.audit_logs.createIndex({ "created_at": -1 })
```

**Expected:** Each should return something like `{ "numIndexesAfter": X }`

---

### Step 2.5: Check Database Structure

```javascript
// List databases
show databases

// Show current database details
db.getCollectionNames()

// Check a collection's indexes
db.users.getIndexes()
```

✅ Your database is now ready!

---

## Part 3: Connect Python to MongoDB

Now we'll set up Python to connect to MongoDB.

### Step 3.1: Install MongoDB Python Driver

```powershell
# Make sure you're in your project folder
cd D:\Smart-Legal-Assistant

# Activate virtual environment
.\.venv\Scripts\activate

# Install pymongo (MongoDB Python driver)
pip install pymongo
pip install python-dotenv
```

**Expected:**
```
Successfully installed pymongo-4.x.x
```

✅ MongoDB Python driver installed!

---

### Step 3.2: Create Configuration File

Create a file: `config/db_config.py`

**Content:**
```python
import os
from dotenv import load_dotenv

load_dotenv()

# MongoDB Configuration
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://127.0.0.1:27017/")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "smart_legal_db")

# These are your connection details
DB_CONFIG = {
    "url": MONGODB_URL,
    "db_name": MONGODB_DB_NAME,
    "timeout": 5000,
}

print(f"[DB CONFIG] Connecting to: {MONGODB_URL}")
print(f"[DB CONFIG] Database: {MONGODB_DB_NAME}")
```

---

### Step 3.3: Create .env File

Create a file: `.env` (in root folder: `D:\Smart-Legal-Assistant\.env`)

**Content:**
```
# MongoDB Configuration
MONGODB_URL=mongodb://127.0.0.1:27017/
MONGODB_DB_NAME=smart_legal_db

# Later you'll use MongoDB Atlas (cloud version)
# MONGODB_URL=mongodb+srv://username:password@cluster.mongodb.net/
```

---

### Step 3.4: Create Database Connection Module

Create a file: `src/services/db_connection.py`

**Content:**
```python
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError, ConnectionFailure
from config.db_config import DB_CONFIG
import logging

logger = logging.getLogger(__name__)

class DatabaseConnection:
    """Singleton connection to MongoDB"""
    _instance = None
    _client = None
    _db = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseConnection, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize database connection"""
        if self._client is None:
            try:
                self._client = MongoClient(
                    DB_CONFIG["url"],
                    serverSelectionTimeoutMS=DB_CONFIG["timeout"]
                )
                
                # Test the connection
                self._client.admin.command('ping')
                logger.info("✅ Connected to MongoDB successfully")
                
                # Get database
                self._db = self._client[DB_CONFIG["db_name"]]
                logger.info(f"✅ Using database: {DB_CONFIG['db_name']}")
                
            except ServerSelectionTimeoutError:
                logger.error("❌ Could not connect to MongoDB server!")
                logger.error("   Make sure: mongod is running")
                raise
            except Exception as e:
                logger.error(f"❌ Database connection error: {e}")
                raise
    
    @property
    def client(self):
        """Get MongoDB client"""
        return self._client
    
    @property
    def db(self):
        """Get database instance"""
        return self._db
    
    def close(self):
        """Close database connection"""
        if self._client:
            self._client.close()
            self._client = None
            self._db = None
            logger.info("Database connection closed")
    
    def get_collection(self, collection_name):
        """Get a specific collection"""
        return self._db[collection_name]

# Create singleton instance
db_connection = DatabaseConnection()

def get_db():
    """Get database instance (for dependency injection)"""
    return db_connection.db

def get_collection(collection_name):
    """Get collection by name"""
    return db_connection.get_collection(collection_name)
```

---

### Step 3.5: Test the Connection

Create a file: `test_db_connection.py`

**Content:**
```python
#!/usr/bin/env python3
"""Test MongoDB connection"""

import sys
sys.path.insert(0, 'src')

from services.db_connection import db_connection

def test_connection():
    """Test if we can connect to MongoDB"""
    try:
        print("[TEST] Testing MongoDB connection...")
        
        # Get database
        db = db_connection.db
        print(f"✅ Connected to database: {db.name}")
        
        # List collections
        collections = db.list_collection_names()
        print(f"✅ Collections found: {collections}")
        
        # Check each collection
        for collection_name in ["users", "conversations", "case_predictions", "feedback", "audit_logs"]:
            collection = db[collection_name]
            count = collection.count_documents({})
            print(f"   - {collection_name}: {count} documents")
        
        print("\n✅ All tests passed! MongoDB is ready.")
        
        return True
        
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False

if __name__ == "__main__":
    test_connection()
```

**Run it:**
```powershell
python test_db_connection.py
```

**Expected output:**
```
[TEST] Testing MongoDB connection...
✅ Connected to database: smart_legal_db
✅ Collections found: ['audit_logs', 'case_predictions', 'conversations', 'feedback', 'users']
   - users: 0 documents
   - conversations: 0 documents
   - case_predictions: 0 documents
   - feedback: 0 documents
   - audit_logs: 0 documents

✅ All tests passed! MongoDB is ready.
```

✅ Python can connect to MongoDB!

---

## Part 4: Create Data Models

Now we'll create Python models for our data (Pydantic models).

### Step 4.1: Create User Model

Create a file: `src/models/db_models.py`

**Content:**
```python
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional, List
from bson import ObjectId

# ==================== USER MODEL ====================

class UserBase(BaseModel):
    """Base user data (without ID or timestamps)"""
    email: EmailStr
    name: str
    preferred_language: str = "en"  # en, hi, bn, etc.
    jurisdiction: str = "india"

class UserCreate(UserBase):
    """Data needed to create a user"""
    password: str  # Will be hashed

class UserInDB(UserBase):
    """User data as stored in database"""
    id: str = Field(..., alias="_id")
    password_hash: str  # Hashed password, not plain password
    created_at: datetime
    updated_at: datetime
    is_active: bool = True
    
    class Config:
        populate_by_name = True  # Allow both 'id' and '_id'

class User(UserBase):
    """User data returned to frontend (without password)"""
    id: str = Field(..., alias="_id")
    created_at: datetime
    updated_at: datetime
    
    class Config:
        populate_by_name = True

# ==================== CONVERSATION MODEL ====================

class MessageInConversation(BaseModel):
    """Single message in a conversation"""
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime
    language: Optional[str] = None

class ConversationBase(BaseModel):
    """Base conversation data"""
    title: str
    language: str = "en"

class ConversationCreate(ConversationBase):
    """Data needed to create a conversation"""
    user_id: str

class ConversationInDB(ConversationBase):
    """Conversation as stored in database"""
    id: str = Field(..., alias="_id")
    user_id: str
    messages: List[MessageInConversation] = []
    created_at: datetime
    updated_at: datetime
    
    class Config:
        populate_by_name = True

class Conversation(ConversationBase):
    """Conversation returned to frontend"""
    id: str = Field(..., alias="_id")
    messages: List[MessageInConversation] = []
    created_at: datetime
    updated_at: datetime
    
    class Config:
        populate_by_name = True

# ==================== CASE PREDICTION MODEL ====================

class CasePredictionMetadata(BaseModel):
    """Metadata about a prediction"""
    case_name: str
    case_type: str
    year: int
    jurisdiction_state: str
    damages: Optional[float] = None
    parties_count: int = 2
    is_appeal: bool = False

class PredictionResult(BaseModel):
    """The AI prediction result"""
    verdict: str  # One of: Accepted, Acquitted, Convicted, etc.
    confidence: float  # 0-100
    probabilities: dict  # {"Accepted": 0.45, "Convicted": 0.3, ...}
    shap_explanation: dict  # Feature importance from SHAP
    similar_cases: List[dict] = []
    risk_assessment: dict = {}

class CasePredictionCreate(BaseModel):
    """Data needed to create a prediction"""
    user_id: str
    metadata: CasePredictionMetadata
    result: PredictionResult

class CasePredictionInDB(BaseModel):
    """Prediction as stored in database"""
    id: str = Field(..., alias="_id")
    user_id: str
    metadata: CasePredictionMetadata
    result: PredictionResult
    created_at: datetime
    
    class Config:
        populate_by_name = True

class CasePrediction(BaseModel):
    """Prediction returned to frontend"""
    id: str = Field(..., alias="_id")
    metadata: CasePredictionMetadata
    result: PredictionResult
    created_at: datetime
    
    class Config:
        populate_by_name = True

# ==================== FEEDBACK MODEL ====================

class FeedbackCreate(BaseModel):
    """User feedback on a prediction"""
    prediction_id: str
    user_id: str
    rating: int  # 1-5 stars
    comment: Optional[str] = None
    was_verdict_correct: Optional[bool] = None

class FeedbackInDB(FeedbackCreate):
    """Feedback as stored in database"""
    id: str = Field(..., alias="_id")
    created_at: datetime
    
    class Config:
        populate_by_name = True

# ==================== AUDIT LOG MODEL ====================

class AuditLogCreate(BaseModel):
    """Log entry for auditing"""
    user_id: Optional[str] = None
    action: str  # "predict", "feedback", "login", etc.
    resource: str  # "case_prediction", "conversation", etc.
    resource_id: Optional[str] = None
    details: dict = {}

class AuditLogInDB(AuditLogCreate):
    """Audit log as stored in database"""
    id: str = Field(..., alias="_id")
    created_at: datetime
    
    class Config:
        populate_by_name = True
```

---

## Part 5: Create Database Services

Now we'll create services that interact with the database.

### Step 5.1: Create User Service

Create a file: `src/services/user_service.py`

**Content:**
```python
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from bson import ObjectId
from datetime import datetime
import logging
from typing import Optional
from src.models.db_models import User, UserCreate, UserInDB
from src.services.db_connection import get_collection

logger = logging.getLogger(__name__)

class UserService:
    """Service for managing users"""
    
    @staticmethod
    def create_user(user_data: UserCreate, password_hash: str) -> Optional[User]:
        """Create a new user"""
        collection = get_collection("users")
        
        user_dict = {
            "email": user_data.email,
            "name": user_data.name,
            "preferred_language": user_data.preferred_language,
            "jurisdiction": user_data.jurisdiction,
            "password_hash": password_hash,
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        
        try:
            result = collection.insert_one(user_dict)
            user_dict["_id"] = result.inserted_id
            logger.info(f"✅ User created: {user_data.email}")
            return UserInDB(**user_dict)
        except DuplicateKeyError:
            logger.error(f"❌ User already exists: {user_data.email}")
            return None
        except Exception as e:
            logger.error(f"❌ Error creating user: {e}")
            return None
    
    @staticmethod
    def get_user_by_email(email: str) -> Optional[UserInDB]:
        """Get user by email"""
        collection = get_collection("users")
        user_dict = collection.find_one({"email": email})
        
        if user_dict:
            return UserInDB(**user_dict)
        return None
    
    @staticmethod
    def get_user_by_id(user_id: str) -> Optional[UserInDB]:
        """Get user by ID"""
        collection = get_collection("users")
        
        try:
            user_dict = collection.find_one({"_id": ObjectId(user_id)})
            if user_dict:
                return UserInDB(**user_dict)
        except Exception as e:
            logger.error(f"❌ Error getting user: {e}")
        
        return None
    
    @staticmethod
    def update_user(user_id: str, **kwargs) -> Optional[UserInDB]:
        """Update user data"""
        collection = get_collection("users")
        
        try:
            update_dict = {**kwargs, "updated_at": datetime.utcnow()}
            
            collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": update_dict}
            )
            
            # Return updated user
            return UserService.get_user_by_id(user_id)
        except Exception as e:
            logger.error(f"❌ Error updating user: {e}")
            return None
    
    @staticmethod
    def user_exists(email: str) -> bool:
        """Check if user exists"""
        collection = get_collection("users")
        return collection.find_one({"email": email}) is not None
```

---

### Step 5.2: Create Conversation Service

Create a file: `src/services/conversation_service.py`

**Content:**
```python
from pymongo import DESCENDING
from bson import ObjectId
from datetime import datetime
import logging
from typing import Optional, List
from src.models.db_models import (
    Conversation, ConversationCreate, ConversationInDB,
    MessageInConversation
)
from src.services.db_connection import get_collection

logger = logging.getLogger(__name__)

class ConversationService:
    """Service for managing conversations"""
    
    @staticmethod
    def create_conversation(conv_data: ConversationCreate) -> Optional[ConversationInDB]:
        """Create a new conversation"""
        collection = get_collection("conversations")
        
        conv_dict = {
            "user_id": conv_data.user_id,
            "title": conv_data.title,
            "language": conv_data.language,
            "messages": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        
        try:
            result = collection.insert_one(conv_dict)
            conv_dict["_id"] = result.inserted_id
            logger.info(f"✅ Conversation created: {result.inserted_id}")
            return ConversationInDB(**conv_dict)
        except Exception as e:
            logger.error(f"❌ Error creating conversation: {e}")
            return None
    
    @staticmethod
    def get_conversation(conv_id: str) -> Optional[ConversationInDB]:
        """Get conversation by ID"""
        collection = get_collection("conversations")
        
        try:
            conv_dict = collection.find_one({"_id": ObjectId(conv_id)})
            if conv_dict:
                return ConversationInDB(**conv_dict)
        except Exception as e:
            logger.error(f"❌ Error getting conversation: {e}")
        
        return None
    
    @staticmethod
    def get_user_conversations(user_id: str, limit: int = 20) -> List[ConversationInDB]:
        """Get all conversations for a user"""
        collection = get_collection("conversations")
        
        try:
            conversations = list(collection.find(
                {"user_id": user_id}
            ).sort("created_at", DESCENDING).limit(limit))
            
            return [ConversationInDB(**conv) for conv in conversations]
        except Exception as e:
            logger.error(f"❌ Error getting conversations: {e}")
            return []
    
    @staticmethod
    def add_message(conv_id: str, role: str, content: str, language: Optional[str] = None) -> Optional[ConversationInDB]:
        """Add message to conversation"""
        collection = get_collection("conversations")
        
        try:
            message = {
                "role": role,
                "content": content,
                "timestamp": datetime.utcnow(),
                "language": language,
            }
            
            collection.update_one(
                {"_id": ObjectId(conv_id)},
                {
                    "$push": {"messages": message},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
            
            # Return updated conversation
            return ConversationService.get_conversation(conv_id)
        except Exception as e:
            logger.error(f"❌ Error adding message: {e}")
            return None
    
    @staticmethod
    def delete_conversation(conv_id: str) -> bool:
        """Delete a conversation"""
        collection = get_collection("conversations")
        
        try:
            result = collection.delete_one({"_id": ObjectId(conv_id)})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"❌ Error deleting conversation: {e}")
            return False
    
    @staticmethod
    def search_conversations(user_id: str, query: str) -> List[ConversationInDB]:
        """Search conversations by title"""
        collection = get_collection("conversations")
        
        try:
            conversations = list(collection.find({
                "user_id": user_id,
                "title": {"$regex": query, "$options": "i"}  # Case-insensitive search
            }).sort("created_at", DESCENDING))
            
            return [ConversationInDB(**conv) for conv in conversations]
        except Exception as e:
            logger.error(f"❌ Error searching conversations: {e}")
            return []
```

---

### Step 5.3: Create Case Prediction Service

Create a file: `src/services/prediction_history_service.py`

**Content:**
```python
from pymongo import DESCENDING
from bson import ObjectId
from datetime import datetime
import logging
from typing import Optional, List
from src.models.db_models import (
    CasePrediction, CasePredictionCreate, CasePredictionInDB,
    CasePredictionMetadata, PredictionResult
)
from src.services.db_connection import get_collection

logger = logging.getLogger(__name__)

class PredictionHistoryService:
    """Service for managing case prediction history"""
    
    @staticmethod
    def save_prediction(pred_data: CasePredictionCreate) -> Optional[CasePredictionInDB]:
        """Save a case prediction"""
        collection = get_collection("case_predictions")
        
        pred_dict = {
            "user_id": pred_data.user_id,
            "metadata": pred_data.metadata.dict(),
            "result": pred_data.result.dict(),
            "created_at": datetime.utcnow(),
        }
        
        try:
            result = collection.insert_one(pred_dict)
            pred_dict["_id"] = result.inserted_id
            logger.info(f"✅ Prediction saved: {result.inserted_id}")
            return CasePredictionInDB(**pred_dict)
        except Exception as e:
            logger.error(f"❌ Error saving prediction: {e}")
            return None
    
    @staticmethod
    def get_prediction(pred_id: str) -> Optional[CasePredictionInDB]:
        """Get prediction by ID"""
        collection = get_collection("case_predictions")
        
        try:
            pred_dict = collection.find_one({"_id": ObjectId(pred_id)})
            if pred_dict:
                return CasePredictionInDB(**pred_dict)
        except Exception as e:
            logger.error(f"❌ Error getting prediction: {e}")
        
        return None
    
    @staticmethod
    def get_user_predictions(user_id: str, limit: int = 50) -> List[CasePredictionInDB]:
        """Get all predictions for a user"""
        collection = get_collection("case_predictions")
        
        try:
            predictions = list(collection.find(
                {"user_id": user_id}
            ).sort("created_at", DESCENDING).limit(limit))
            
            return [CasePredictionInDB(**pred) for pred in predictions]
        except Exception as e:
            logger.error(f"❌ Error getting predictions: {e}")
            return []
    
    @staticmethod
    def get_predictions_by_verdict(user_id: str, verdict: str) -> List[CasePredictionInDB]:
        """Get predictions filtered by verdict"""
        collection = get_collection("case_predictions")
        
        try:
            predictions = list(collection.find({
                "user_id": user_id,
                "result.verdict": verdict
            }).sort("created_at", DESCENDING))
            
            return [CasePredictionInDB(**pred) for pred in predictions]
        except Exception as e:
            logger.error(f"❌ Error filtering predictions: {e}")
            return []
    
    @staticmethod
    def search_predictions(user_id: str, query: str) -> List[CasePredictionInDB]:
        """Search predictions by case name"""
        collection = get_collection("case_predictions")
        
        try:
            predictions = list(collection.find({
                "user_id": user_id,
                "metadata.case_name": {"$regex": query, "$options": "i"}
            }).sort("created_at", DESCENDING))
            
            return [CasePredictionInDB(**pred) for pred in predictions]
        except Exception as e:
            logger.error(f"❌ Error searching predictions: {e}")
            return []
    
    @staticmethod
    def delete_prediction(pred_id: str) -> bool:
        """Delete a prediction"""
        collection = get_collection("case_predictions")
        
        try:
            result = collection.delete_one({"_id": ObjectId(pred_id)})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"❌ Error deleting prediction: {e}")
            return False
    
    @staticmethod
    def get_user_stats(user_id: str) -> dict:
        """Get prediction statistics for a user"""
        collection = get_collection("case_predictions")
        
        try:
            total = collection.count_documents({"user_id": user_id})
            
            # Count by verdict
            verdicts = collection.aggregate([
                {"$match": {"user_id": user_id}},
                {"$group": {
                    "_id": "$result.verdict",
                    "count": {"$sum": 1}
                }}
            ])
            
            verdict_counts = {v["_id"]: v["count"] for v in verdicts}
            
            return {
                "total_predictions": total,
                "by_verdict": verdict_counts,
            }
        except Exception as e:
            logger.error(f"❌ Error getting stats: {e}")
            return {"total_predictions": 0, "by_verdict": {}}
```

---

## Part 6: Test Everything

### Step 6.1: Create Integration Test

Create a file: `test_database_integration.py`

**Content:**
```python
#!/usr/bin/env python3
"""Test complete database integration"""

import sys
sys.path.insert(0, 'src')

from datetime import datetime
from services.db_connection import db_connection
from services.user_service import UserService
from services.conversation_service import ConversationService
from services.prediction_history_service import PredictionHistoryService
from models.db_models import (
    UserCreate, ConversationCreate, CasePredictionCreate,
    CasePredictionMetadata, PredictionResult
)

def test_database_integration():
    """Test all database services"""
    
    print("=" * 60)
    print("MONGODB DATABASE INTEGRATION TEST")
    print("=" * 60)
    
    try:
        # TEST 1: Create User
        print("\n[TEST 1] Creating user...")
        user_data = UserCreate(
            email="test@example.com",
            name="Test User",
            preferred_language="en",
            jurisdiction="india"
        )
        user = UserService.create_user(user_data, "hashed_password_123")
        
        if user:
            print(f"  ✅ User created: {user.email}")
            user_id = str(user.id)
        else:
            print("  ❌ Failed to create user")
            return False
        
        # TEST 2: Get User
        print("\n[TEST 2] Retrieving user...")
        retrieved_user = UserService.get_user_by_email("test@example.com")
        if retrieved_user:
            print(f"  ✅ User retrieved: {retrieved_user.name}")
        else:
            print("  ❌ Failed to retrieve user")
            return False
        
        # TEST 3: Create Conversation
        print("\n[TEST 3] Creating conversation...")
        conv_data = ConversationCreate(
            user_id=user_id,
            title="Initial Consultation",
            language="en"
        )
        conversation = ConversationService.create_conversation(conv_data)
        
        if conversation:
            print(f"  ✅ Conversation created: {conversation.title}")
            conv_id = str(conversation.id)
        else:
            print("  ❌ Failed to create conversation")
            return False
        
        # TEST 4: Add Messages
        print("\n[TEST 4] Adding messages...")
        ConversationService.add_message(
            conv_id, 
            "user", 
            "What are my case prospects?",
            language="en"
        )
        
        ConversationService.add_message(
            conv_id,
            "assistant",
            "Based on the case details, acceptance probability is 45%",
            language="en"
        )
        
        updated_conv = ConversationService.get_conversation(conv_id)
        if updated_conv and len(updated_conv.messages) == 2:
            print(f"  ✅ Messages added: {len(updated_conv.messages)} messages")
        else:
            print("  ❌ Failed to add messages")
            return False
        
        # TEST 5: Save Prediction
        print("\n[TEST 5] Saving prediction...")
        pred_metadata = CasePredictionMetadata(
            case_name="John vs State",
            case_type="Criminal",
            year=2025,
            jurisdiction_state="Delhi",
            damages=100000,
            parties_count=2,
            is_appeal=False
        )
        
        pred_result = PredictionResult(
            verdict="Accepted",
            confidence=87.5,
            probabilities={
                "Accepted": 0.875,
                "Rejected": 0.125
            },
            shap_explanation={"feature1": 0.5, "feature2": 0.3},
            similar_cases=[],
            risk_assessment={"risk_level": "low"}
        )
        
        pred_data = CasePredictionCreate(
            user_id=user_id,
            metadata=pred_metadata,
            result=pred_result
        )
        
        prediction = PredictionHistoryService.save_prediction(pred_data)
        
        if prediction:
            print(f"  ✅ Prediction saved: {prediction.metadata.case_name}")
            pred_id = str(prediction.id)
        else:
            print("  ❌ Failed to save prediction")
            return False
        
        # TEST 6: Get User Predictions
        print("\n[TEST 6] Retrieving user predictions...")
        user_preds = PredictionHistoryService.get_user_predictions(user_id)
        if user_preds:
            print(f"  ✅ Found {len(user_preds)} prediction(s)")
        else:
            print("  ❌ No predictions found")
            return False
        
        # TEST 7: Get User Conversations
        print("\n[TEST 7] Retrieving user conversations...")
        user_convs = ConversationService.get_user_conversations(user_id)
        if user_convs:
            print(f"  ✅ Found {len(user_convs)} conversation(s)")
        else:
            print("  ❌ No conversations found")
            return False
        
        # TEST 8: Get User Stats
        print("\n[TEST 8] Getting user statistics...")
        stats = PredictionHistoryService.get_user_stats(user_id)
        print(f"  ✅ Total predictions: {stats['total_predictions']}")
        print(f"     By verdict: {stats['by_verdict']}")
        
        # TEST 9: Search Predictions
        print("\n[TEST 9] Searching predictions...")
        search_results = PredictionHistoryService.search_predictions(user_id, "John")
        if search_results:
            print(f"  ✅ Found {len(search_results)} matching prediction(s)")
        else:
            print("  ❌ No matching predictions found")
        
        # TEST 10: Search Conversations
        print("\n[TEST 10] Searching conversations...")
        search_convs = ConversationService.search_conversations(user_id, "Consultation")
        if search_convs:
            print(f"  ✅ Found {len(search_convs)} matching conversation(s)")
        else:
            print("  ❌ No matching conversations found")
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        
        # Cleanup
        print("\n[CLEANUP] Deleting test data...")
        ConversationService.delete_conversation(conv_id)
        PredictionHistoryService.delete_prediction(pred_id)
        print("  ✅ Test data deleted")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_database_integration()
    sys.exit(0 if success else 1)
```

---

## Part 7: Quick Reference Checklist

Use this to verify each step:

```
MONGODB SETUP CHECKLIST
=======================

☐ Step 1: Verify MongoDB installation
  Command: mongod --version
  
☐ Step 2: Create data directory
  Folder: C:\data\db
  
☐ Step 3: Start MongoDB server
  Command: mongod
  Keep running in background
  
☐ Step 4: Connect to MongoDB shell
  Command: mongosh
  Look for: test>
  
☐ Step 5: Create database
  Command: use smart_legal_db
  
☐ Step 6: Create collections
  Create: users, conversations, case_predictions, feedback, audit_logs
  
☐ Step 7: Create indexes
  Run all index creation commands
  
☐ Step 8: Install Python driver
  Command: pip install pymongo python-dotenv
  
☐ Step 9: Create config files
  Files: config/db_config.py, .env
  
☐ Step 10: Create connection module
  File: src/services/db_connection.py
  
☐ Step 11: Test connection
  Command: python test_db_connection.py
  Expected: ✅ All tests passed!
  
☐ Step 12: Create data models
  File: src/models/db_models.py
  
☐ Step 13: Create services
  Files: src/services/user_service.py
         src/services/conversation_service.py
         src/services/prediction_history_service.py
  
☐ Step 14: Run integration test
  Command: python test_database_integration.py
  Expected: ✅ ALL TESTS PASSED!
  
✅ DATABASE PHASE COMPLETE!
```

---

## Next Steps After Setup

Once you complete all tests, we'll:

1. Create FastAPI endpoints for authentication
2. Integrate with existing /query and /document/analyze endpoints  
3. Update /case-outcome/predict to save results to DB
4. Build frontend pages (Login, Dashboard, History)
5. Deploy to MongoDB Atlas (cloud version)

Let me know when you reach each step and I'll guide you through! 🚀
