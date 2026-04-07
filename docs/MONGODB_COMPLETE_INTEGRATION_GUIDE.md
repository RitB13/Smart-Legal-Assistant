# MongoDB Complete Integration Guide
## Smart Legal Assistant Project

**Last Updated**: March 16, 2026  
**Version**: 1.0.0 (Comprehensive)  
**Status**: Production-Ready

---

## Table of Contents

1. [MongoDB Configuration & Connection](#mongodb-configuration--connection)
2. [Database & Collection Structure](#database--collection-structure)
3. [Data Models & Schemas](#data-models--schemas)
4. [Authentication & Connection Strings](#authentication--connection-strings)
5. [CRUD Operations by Collection](#crud-operations-by-collection)
6. [Indexing Strategies](#indexing-strategies)
7. [Data Validation](#data-validation)
8. [FastAPI/Python Integration](#fastapipython-integration)
9. [User Profiles & Authentication](#user-profiles--authentication)
10. [Case Predictions & Outcomes](#case-predictions--outcomes)
11. [Conversations & Message Storage](#conversations--message-storage)
12. [Feedback & Audit Trails](#feedback--audit-trails)
13. [Error Handling & Connection Management](#error-handling--connection-management)
14. [Production Deployment Considerations](#production-deployment-considerations)

---

## 1. MongoDB Configuration & Connection

### 1.1 Configuration Files

#### **config/db_config.py**
```python
import os
from dotenv import load_dotenv

load_dotenv()

# MongoDB Configuration
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://127.0.0.1:27017/")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "smart_legal_db")

# Database connection settings
DB_CONFIG = {
    "url": MONGODB_URL,
    "db_name": MONGODB_DB_NAME,
    "timeout": 5000,  # serverSelectionTimeoutMS
}
```

### 1.2 Connection URL Formats

**Local Development**
```
mongodb://127.0.0.1:27017/
```

**With Authentication**
```
mongodb://username:password@host:27017/
```

**MongoDB Atlas (Cloud)**
```
mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority
```

**To use in .env file:**
```
MONGODB_URL=mongodb://127.0.0.1:27017/
MONGODB_DB_NAME=smart_legal_db
```

### 1.3 Driver & Dependencies

From **requirements.txt**:
```
pymongo==4.6.0          # MongoDB Python driver
python-dotenv==1.0.0    # Environment variable loading
bcrypt==4.1.1           # Password hashing
```

---

## 2. Database & Collection Structure

### 2.1 Database Information

| Property | Value |
|----------|-------|
| **Database Name** | `smart_legal_db` |
| **Location** | Default: `127.0.0.1:27017` |
| **Collections** | 8 main collections |
| **Total Indexes** | 20+ indexes for optimization |

### 2.2 Collections Overview

```
smart_legal_db/
├── users                    # User accounts and profiles
├── conversations           # Conversation history
├── case_predictions        # ML predictions for cases
├── feedback                # User feedback on predictions
├── audit_logs              # Audit trail of operations
├── sessions                # Session tracking (Phase 4)
├── queries                 # Query records (Phase 4)
└── simulations             # Consequence simulations (Phase 4)
```

### 2.3 Collection Creation (Initialization)

**File**: `init_database.py`

```python
#!/usr/bin/env python3

from src.services.db_connection import db_connection

def init_database():
    """Initialize MongoDB database with collections and indexes"""
    
    db = db_connection.db
    
    # Create collections
    collections = [
        "users",
        "conversations", 
        "case_predictions",
        "feedback",
        "audit_logs"
    ]
    
    for collection_name in collections:
        if collection_name not in db.list_collection_names():
            db.create_collection(collection_name)
            print(f"✅ Created collection: {collection_name}")
    
    # Create indexes (see section 6)
```

**To Initialize:**
```bash
python init_database.py
```

---

## 3. Data Models & Schemas

### 3.1 User Model

**File**: `src/models/db_models.py`

```python
class UserBase(BaseModel):
    """Base user data (shared fields)"""
    email: EmailStr
    name: str
    preferred_language: str = "en"
    jurisdiction: str = "india"

class UserCreate(UserBase):
    """Form for creating user"""
    password: str  # Will be hashed

class UserInDB(UserBase):
    """User as stored in MongoDB"""
    id: str = Field(alias="_id")
    password_hash: str
    is_active: bool = True
    created_at: datetime
    updated_at: datetime
```

**MongoDB Document Structure:**
```json
{
  "_id": ObjectId("507f1f77bcf86cd799439011"),
  "email": "john@example.com",
  "name": "John Doe",
  "preferred_language": "en",
  "jurisdiction": "india",
  "password_hash": "$2b$12$...",
  "is_active": true,
  "created_at": ISODate("2026-03-16T10:30:00Z"),
  "updated_at": ISODate("2026-03-16T10:30:00Z")
}
```

### 3.2 Conversation Model

**File**: `src/models/db_models.py`

```python
class MessageInConversation(BaseModel):
    """Single message in a conversation"""
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime
    language: Optional[str] = None

class ConversationInDB(BaseModel):
    """Conversation as stored in database"""
    id: str = Field(alias="_id")
    user_id: str
    title: str
    language: str = "en"
    messages: List[MessageInConversation] = []
    created_at: datetime
    updated_at: datetime
```

**MongoDB Document Example:**
```json
{
  "_id": ObjectId("507f1f77bcf86cd799439012"),
  "user_id": "507f1f77bcf86cd799439011",
  "title": "Property Dispute Consultation",
  "language": "en",
  "messages": [
    {
      "role": "user",
      "content": "What are my rights in a property dispute?",
      "timestamp": ISODate("2026-03-16T10:40:00Z"),
      "language": "en"
    },
    {
      "role": "assistant",
      "content": "In India, property disputes are governed by...",
      "timestamp": ISODate("2026-03-16T10:41:00Z"),
      "language": "en"
    }
  ],
  "created_at": ISODate("2026-03-16T10:40:00Z"),
  "updated_at": ISODate("2026-03-16T10:41:00Z")
}
```

### 3.3 Case Prediction Model

**File**: `src/models/db_models.py`

```python
class CasePredictionMetadata(BaseModel):
    """Metadata about a case"""
    case_name: str
    case_type: str  # "Criminal", "Civil", "Family", etc.
    year: int
    jurisdiction_state: str
    damages: Optional[float] = None
    parties_count: int = 2
    is_appeal: bool = False

class PredictionResult(BaseModel):
    """ML prediction result"""
    verdict: str  # Accepted, Acquitted, Convicted, etc.
    confidence: float  # 0-100
    probabilities: Dict[str, float]
    shap_explanation: Dict[str, float]
    similar_cases: List[Dict[str, Any]] = []
    risk_assessment: Dict[str, Any] = {}

class CasePredictionInDB(BaseModel):
    """Prediction stored in database"""
    id: str = Field(alias="_id")
    user_id: str
    metadata: CasePredictionMetadata
    result: PredictionResult
    created_at: datetime
```

**MongoDB Document Example:**
```json
{
  "_id": ObjectId("507f1f77bcf86cd799439013"),
  "user_id": "507f1f77bcf86cd799439011",
  "metadata": {
    "case_name": "State v. John Doe",
    "case_type": "Criminal",
    "year": 2023,
    "jurisdiction_state": "Delhi",
    "damages": 500000,
    "parties_count": 2,
    "is_appeal": true
  },
  "result": {
    "verdict": "Accepted",
    "confidence": 87.5,
    "probabilities": {
      "Accepted": 0.875,
      "Convicted": 0.050,
      "Acquitted": 0.050,
      "Rejected": 0.025,
      "Settlement": 0.0,
      "Other": 0.0,
      "Unknown": 0.0
    },
    "shap_explanation": {
      "case_type": 0.15,
      "year": 0.10,
      "jurisdiction": 0.08
    },
    "similar_cases": [
      {
        "case_id": "case_001",
        "similarity_score": 0.92,
        "verdict": "Accepted"
      }
    ]
  },
  "created_at": ISODate("2026-03-16T10:50:00Z")
}
```

### 3.4 Session Model (Phase 4)

**File**: `src/models/database_models.py`

```python
class UserSessionModel(BaseModel):
    """User session for tracking conversation context"""
    session_id: str
    user_id: Optional[str] = None
    language: str = "en"
    start_time: datetime
    last_activity: datetime
    total_queries: int = 0
    modes_used: List[str] = []
    metadata: Dict[str, Any] = {}
    is_active: bool = True
```

### 3.5 Query Record Model (Phase 4)

```python
class QueryRecordModel(BaseModel):
    """Record of a query and its response"""
    query_id: str
    session_id: Optional[str] = None
    query_text: str
    language: str = "en"
    
    # Response
    response_summary: str
    applicable_laws: List[str] = []
    suggestions: List[str] = []
    impact_score: Optional[int] = None
    
    # Mode info
    detected_mode: str  # chat/predict/simulate
    mode_confidence: float
    mode_reasoning: Optional[str] = None
    
    # Metadata
    timestamp: datetime
    processing_time_ms: float
    llm_model: Optional[str] = None
    
    # Feedback
    user_feedback: Optional[int] = None  # 1-5
    user_comment: Optional[str] = None
```

### 3.6 Feedback Model

```python
class UserFeedbackModel(BaseModel):
    """User feedback on system quality"""
    feedback_id: str
    session_id: Optional[str] = None
    
    # What feedback is about
    feedback_type: str  # mode_accuracy/content_quality/helpfulness
    related_query_id: Optional[str] = None
    related_simulation_id: Optional[str] = None
    
    # Feedback
    rating: int  # 1-5 stars
    comment: Optional[str] = None
    
    # Metadata
    timestamp: datetime
    language: str = "en"
```

---

## 4. Authentication & Connection Strings

### 4.1 Singleton Connection Pattern

**File**: `src/services/db_connection.py`

```python
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError, ConnectionFailure
from config.db_config import DB_CONFIG

class DatabaseConnection:
    """Singleton class for MongoDB connection"""
    
    _instance = None
    _client = None
    _db = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseConnection, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._client is None:
            self._connect()
    
    def _connect(self):
        """Establish connection to MongoDB"""
        self._client = MongoClient(
            DB_CONFIG["url"],
            serverSelectionTimeoutMS=DB_CONFIG["timeout"]
        )
        
        # Test connection
        self._client.admin.command('ping')
        
        # Get database
        self._db = self._client[DB_CONFIG["db_name"]]
    
    @property
    def client(self):
        return self._client
    
    @property
    def db(self):
        if self._db is None:
            raise RuntimeError("Database not connected")
        return self._db
    
    def get_collection(self, collection_name: str):
        return self._db[collection_name]
    
    def close(self):
        if self._client:
            self._client.close()

# Singleton instance
db_connection = DatabaseConnection()

# Helper functions
def get_collection(collection_name: str):
    """Get a collection by name"""
    return db_connection.get_collection(collection_name)

def get_db():
    """Get database instance"""
    return db_connection.db
```

### 4.2 Connection Parameters

```
MongoDB Connection String
├── Protocol: mongodb:// or mongodb+srv://
├── Host: localhost:27017 or cluster.mongodb.net
├── Database: smart_legal_db
├── Options:
│   ├── serverSelectionTimeoutMS: 5000
│   ├── connectTimeoutMS: 10000
│   └── retryWrites: true
└── Authentication: username:password (if required)
```

### 4.3 User Authentication (JWT)

**Separate from MongoDB** - JWT tokens are in memory, not stored in MongoDB.

**File**: `src/services/auth_service.py`

```python
from jose import jwt
from datetime import datetime, timedelta
from passlib.context import CryptContext

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Configuration
SECRET_KEY = "your-secret-key-change-this-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 24 * 60  # 24 hours

def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    # Pre-hash with SHA256 if password > 72 bytes (bcrypt limit)
    if len(password.encode('utf-8')) > 72:
        import hashlib
        password = hashlib.sha256(password.encode('utf-8')).hexdigest()
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plaintext password against hash"""
    if len(plain_password.encode('utf-8')) > 72:
        import hashlib
        plain_password = hashlib.sha256(plain_password.encode('utf-8')).hexdigest()
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=24)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
```

---

## 5. CRUD Operations by Collection

### 5.1 Users Collection CRUD

**File**: `src/services/user_service.py`

#### **CREATE: Add User**
```python
def create_user(user_data: UserCreate, password_hash: str) -> Optional[UserInDB]:
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
    
    result = collection.insert_one(user_dict)
    user_dict["_id"] = result.inserted_id
    return UserInDB(**user_dict)
```

#### **READ: Get User by Email**
```python
def get_user_by_email(email: str) -> Optional[UserInDB]:
    """Get user by email"""
    collection = get_collection("users")
    user_dict = collection.find_one({"email": email})
    
    if user_dict:
        return UserInDB(**user_dict)
    return None
```

#### **READ: Get User by ID**
```python
def get_user_by_id(user_id: str) -> Optional[UserInDB]:
    """Get user by MongoDB ObjectId"""
    collection = get_collection("users")
    object_id = ObjectId(user_id)
    user_dict = collection.find_one({"_id": object_id})
    
    if user_dict:
        return UserInDB(**user_dict)
    return None
```

#### **UPDATE: Update User Information**
```python
def update_user(user_id: str, **kwargs) -> Optional[UserInDB]:
    """Update user fields"""
    collection = get_collection("users")
    
    update_dict = {**kwargs, "updated_at": datetime.utcnow()}
    
    result = collection.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": update_dict}
    )
    
    if result.matched_count > 0:
        return get_user_by_id(user_id)
    return None
```

#### **DELETE: Deactivate User (Soft Delete)**
```python
def delete_user(user_id: str) -> bool:
    """Deactivate user (soft delete)"""
    collection = get_collection("users")
    
    result = collection.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {
            "is_active": False,
            "updated_at": datetime.utcnow()
        }}
    )
    
    return result.matched_count > 0
```

#### **CHECK: User Exists**
```python
def user_exists(email: str) -> bool:
    """Check if user with email exists"""
    collection = get_collection("users")
    return collection.find_one({"email": email}) is not None
```

### 5.2 Conversations Collection CRUD

**File**: `src/services/conversation_service.py`

#### **CREATE: Create Conversation**
```python
def create_conversation(conv_data: ConversationCreate) -> Optional[ConversationInDB]:
    """Create new conversation"""
    collection = get_collection("conversations")
    
    conv_dict = {
        "user_id": conv_data.user_id,
        "title": conv_data.title,
        "language": conv_data.language,
        "messages": [],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    
    result = collection.insert_one(conv_dict)
    conv_dict["_id"] = result.inserted_id
    return ConversationInDB(**conv_dict)
```

#### **READ: Get Conversation**
```python
def get_conversation(conv_id: str) -> Optional[ConversationInDB]:
    """Get conversation by ID"""
    collection = get_collection("conversations")
    conv_dict = collection.find_one({"_id": ObjectId(conv_id)})
    
    if conv_dict:
        return ConversationInDB(**conv_dict)
    return None
```

#### **READ: Get All User Conversations**
```python
def get_user_conversations(user_id: str, limit: int = 50) -> List[ConversationInDB]:
    """Get all conversations for a user (newest first)"""
    collection = get_collection("conversations")
    
    conversations = list(collection.find(
        {"user_id": user_id}
    ).sort("created_at", DESCENDING).limit(limit))
    
    return [ConversationInDB(**conv) for conv in conversations]
```

#### **UPDATE: Add Message to Conversation**
```python
def add_message(conv_id: str, role: str, content: str, language: Optional[str] = None) -> Optional[ConversationInDB]:
    """Add message to conversation"""
    collection = get_collection("conversations")
    
    message = {
        "role": role,
        "content": content,
        "timestamp": datetime.utcnow(),
        "language": language
    }
    
    collection.update_one(
        {"_id": ObjectId(conv_id)},
        {
            "$push": {"messages": message},
            "$set": {"updated_at": datetime.utcnow()}
        }
    )
    
    return get_conversation(conv_id)
```

#### **DELETE: Delete Conversation**
```python
def delete_conversation(conv_id: str) -> bool:
    """Delete conversation"""
    collection = get_collection("conversations")
    result = collection.delete_one({"_id": ObjectId(conv_id)})
    return result.deleted_count > 0
```

### 5.3 Case Predictions Collection CRUD

**File**: `src/services/prediction_history_service.py`

#### **CREATE: Save Prediction**
```python
def save_prediction(pred_data: CasePredictionCreate) -> Optional[CasePredictionInDB]:
    """Save case prediction"""
    collection = get_collection("case_predictions")
    
    pred_dict = {
        "user_id": pred_data.user_id,
        "metadata": pred_data.metadata.dict(),
        "result": pred_data.result.dict(),
        "created_at": datetime.utcnow(),
    }
    
    result = collection.insert_one(pred_dict)
    pred_dict["_id"] = result.inserted_id
    return CasePredictionInDB(**pred_dict)
```

#### **READ: Get Prediction by ID**
```python
def get_prediction(pred_id: str) -> Optional[CasePredictionInDB]:
    """Get prediction by ID"""
    collection = get_collection("case_predictions")
    pred_dict = collection.find_one({"_id": ObjectId(pred_id)})
    
    if pred_dict:
        return CasePredictionInDB(**pred_dict)
    return None
```

#### **READ: Get User Predictions**
```python
def get_user_predictions(user_id: str, limit: int = 50) -> List[CasePredictionInDB]:
    """Get all predictions for user"""
    collection = get_collection("case_predictions")
    
    predictions = list(collection.find(
        {"user_id": user_id}
    ).sort("created_at", DESCENDING).limit(limit))
    
    return [CasePredictionInDB(**pred) for pred in predictions]
```

#### **SEARCH: Search Predictions**
```python
def search_predictions(user_id: str, filters: dict) -> List[CasePredictionInDB]:
    """Search predictions with filters"""
    collection = get_collection("case_predictions")
    
    query = {"user_id": user_id}
    
    # Add filters
    if filters.get("case_type"):
        query["metadata.case_type"] = filters["case_type"]
    if filters.get("jurisdiction"):
        query["metadata.jurisdiction_state"] = filters["jurisdiction"]
    if filters.get("year"):
        query["metadata.year"] = filters["year"]
    
    predictions = list(collection.find(query).sort("created_at", DESCENDING))
    return [CasePredictionInDB(**pred) for pred in predictions]
```

#### **DELETE: Delete Prediction**
```python
def delete_prediction(pred_id: str) -> bool:
    """Delete prediction"""
    collection = get_collection("case_predictions")
    result = collection.delete_one({"_id": ObjectId(pred_id)})
    return result.deleted_count > 0
```

### 5.4 Feedback Collection CRUD

```python
class FeedbackService:
    """Service for managing feedback"""
    
    @staticmethod
    def save_feedback(feedback_data: UserFeedbackModel) -> bool:
        """Save user feedback"""
        collection = get_collection("feedback")
        collection.insert_one(feedback_data.dict())
        return True
    
    @staticmethod
    def get_feedback_for_prediction(pred_id: str) -> List[UserFeedbackModel]:
        """Get all feedback for a prediction"""
        collection = get_collection("feedback")
        results = collection.find({"related_query_id": pred_id})
        return [UserFeedbackModel(**doc) for doc in results]
    
    @staticmethod
    def get_user_feedback(user_id: str) -> List[UserFeedbackModel]:
        """Get all feedback from a user"""
        collection = get_collection("feedback")
        results = collection.find({"user_id": user_id})
        return [UserFeedbackModel(**doc) for doc in results]
```

### 5.5 Sessions Collection CRUD (Phase 4)

**File**: `src/services/database_service.py`

```python
def save_session(self, session: UserSessionModel) -> bool:
    """Save user session"""
    self._collections['sessions'].replace_one(
        {'session_id': session.session_id},
        session.dict(),
        upsert=True
    )
    return True

def get_session(self, session_id: str) -> Optional[UserSessionModel]:
    """Retrieve session"""
    result = self._collections['sessions'].find_one({'session_id': session_id})
    if result:
        result.pop('_id', None)
        return UserSessionModel(**result)
    return None

def update_session_activity(self, session_id: str) -> bool:
    """Update last activity timestamp"""
    self._collections['sessions'].update_one(
        {'session_id': session_id},
        {'$set': {'last_activity': datetime.utcnow()}}
    )
    return True
```

### 5.6 Queries Collection CRUD (Phase 4)

```python
def save_query_record(self, query_record: QueryRecordModel) -> bool:
    """Save query record"""
    self._collections['queries'].insert_one(query_record.dict())
    return True

def get_query_record(self, query_id: str) -> Optional[QueryRecordModel]:
    """Get query record"""
    result = self._collections['queries'].find_one({'query_id': query_id})
    if result:
        result.pop('_id', None)
        return QueryRecordModel(**result)
    return None

def get_session_queries(self, session_id: str) -> List[QueryRecordModel]:
    """Get all queries in session"""
    results = self._collections['queries'].find(
        {'session_id': session_id}
    ).sort('timestamp', -1)
    
    return [QueryRecordModel(**doc) for doc in results]

def save_query_feedback(self, query_id: str, rating: int, comment: Optional[str] = None) -> bool:
    """Save feedback on query"""
    self._collections['queries'].update_one(
        {'query_id': query_id},
        {'$set': {
            'user_feedback': rating,
            'user_comment': comment
        }}
    )
    return True
```

---

## 6. Indexing Strategies

### 6.1 Index Creation

**File**: `init_database.py`

```python
# Users indexes
users = db["users"]
users.create_index("email", unique=True)      # Email must be unique
users.create_index("created_at")              # Query by creation date

# Conversations indexes
conversations = db["conversations"]
conversations.create_index("user_id")         # Query by user
conversations.create_index([("created_at", -1)])  # Newest first

# Case predictions indexes
predictions = db["case_predictions"]
predictions.create_index("user_id")           # Query by user
predictions.create_index([("created_at", -1)])   # Newest first
predictions.create_index("metadata.case_type")   # Query by case type
predictions.create_index("metadata.jurisdiction_state")  # By jurisdiction

# Feedback indexes
feedback = db["feedback"]
feedback.create_index("prediction_id")        # Related prediction
feedback.create_index("user_id")              # By user
feedback.create_index([("timestamp", -1)])    # By time

# Sessions indexes
sessions = db["sessions"]
sessions.create_index("session_id", unique=True)  # Unique session
sessions.create_index("user_id")              # Query by user
sessions.create_index("start_time")           # Query by time

# Queries indexes
queries = db["queries"]
queries.create_index("query_id", unique=True)     # Unique query
queries.create_index("session_id")            # Query by session
queries.create_index("timestamp")             # Query by time
queries.create_index("detected_mode")         # Query by mode

# Simulations indexes
simulations = db["simulations"]
simulations.create_index("simulation_id", unique=True)
simulations.create_index("session_id")
simulations.create_index("timestamp")
simulations.create_index("risk_level")        # Query by risk
```

### 6.2 Index Performance Impact

| Index | Collection | Query Performance | Storage Cost | Usage |
|-------|-----------|------------------|--------------|-------|
| `email` (unique) | users | +++++ | Low | User lookup, auth |
| `user_id` | conversations | +++ | Low | User's conversations |
| `created_at` (desc) | conversations | ++ | Low | Sort newest first |
| `metadata.case_type` | case_predictions | +++ | Low | Filter by case type |
| `session_id` (unique) | sessions | +++++ | Low | Session lookup |
| `query_id` (unique) | queries | +++++ | Low | Query lookup |
| `timestamp` | queries | ++ | Low | Time-based queries |
| `detected_mode` | queries | ++ | Low | Mode analysis |

### 6.3 Index Verification

```python
# List all indexes on a collection
db.users.list_indexes()

# Drop an index
db.users.drop_index("email_1")

# Rebuild indexes
db.users.reindex()
```

---

## 7. Data Validation

### 7.1 Pydantic Model Validation

**File**: `src/models/db_models.py`

```python
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional

class UserCreate(BaseModel):
    email: EmailStr  # Validates email format
    password: str = Field(..., min_length=8)  # Min 8 characters
    name: str = Field(..., min_length=2)  # Min 2 characters
    preferred_language: str = "en"
    jurisdiction: str = "india"

class CasePredictionMetadata(BaseModel):
    case_name: str
    case_type: str
    year: int = Field(..., ge=1950, le=2100)  # Year range
    damages: Optional[float] = Field(None, ge=0)  # Non-negative
    parties_count: int = Field(..., ge=1)  # At least 1 party

# Custom validation
class QueryRecordModel(BaseModel):
    mode_confidence: float = Field(..., ge=0.0, le=1.0)  # 0-1 range
    impact_score: Optional[int] = Field(None, ge=0, le=100)  # 0-100
    user_feedback: Optional[int] = Field(None, ge=1, le=5)  # 1-5 stars
    
    @field_validator('mode_confidence')
    def validate_confidence(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError('Confidence must be between 0 and 1')
        return v
```

### 7.2 MongoDB Field Validation

```javascript
// MongoDB can enforce schema validation (optional)
db.createCollection("users", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["email", "name", "password_hash"],
      properties: {
        _id: { bsonType: "objectId" },
        email: { bsonType: "string", pattern: "^([a-zA-Z0-9_.-])+@([a-zA-Z0-9_.-])+\\.([a-zA-Z])+([a-zA-Z])*$" },
        name: { bsonType: "string", minLength: 2 },
        password_hash: { bsonType: "string" },
        is_active: { bsonType: "bool" },
        created_at: { bsonType: "date" },
        updated_at: { bsonType: "date" }
      }
    }
  }
})
```

### 7.3 Data Type Constraints

```python
# In models.py - these are enforced by Pydantic before MongoDB insertion

Constraints by Field Type:
├── EmailStr
│   └── Validates RFC 5321 email format
├── str (min_length, max_length)
│   └── String length validation
├── int (ge, le)
│   └── Integer range validation
├── float (ge, le)
│   └── Float range validation
├── datetime
│   └── ISO 8601 format validation
├── List
│   └── List type and item validation
└── Optional
    └── Allow None or specified type
```

---

## 8. FastAPI/Python Integration

### 8.1 Router Integration

**File**: `app.py`

```python
from fastapi import FastAPI
from src.routes import auth_routes, conversation_routes, prediction_routes, case_outcome

app = FastAPI(
    title="Smart Legal Assistant API",
    version="1.0.0"
)

# Include routers
app.include_router(auth_routes.router)              # /auth
app.include_router(conversation_routes.router)      # /conversations
app.include_router(prediction_routes.router)         # /predictions
app.include_router(case_outcome.router)             # /case-outcome

@app.on_event("startup")
async def startup_event():
    """Initialize on app startup"""
    # PHASE 9: Load models at startup
    from src.services.model_manager import get_model_manager
    model_manager = get_model_manager()
    model_manager.load_model_at_startup()
```

### 8.2 Endpoint -> MongoDB Flow

```python
# Example: Register User Endpoint
# File: src/routes/auth_routes.py

from fastapi import APIRouter, HTTPException
from src.services.user_service import UserService
from src.services.auth_service import hash_password, create_access_token

router = APIRouter(prefix="/auth")

@router.post("/register")
def register(user_data: RegisterRequest):
    """Register new user"""
    try:
        # Check if user exists
        if UserService.user_exists(user_data.email):
            raise HTTPException(status_code=400, detail="User already exists")
        
        # Hash password
        password_hash = hash_password(user_data.password)
        
        # Save to MongoDB
        user = UserService.create_user(
            UserCreate(
                email=user_data.email,
                name=user_data.name,
                preferred_language=user_data.preferred_language,
                jurisdiction=user_data.jurisdiction
            ),
            password_hash=password_hash
        )
        
        if not user:
            raise HTTPException(status_code=500, detail="Failed to create user")
        
        # Generate JWT token
        token = create_access_token({"user_id": str(user.id), "email": user.email})
        
        return LoginResponse(
            user_id=user.id,
            email=user.email,
            name=user.name,
            access_token=token,
            expires_in=86400
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### 8.3 Dependency Injection

```python
# Database dependency
from src.services.db_connection import get_db, get_collection

async def get_current_user(authorization: Optional[str] = Header(None)) -> TokenData:
    """Dependency to extract current user from JWT"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing token")
    
    token = authorization.replace("Bearer ", "")
    token_data = verify_token(token)
    
    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return token_data

# Use in routes
@router.get("/conversations")
def get_conversations(current_user: TokenData = Depends(get_current_user)):
    """Get current user's conversations"""
    conversations = ConversationService.get_user_conversations(current_user.user_id)
    return conversations
```

### 8.4 Error Handling

```python
from pymongo.errors import DuplicateKeyError, ServerSelectionTimeoutError

try:
    # MongoDB operation
    result = collection.insert_one(document)
except DuplicateKeyError:
    raise HTTPException(status_code=400, detail="Duplicate entry")
except ServerSelectionTimeoutError:
    raise HTTPException(status_code=503, detail="Database connection failed")
except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))
```

---

## 9. User Profiles & Authentication

### 9.1 User Registration Flow

```
User Registration Request
    ↓
1. Validate email format + password strength
2. Check if email already exists (MongoDB query)
3. Hash password using bcrypt
4. Create user document in MongoDB
5. Generate JWT token
6. Return user + token to client
```

**Implementation:**
```python
@router.post("/auth/register")
async def register(request: RegisterRequest):
    """
    Step 1: Validate request
    """
    if not 8 <= len(request.password) <= 100:
        raise HTTPException(status_code=400, detail="Invalid password")
    
    """
    Step 2: Check existence (MongoDB)
    """
    if UserService.user_exists(request.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    
    """
    Step 3: Hash password
    """
    password_hash = hash_password(request.password)
    
    """
    Step 4: Save to MongoDB
    """
    user = UserService.create_user(
        UserCreate(...),
        password_hash
    )
    
    if not user:
        raise HTTPException(status_code=500, detail="Registration failed")
    
    """
    Step 5: Create JWT token
    """
    token = create_access_token({
        "user_id": str(user.id),
        "email": user.email
    })
    
    """
    Step 6: Return response
    """
    return LoginResponse(
        user_id=user.id,
        email=user.email,
        access_token=token
    )
```

### 9.2 User Login Flow

```
Login Request
    ↓
1. Find user by email (MongoDB query)
2. Verify password against hash
3. Generate new JWT token
4. Return token to client
```

**Implementation:**
```python
@router.post("/auth/login")
async def login(credentials: LoginRequest):
    # Query MongoDB for user
    user = UserService.get_user_by_email(credentials.email)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Verify password
    if not verify_password(credentials.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Generate token
    token = create_access_token({
        "user_id": str(user.id),
        "email": user.email
    })
    
    return LoginResponse(
        user_id=user.id,
        email=user.email,
        access_token=token,
        expires_in=86400
    )
```

### 9.3 User Profile Operations

```python
# Get current user
@router.get("/auth/me")
async def get_profile(current_user: TokenData = Depends(get_current_user)):
    user = UserService.get_user_by_id(current_user.user_id)
    return User(**user.dict())

# Update profile
@router.put("/auth/me")
async def update_profile(
    updates: UserUpdate,
    current_user: TokenData = Depends(get_current_user)
):
    user = UserService.update_user(
        current_user.user_id,
        preferred_language=updates.preferred_language,
        jurisdiction=updates.jurisdiction
    )
    return User(**user.dict())

# Change password
@router.post("/auth/change-password")
async def change_password(
    password_change: PasswordChangeRequest,
    current_user: TokenData = Depends(get_current_user)
):
    user = UserService.get_user_by_id(current_user.user_id)
    
    # Verify old password
    if not verify_password(password_change.old_password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid current password")
    
    # Hash new password
    new_hash = hash_password(password_change.new_password)
    
    # Update in MongoDB
    UserService.update_user(current_user.user_id, password_hash=new_hash)
    
    return {"message": "Password changed successfully"}
```

---

## 10. Case Predictions & Outcomes

### 10.1 Prediction Save Flow

```python
# File: src/routes/case_outcome.py

@router.post("/case-outcome/predict")
async def predict_case_outcome(
    case_input: CaseInputModel,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Predict case outcome and save to MongoDB
    """
    try:
        # 1. Run ML model
        predictor = get_predictor_service()
        prediction = predictor.predict(case_input)
        
        # 2. Generate prediction ID
        prediction_id = str(uuid.uuid4())
        
        # 3. Prepare metadata
        metadata = CasePredictionMetadata(
            case_name=case_input.case_name,
            case_type=case_input.case_type,
            year=case_input.year,
            jurisdiction_state=case_input.jurisdiction_state,
            damages_awarded=case_input.damages_awarded,
            parties_count=case_input.parties_count,
            is_appeal=case_input.is_appeal
        )
        
        # 4. Prepare result
        result = PredictionResult(
            verdict=prediction.verdict,
            confidence=prediction.confidence,
            probabilities=prediction.probabilities,
            shap_explanation=prediction.shap_explanation,
            similar_cases=prediction.similar_cases
        )
        
        # 5. Save to MongoDB
        pred_to_save = CasePredictionCreate(
            user_id=current_user.user_id,
            metadata=metadata,
            result=result
        )
        
        saved_pred = PredictionHistoryService.save_prediction(pred_to_save)
        
        # 6. Log to audit trail
        audit_service = AuditTrailService()
        audit_service.log_prediction(
            prediction_id=prediction_id,
            user_id=current_user.user_id,
            case_type=case_input.case_type,
            verdict=prediction.verdict,
            confidence=prediction.confidence
        )
        
        # 7. Return response
        return CaseOutcomePredictionResponse(
            prediction_id=prediction_id,
            case_summary=metadata.dict(),
            verdict=prediction.verdict,
            probability=prediction.confidence,
            confidence=PredictionConfidence(
                level="high" if prediction.confidence > 0.7 else "medium",
                score=prediction.confidence,
                interpretation="Model is confident" if prediction.confidence > 0.7 else "Moderate confidence"
            ),
            verdict_probabilities=prediction.probabilities,
            explanation=prediction.shap_explanation,
            similar_cases=prediction.similar_cases,
            timestamp=datetime.utcnow()
        )
    
    except Exception as e:
        logger.error(f"Prediction failed: {e}")
        raise HTTPException(status_code=500, detail="Prediction failed")
```

### 10.2 Prediction Retrieval

```python
@router.get("/predictions/{prediction_id}")
async def get_prediction(
    prediction_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """Get stored prediction"""
    
    # Retrieve from MongoDB
    prediction = PredictionHistoryService.get_prediction(prediction_id)
    
    if not prediction:
        raise HTTPException(status_code=404, detail="Prediction not found")
    
    # Verify ownership
    if prediction.user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    return CasePrediction(**prediction.dict())
```

### 10.3 Prediction History

```python
@router.get("/predictions")
async def list_user_predictions(
    current_user: TokenData = Depends(get_current_user),
    limit: int = Query(50, le=100),
    case_type: Optional[str] = None,
    jurisdiction: Optional[str] = None
):
    """Get user's predictions with optional filters"""
    
    filters = {}
    if case_type:
        filters["case_type"] = case_type
    if jurisdiction:
        filters["jurisdiction"] = jurisdiction
    
    predictions = PredictionHistoryService.search_predictions(
        current_user.user_id,
        filters
    )
    
    return [CasePrediction(**p.dict()) for p in predictions[:limit]]
```

---

## 11. Conversations & Message Storage

### 11.1 Conversation Creation

```python
@router.post("/conversations")
async def create_conversation(
    conv_req: ConversationCreate,
    current_user: TokenData = Depends(get_current_user)
):
    """Create new conversation"""
    
    conv_data = ConversationCreate(
        user_id=current_user.user_id,
        title=conv_req.title or f"Conversation {datetime.now().strftime('%Y-%m-%d')}",
        language=conv_req.language
    )
    
    # Save to MongoDB
    conversation = ConversationService.create_conversation(conv_data)
    
    if not conversation:
        raise HTTPException(status_code=500, detail="Failed to create conversation")
    
    return ConversationResponse(
        id=str(conversation.id),
        user_id=conversation.user_id,
        title=conversation.title,
        messages=[],
        created_at=conversation.created_at,
        updated_at=conversation.updated_at
    )
```

### 11.2 Add Message to Conversation

```python
@router.post("/conversations/{conversation_id}/message")
async def add_message(
    conversation_id: str,
    message_req: MessageCreate,
    current_user: TokenData = Depends(get_current_user)
):
    """Add message to conversation"""
    
    # Verify ownership
    conversation = ConversationService.get_conversation(conversation_id)
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    if conversation.user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Add message (MongoDB $push)
    updated_conv = ConversationService.add_message(
        conversation_id,
        role=message_req.role,
        content=message_req.content,
        language=message_req.language
    )
    
    if not updated_conv:
        raise HTTPException(status_code=500, detail="Failed to add message")
    
    return ConversationResponse(
        id=str(updated_conv.id),
        user_id=updated_conv.user_id,
        title=updated_conv.title,
        messages=[MessageResponse(**m.dict()) for m in updated_conv.messages],
        created_at=updated_conv.created_at,
        updated_at=updated_conv.updated_at,
        message_count=len(updated_conv.messages)
    )
```

### 11.3 Retrieve Conversations

```python
@router.get("/conversations")
async def list_conversations(
    current_user: TokenData = Depends(get_current_user),
    limit: int = Query(50, le=100)
):
    """Get user's conversations"""
    
    conversations = ConversationService.get_user_conversations(
        current_user.user_id,
        limit=limit
    )
    
    return [
        ConversationResponse(
            id=str(conv.id),
            user_id=conv.user_id,
            title=conv.title,
            messages=[MessageResponse(**m.dict()) for m in conv.messages],
            created_at=conv.created_at,
            updated_at=conv.updated_at,
            message_count=len(conv.messages)
        )
        for conv in conversations
    ]
```

### 11.4 Message Storage Structure

**In MongoDB:**
```json
{
  "_id": ObjectId("..."),
  "user_id": "507f1f77bcf86cd799439011",
  "title": "Property Dispute Discussion",
  "language": "en",
  "messages": [
    {
      "role": "user",
      "content": "What are property dispute laws in Delhi?",
      "timestamp": ISODate("2026-03-16T10:40:00Z"),
      "language": "en"
    },
    {
      "role": "assistant",
      "content": "In Delhi, property disputes are governed by...",
      "timestamp": ISODate("2026-03-16T10:41:00Z"),
      "language": "en"
    }
  ],
  "created_at": ISODate("2026-03-16T10:40:00Z"),
  "updated_at": ISODate("2026-03-16T10:41:00Z")
}
```

---

## 12. Feedback & Audit Trails

### 12.1 Feedback Storage

```python
@router.post("/case-outcome/feedback/{prediction_id}")
async def submit_feedback(
    prediction_id: str,
    feedback_req: FeedbackCreate,
    current_user: TokenData = Depends(get_current_user)
):
    """Log user feedback on prediction"""
    
    feedback = UserFeedbackModel(
        feedback_id=str(uuid.uuid4()),
        session_id=None,
        feedback_type=feedback_req.feedback_type,
        related_query_id=prediction_id,
        rating=feedback_req.rating,
        comment=feedback_req.comment,
        timestamp=datetime.utcnow(),
        language=current_user.language
    )
    
    # Save to MongoDB
    collection = get_collection("feedback")
    collection.insert_one(feedback.dict())
    
    # Update prediction model version tracking
    monitoring_service = get_prediction_monitor()
    monitoring_service.log_user_feedback(
        prediction_id=prediction_id,
        rating=feedback_req.rating,
        is_correct=feedback_req.is_correct
    )
    
    return {"status": "success", "feedback_id": feedback.feedback_id}
```

### 12.2 Audit Trail Service

**File**: `src/services/audit_trail_service.py`

```python
class AuditTrailService:
    """Maintains complete audit log of all decisions"""
    
    def start_audit_trail(self, request_id: str, query: str, client_ip: Optional[str] = None):
        """Start new audit trail"""
        self.trails[request_id] = []
        
        self.log_event(
            request_id=request_id,
            event_type="request_received",
            description="New legal query received",
            details={
                "query_length": len(query),
                "client_ip": client_ip
            }
        )
    
    def log_event(
        self,
        request_id: str,
        event_type: str,
        description: str,
        details: Optional[Dict[str, Any]] = None,
        input_data: Optional[Dict[str, Any]] = None,
        output_data: Optional[Dict[str, Any]] = None,
        duration_ms: float = 0,
        component: str = "system",
        status: str = "success"
    ):
        """Log single event in audit trail"""
        
        event = AuditEvent(
            timestamp=datetime.utcnow().isoformat(),
            event_type=event_type,
            description=description,
            details=details or {},
            input_data=input_data or {},
            output_data=output_data or {},
            duration_ms=duration_ms,
            component=component,
            status=status
        )
        
        self.trails[request_id].append(event)
    
    def log_prediction(
        self,
        prediction_id: str,
        user_id: str,
        case_type: str,
        verdict: str,
        confidence: float,
        model_version: Optional[str] = None,
        similar_cases: Optional[List[Dict]] = None
    ):
        """Log prediction with details"""
        
        event = {
            "prediction_id": prediction_id,
            "user_id": user_id,
            "timestamp": datetime.utcnow(),
            "case_type": case_type,
            "verdict": verdict,
            "confidence": confidence,
            "model_version": model_version,
            "similar_cases": similar_cases or []
        }
        
        # Store in audit_logs collection
        collection = get_collection("audit_logs")
        collection.insert_one(event)
```

### 12.3 Audit Retrieval

```python
@router.get("/audit/trail/{request_id}")
async def get_audit_trail(request_id: str, current_user: TokenData = Depends(get_current_user)):
    """Get complete audit trail for request"""
    
    collection = get_collection("audit_logs")
    trail_docs = list(collection.find({"request_id": request_id}))
    
    return {
        "request_id": request_id,
        "events": trail_docs
    }

@router.get("/audit/user/{user_id}")
async def get_user_audit(user_id: str, current_user: TokenData = Depends(get_current_user)):
    """Get all audit logs for user"""
    
    # Verify permission (user can only see own audit)
    if user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    collection = get_collection("audit_logs")
    logs = list(collection.find({"user_id": user_id}).sort("timestamp", -1).limit(100))
    
    return {
        "user_id": user_id,
        "total": len(logs),
        "logs": logs
    }
```

---

## 13. Error Handling & Connection Management

### 13.1 Connection Error Handling

```python
from pymongo.errors import (
    ServerSelectionTimeoutError,
    ConnectionFailure,
    OperationFailure,
    DuplicateKeyError
)

class DatabaseConnection:
    def _connect(self):
        """Establish connection with error handling"""
        try:
            self._client = MongoClient(
                DB_CONFIG["url"],
                serverSelectionTimeoutMS=DB_CONFIG["timeout"]
            )
            
            # Test connection
            self._client.admin.command('ping')
            
            self._db = self._client[DB_CONFIG["db_name"]]
            logger.info("✅ Connected to MongoDB successfully")
            
        except ServerSelectionTimeoutError as e:
            logger.error("❌ Could not connect to MongoDB server!")
            logger.error("   Make sure MongoDB is running (mongod)")
            raise
        
        except ConnectionFailure as e:
            logger.error(f"❌ Connection failure: {e}")
            raise
        
        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}")
            raise
```

### 13.2 CRUD Error Handling

```python
def create_user(user_data: UserCreate, password_hash: str) -> Optional[UserInDB]:
    """Create user with error handling"""
    collection = get_collection("users")
    
    user_dict = {...}
    
    try:
        result = collection.insert_one(user_dict)
        user_dict["_id"] = result.inserted_id
        logger.info(f"✅ Created user: {user_data.email}")
        return UserInDB(**user_dict)
    
    except DuplicateKeyError:
        logger.error(f"❌ User already exists: {user_data.email}")
        return None
    
    except Exception as e:
        logger.error(f"❌ Error creating user: {e}")
        return None
```

### 13.3 Retry Logic

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
def get_user_with_retry(email: str) -> Optional[UserInDB]:
    """Get user with automatic retry"""
    collection = get_collection("users")
    user_dict = collection.find_one({"email": email})
    
    if user_dict:
        return UserInDB(**user_dict)
    return None
```

### 13.4 Connection Lifecycle

```python
# Startup
@app.on_event("startup")
async def startup():
    """Initialize database connection"""
    db_connection = DatabaseConnection()
    logger.info("✅ Database initialized")

# Shutdown
@app.on_event("shutdown")
async def shutdown():
    """Close database connection"""
    db_connection = DatabaseConnection()
    db_connection.close()
    logger.info("✅ Database connection closed")
```

---

## 14. Production Deployment Considerations

### 14.1 MongoDB Atlas Setup

#### **Step 1: Create Cluster**
```
1. Go to mongodb.com/cloud/atlas
2. Create account / sign in
3. Create new cluster (free tier available)
4. Save connection string
```

#### **Step 2: Update Configuration**
```python
# .env file
MONGODB_URL=mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority
MONGODB_DB_NAME=smart_legal_db
```

#### **Step 3: Set Up Authentication**
- In Atlas: Create database user
- Set IP whitelist (or allow all 0.0.0.0/0 for development)
- Use strong passwords

### 14.2 Connection Pooling

```python
# Automatic with PyMongo 4.0+
client = MongoClient(
    DB_CONFIG["url"],
    serverSelectionTimeoutMS=DB_CONFIG["timeout"],
    maxPoolSize=50,  # Max connections
    minPoolSize=10   # Min connections
)
```

### 14.3 SSL/TLS Configuration

```python
# For MongoDB Atlas (MongoDB 4.0+)
MONGODB_URL = "mongodb+srv://user:password@cluster.mongodb.net/?retryWrites=true&w=majority&ssl=true"

# For self-hosted with SSL
MONGODB_URL = "mongodb://user:password@host:27017/?ssl=true&sslCertificateKeyFile=/path/to/cert.pem"
```

### 14.4 Data Backup

```bash
# Backup all collections
mongodump --uri="mongodb://localhost:27017/smart_legal_db" --out ./backup

# Restore from backup
mongorestore --uri="mongodb://localhost:27017" ./backup
```

### 14.5 Performance Monitoring

```python
# Monitor slow queries
db.set_profiling_level(1)  # Log slow operations > 100ms

# View profiling data
db.system.profile.find().sort({"ts": -1}).pretty()
```

### 14.6 Replication & High Availability

```
Production Deployment:
├── Replica Set (3+ nodes)
│   ├── Primary node (reads/writes)
│   ├── Secondary node 1 (reads only, backup)
│   └── Secondary node 2 (reads only, backup)
├── Automated failover
├── Data redundancy
└── Read scaling (distribute reads to secondaries)
```

### 14.7 Database Security Checklist

- [ ] Change default port from 27017
- [ ] Enable authentication (username/password)
- [ ] Use strong passwords (min 16 chars, mixed case, numbers, symbols)
- [ ] Set IP whitelist (don't use 0.0.0.0/0 in production)
- [ ] Enable TLS/SSL encryption in transit
- [ ] Enable encryption at rest (MongoDB Enterprise or Atlas)
- [ ] Regular backups (daily minimum)
- [ ] Monitor audit logs
- [ ] Use role-based access control
- [ ] Rotate credentials periodically

### 14.8 Scaling Strategy

```
As data grows:

Current (March 2026):
├── Single MongoDB instance
├── All collections in one database
└── Suitable for < 1M documents

Growth Phase:
├── Replica set (3+ nodes)
├── Atlas auto-scaling enabled
└── Suitable for 1M - 100M documents

Large Scale:
├── Sharded cluster
├── Data partitioned by user_id
├── Separate read replicas
└── Suitable for > 100M documents
```

---

## Summary Table: Collections at a Glance

| Collection | Purpose | Key Fields | Typical Docs/Year | Indexes |
|-----------|---------|-----------|------------------|---------|
| **users** | User accounts | `email`, `hash`, `timezone` | 1K-10K | email (unique), created_at |
| **conversations** | Chat history | `user_id`, `messages[]` | 10K-100K | user_id, created_at |
| **case_predictions** | Predictions | `user_id`, `metadata`, `result` | 10K-100K | user_id, case_type, created_at |
| **feedback** | User ratings | `prediction_id`, `rating` | 5K-50K | prediction_id, user_id |
| **audit_logs** | Audit trail | `user_id`, `event_type` | 100K-1M | user_id, timestamp, action |
| **sessions** | Session tracking | `session_id`, `user_id` | 10K-100K | session_id, user_id, start_time |
| **queries** | Query records | `query_id`, `session_id` | 100K-1M | query_id, session_id, timestamp |
| **simulations** | Consequence sims | `simulation_id`, `risk_level` | 10K-100K | simulation_id, session_id, risk_level |

---

## Quick Reference: Common Queries

### Get User's Recent Conversations
```python
collection = get_collection("conversations")
convs = collection.find({"user_id": user_id}).sort("created_at", -1).limit(10)
```

### Get All Predictions for Case Type
```python
collection = get_collection("case_predictions")
preds = collection.find({"metadata.case_type": "Criminal"})
```

### Get User's Average Prediction Confidence
```python
collection = get_collection("case_predictions")
pipeline = [
    {"$match": {"user_id": user_id}},
    {"$group": {"_id": None, "avg_confidence": {"$avg": "$result.confidence"}}}
]
avg = collection.aggregate(pipeline)
```

### Get Feedback Statistics
```python
collection = get_collection("feedback")
pipeline = [
    {"$group": {
        "_id": "$feedback_type",
        "count": {"$sum": 1},
        "avg_rating": {"$avg": "$rating"}
    }}
]
stats = collection.aggregate(pipeline)
```

### Find Similar Cases
```python
collection = get_collection("case_predictions")
similar = collection.find({
    "metadata.case_type": case_type,
    "metadata.jurisdiction_state": jurisdiction,
    "result.verdict": verdict
}).limit(5)
```

---

## Troubleshooting

### Connection Issues
```
Error: ServerSelectionTimeoutError
- Ensure MongoDB server is running: mongod
- Check connection string
- Verify firewall allows port 27017
- Test with: python -c "from pymongo import MongoClient; MongoClient().list_database_names()"
```

### Slow Queries
```
Solution 1: Add indexes
db.conversations.create_index("user_id")

Solution 2: Use explain() to analyze
db.case_predictions.find({...}).explain()
Lookfor "executionStages.executionStageType": "COLLSCAN" (bad - means full scan)

Solution 3: Optimize query
Instead of: find({"name": "John", "email": "john@...})
Use index: create_index([("email", 1)])
```

### Duplicate Key Errors
```
Fix: Drop and recreate index
db.users.drop_index("email_1")
db.users.create_index("email", unique=True)

Or manually check for duplicates:
db.users.aggregate([{$group: {_id: "$email", count: {$sum: 1}}}])
```

### Connection Pool Exhausted
```
Solution: Increase pool size
client = MongoClient(..., maxPoolSize=100)
```

---

End of Document  
**Created**: March 16, 2026  
**For**: Smart Legal Assistant Project
