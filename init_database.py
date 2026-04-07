#!/usr/bin/env python3
"""
MongoDB Database Initialization Script

This script:
1. Creates the database (smart_legal_db)
2. Creates 5 collections (users, conversations, case_predictions, feedback, audit_logs)
3. Creates indexes for faster queries
4. Verifies everything was created successfully

Run this ONCE at the beginning to set up your database structure.
"""

import sys
sys.path.insert(0, 'src')

from src.services.db_connection import get_db_connection

def init_database():
    """Initialize MongoDB database with collections and indexes"""
    
    print("=" * 70)
    print("MONGODB DATABASE INITIALIZATION")
    print("=" * 70)
    
    try:
        db_conn = get_db_connection()
        db = db_conn.db
        
        # ==================== STEP 1: CREATE COLLECTIONS ====================
        print("\n[STEP 1] Creating collections...")
        print("-" * 70)
        
        collections_to_create = [
            "users",
            "conversations", 
            "case_predictions",
            "feedback",
            "audit_logs"
        ]
        
        for collection_name in collections_to_create:
            # Check if collection exists
            if collection_name in db.list_collection_names():
                print(f"  ⚠️  {collection_name} already exists (skipping)")
            else:
                db.create_collection(collection_name)
                print(f"  ✅ Created collection: {collection_name}")
        
        # ==================== STEP 2: CREATE INDEXES ====================
        print("\n[STEP 2] Creating indexes...")
        print("-" * 70)
        
        # Users collection indexes
        print("  Creating indexes for 'users' collection...")
        users = db["users"]
        users.create_index("email", unique=True)  # Email must be unique
        print(f"    ✅ email (unique)")
        users.create_index("created_at")
        print(f"    ✅ created_at")
        
        # Conversations collection indexes
        print("  Creating indexes for 'conversations' collection...")
        conversations = db["conversations"]
        conversations.create_index("user_id")
        print(f"    ✅ user_id")
        conversations.create_index([("created_at", -1)])  # -1 = descending (newest first)
        print(f"    ✅ created_at (descending)")
        
        # Case predictions collection indexes
        print("  Creating indexes for 'case_predictions' collection...")
        predictions = db["case_predictions"]
        predictions.create_index("user_id")
        print(f"    ✅ user_id")
        predictions.create_index([("created_at", -1)])
        print(f"    ✅ created_at (descending)")
        predictions.create_index("metadata.case_type")
        print(f"    ✅ metadata.case_type")
        
        # Feedback collection indexes
        print("  Creating indexes for 'feedback' collection...")
        feedback = db["feedback"]
        feedback.create_index("prediction_id")
        print(f"    ✅ prediction_id")
        feedback.create_index("user_id")
        print(f"    ✅ user_id")
        
        # Audit logs collection indexes
        print("  Creating indexes for 'audit_logs' collection...")
        audit_logs = db["audit_logs"]
        audit_logs.create_index("user_id")
        print(f"    ✅ user_id")
        audit_logs.create_index([("created_at", -1)])
        print(f"    ✅ created_at (descending)")
        audit_logs.create_index("action")
        print(f"    ✅ action")
        
        # ==================== STEP 3: VERIFY ====================
        print("\n[STEP 3] Verifying database setup...")
        print("-" * 70)
        
        # List all collections
        collections = db.list_collection_names()
        print(f"\n  Collections in database '{db.name}':")
        for collection_name in sorted(collections):
            collection = db[collection_name]
            doc_count = collection.count_documents({})
            indexes = list(collection.list_indexes())
            index_count = len(indexes)
            print(f"    • {collection_name:20} (documents: {doc_count:4}, indexes: {index_count})")
        
        # ==================== STEP 4: SHOW SCHEMA ====================
        print("\n[STEP 4] Database Schema Summary...")
        print("-" * 70)
        
        print("""
  USERS Collection:
    _id              (ObjectId) - Auto-generated unique ID
    email            (string)   - User email (UNIQUE)
    password_hash    (string)   - Hashed password
    name             (string)   - User's full name
    preferred_language (string) - Language preference
    jurisdiction     (string)   - Legal jurisdiction
    is_active        (boolean)  - Account status
    created_at       (datetime) - Account creation time
    updated_at       (datetime) - Last update time
  
  CONVERSATIONS Collection:
    _id              (ObjectId) - Auto-generated unique ID
    user_id          (string)   - FK to users
    title            (string)   - Conversation title
    language         (string)   - Language of conversation
    messages         (array)    - List of message objects
      ├─ role        (string)   - "user" or "assistant"
      ├─ content     (string)   - Message text
      ├─ timestamp   (datetime) - When message was sent
      └─ language    (string)   - Message language
    created_at       (datetime) - Conversation start
    updated_at       (datetime) - Last message time
  
  CASE_PREDICTIONS Collection:
    _id              (ObjectId) - Auto-generated unique ID
    user_id          (string)   - FK to users
    metadata         (object)   - Case information
      ├─ case_name   (string)   - Name of the case
      ├─ case_type   (string)   - Type of case
      ├─ year        (integer)  - Year of case
      ├─ jurisdiction_state (string) - State/jurisdiction
      ├─ damages     (number)   - Damage amount
      ├─ parties_count (integer) - Number of parties
      └─ is_appeal   (boolean)  - Appeal status
    result           (object)   - Prediction result
      ├─ verdict     (string)   - Predicted verdict
      ├─ confidence  (number)   - Confidence 0-100
      ├─ probabilities (object) - Verdict probabilities
      ├─ shap_explanation (object) - Feature importance
      ├─ similar_cases (array)  - Similar historical cases
      └─ risk_assessment (object) - Risk analysis
    created_at       (datetime) - Prediction time
  
  FEEDBACK Collection:
    _id              (ObjectId) - Auto-generated unique ID
    prediction_id    (string)   - FK to case_predictions
    user_id          (string)   - FK to users
    rating           (integer)  - 1-5 star rating
    comment          (string)   - User feedback text
    was_verdict_correct (boolean) - If prediction was accurate
    created_at       (datetime) - Feedback submission time
  
  AUDIT_LOGS Collection:
    _id              (ObjectId) - Auto-generated unique ID
    user_id          (string)   - FK to users (optional)
    action           (string)   - Action performed
    resource         (string)   - Resource type
    resource_id      (string)   - Resource ID
    details          (object)   - Additional info
    created_at       (datetime) - Action time
        """)
        
        print("\n" + "=" * 70)
        print("✅ DATABASE INITIALIZATION COMPLETE!")
        print("=" * 70)
        print("\nYour MongoDB database is now ready to use!")
        print(f"Database: {db.name}")
        print(f"Host: 127.0.0.1:27017")
        print(f"Collections: {len(collections)}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ INITIALIZATION FAILED")
        print(f"Error: {e}")
        print("\nTroubleshooting:")
        print("  1. Make sure MongoDB server is running (mongod)")
        print("  2. Check that port 27017 is not blocked")
        print("  3. Verify MONGODB_URL in .env file")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = init_database()
    sys.exit(0 if success else 1)
