"""
Phase 4: Database Service
MongoDB operations for storing and retrieving queries, simulations, and analytics
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import os
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

from src.models.database_models import (
    UserSessionModel, QueryRecordModel, SimulationRecordModel,
    ModeDecisionModel, UserFeedbackModel, UserAnalyticsModel,
    ChecklisItemRecordModel
)

logger = logging.getLogger(__name__)


class DatabaseService:
    """
    MongoDB database service for storing and retrieving legal assistant data.
    Handles:
    - User sessions
    - Query records
    - Simulation records
    - Mode decisions
    - User feedback
    - Analytics
    """
    
    def __init__(self, connection_string: Optional[str] = None):
        """
        Initialize MongoDB connection
        
        Args:
            connection_string: MongoDB connection string
                              Defaults to env var MONGODB_URL or localhost
        """
        
        if not connection_string:
            connection_string = os.getenv(
                "MONGODB_URL",
                "mongodb://localhost:27017"
            )
        
        self.connection_string = connection_string
        self.client = None
        self.db = None
        self.is_connected = False
        self._collections = {}
        
        try:
            self._connect()
            logger.info("DatabaseService initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize database: {str(e)}. Running in offline mode.")
            self.is_connected = False
    
    def _connect(self):
        """Connect to MongoDB"""
        try:
            self.client = MongoClient(
                self.connection_string,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=10000
            )
            # Test connection
            self.client.admin.command('ismaster')
            
            self.db = self.client['smart_legal_assistant']
            self._setup_collections()
            self.is_connected = True
            logger.info("Connected to MongoDB successfully")
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"Failed to connect to MongoDB: {str(e)}")
            self.is_connected = False
            raise
    
    def _setup_collections(self):
        """Setup collections and indexes"""
        collection_names = [
            'sessions', 'queries', 'simulations',
            'mode_decisions', 'feedback', 'analytics', 'checklist_items'
        ]
        
        for collection_name in collection_names:
            self._collections[collection_name] = self.db[collection_name]
        
        # Setup indexes
        if self.is_connected:
            try:
                # Sessions indexes
                self._collections['sessions'].create_index('session_id', unique=True)
                self._collections['sessions'].create_index('user_id')
                self._collections['sessions'].create_index('start_time')
                
                # Queries indexes
                self._collections['queries'].create_index('query_id', unique=True)
                self._collections['queries'].create_index('session_id')
                self._collections['queries'].create_index('timestamp')
                self._collections['queries'].create_index('detected_mode')
                
                # Simulations indexes
                self._collections['simulations'].create_index('simulation_id', unique=True)
                self._collections['simulations'].create_index('session_id')
                self._collections['simulations'].create_index('timestamp')
                self._collections['simulations'].create_index('risk_level')
                
                # Mode decisions indexes
                self._collections['mode_decisions'].create_index('decision_id', unique=True)
                self._collections['mode_decisions'].create_index('session_id')
                self._collections['mode_decisions'].create_index('timestamp')
                
                # Feedback indexes
                self._collections['feedback'].create_index('feedback_id', unique=True)
                self._collections['feedback'].create_index('session_id')
                self._collections['feedback'].create_index('timestamp')
                
                # Analytics indexes
                self._collections['analytics'].create_index('analytics_id', unique=True)
                self._collections['analytics'].create_index('session_id', unique=True)
                self._collections['analytics'].create_index('user_id')
                
                logger.info("Database indexes created successfully")
                
            except Exception as e:
                logger.warning(f"Error setting up indexes: {str(e)}")
    
    # Session operations
    
    def save_session(self, session: UserSessionModel) -> bool:
        """Save user session"""
        if not self.is_connected:
            logger.warning("Database not connected - session not saved")
            return False
        
        try:
            session_dict = session.dict()
            self._collections['sessions'].replace_one(
                {'session_id': session.session_id},
                session_dict,
                upsert=True
            )
            logger.debug(f"Session saved: {session.session_id}")
            return True
        except Exception as e:
            logger.error(f"Error saving session: {str(e)}")
            return False
    
    def get_session(self, session_id: str) -> Optional[UserSessionModel]:
        """Retrieve user session"""
        if not self.is_connected:
            return None
        
        try:
            result = self._collections['sessions'].find_one({'session_id': session_id})
            if result:
                result.pop('_id', None)
                return UserSessionModel(**result)
            return None
        except Exception as e:
            logger.error(f"Error retrieving session: {str(e)}")
            return None
    
    def update_session_activity(self, session_id: str) -> bool:
        """Update session's last activity timestamp"""
        if not self.is_connected:
            return False
        
        try:
            self._collections['sessions'].update_one(
                {'session_id': session_id},
                {'$set': {'last_activity': datetime.utcnow()}}
            )
            return True
        except Exception as e:
            logger.error(f"Error updating session activity: {str(e)}")
            return False
    
    # Query operations
    
    def save_query_record(self, query_record: QueryRecordModel) -> bool:
        """Save query and response record"""
        if not self.is_connected:
            logger.warning("Database not connected - query not saved")
            return False
        
        try:
            record_dict = query_record.dict()
            self._collections['queries'].insert_one(record_dict)
            logger.debug(f"Query saved: {query_record.query_id}")
            return True
        except Exception as e:
            logger.error(f"Error saving query record: {str(e)}")
            return False
    
    def get_query_record(self, query_id: str) -> Optional[QueryRecordModel]:
        """Retrieve query record"""
        if not self.is_connected:
            return None
        
        try:
            result = self._collections['queries'].find_one({'query_id': query_id})
            if result:
                result.pop('_id', None)
                return QueryRecordModel(**result)
            return None
        except Exception as e:
            logger.error(f"Error retrieving query record: {str(e)}")
            return None
    
    def get_session_queries(self, session_id: str) -> List[QueryRecordModel]:
        """Get all queries in a session"""
        if not self.is_connected:
            return []
        
        try:
            results = self._collections['queries'].find(
                {'session_id': session_id}
            ).sort('timestamp', -1)
            
            records = []
            for result in results:
                result.pop('_id', None)
                records.append(QueryRecordModel(**result))
            return records
        except Exception as e:
            logger.error(f"Error retrieving session queries: {str(e)}")
            return []
    
    def save_query_feedback(self, query_id: str, rating: int, comment: Optional[str] = None) -> bool:
        """Save user feedback on query response"""
        if not self.is_connected:
            return False
        
        try:
            self._collections['queries'].update_one(
                {'query_id': query_id},
                {'$set': {
                    'user_feedback': rating,
                    'user_comment': comment
                }}
            )
            return True
        except Exception as e:
            logger.error(f"Error saving query feedback: {str(e)}")
            return False
    
    # Simulation operations
    
    def save_simulation_record(self, simulation_record: SimulationRecordModel) -> bool:
        """Save consequence simulation record"""
        if not self.is_connected:
            logger.warning("Database not connected - simulation not saved")
            return False
        
        try:
            record_dict = simulation_record.dict()
            self._collections['simulations'].insert_one(record_dict)
            logger.debug(f"Simulation saved: {simulation_record.simulation_id}")
            return True
        except Exception as e:
            logger.error(f"Error saving simulation record: {str(e)}")
            return False
    
    def get_simulation_record(self, simulation_id: str) -> Optional[SimulationRecordModel]:
        """Retrieve simulation record"""
        if not self.is_connected:
            return None
        
        try:
            result = self._collections['simulations'].find_one({'simulation_id': simulation_id})
            if result:
                result.pop('_id', None)
                return SimulationRecordModel(**result)
            return None
        except Exception as e:
            logger.error(f"Error retrieving simulation record: {str(e)}")
            return None
    
    def get_session_simulations(self, session_id: str) -> List[SimulationRecordModel]:
        """Get all simulations in a session"""
        if not self.is_connected:
            return []
        
        try:
            results = self._collections['simulations'].find(
                {'session_id': session_id}
            ).sort('timestamp', -1)
            
            records = []
            for result in results:
                result.pop('_id', None)
                records.append(SimulationRecordModel(**result))
            return records
        except Exception as e:
            logger.error(f"Error retrieving session simulations: {str(e)}")
            return []
    
    def save_simulation_feedback(self, simulation_id: str, rating: int, 
                                 comment: Optional[str] = None, helpful: Optional[bool] = None) -> bool:
        """Save user feedback on simulation"""
        if not self.is_connected:
            return False
        
        try:
            self._collections['simulations'].update_one(
                {'simulation_id': simulation_id},
                {'$set': {
                    'user_feedback': rating,
                    'user_comment': comment,
                    'user_found_helpful': helpful
                }}
            )
            return True
        except Exception as e:
            logger.error(f"Error saving simulation feedback: {str(e)}")
            return False
    
    # Mode decision operations
    
    def save_mode_decision(self, decision: ModeDecisionModel) -> bool:
        """Save mode detection decision"""
        if not self.is_connected:
            return False
        
        try:
            decision_dict = decision.dict()
            self._collections['mode_decisions'].insert_one(decision_dict)
            return True
        except Exception as e:
            logger.error(f"Error saving mode decision: {str(e)}")
            return False
    
    def update_mode_decision_feedback(self, decision_id: str, accepted: bool, selected_mode: Optional[str] = None) -> bool:
        """Update whether user accepted mode recommendation"""
        if not self.is_connected:
            return False
        
        try:
            update_dict = {'user_accepted_mode': accepted}
            if selected_mode:
                update_dict['user_selected_mode'] = selected_mode
            
            self._collections['mode_decisions'].update_one(
                {'decision_id': decision_id},
                {'$set': update_dict}
            )
            return True
        except Exception as e:
            logger.error(f"Error updating mode decision: {str(e)}")
            return False
    
    # Feedback operations
    
    def save_feedback(self, feedback: UserFeedbackModel) -> bool:
        """Save user feedback"""
        if not self.is_connected:
            return False
        
        try:
            feedback_dict = feedback.dict()
            self._collections['feedback'].insert_one(feedback_dict)
            return True
        except Exception as e:
            logger.error(f"Error saving feedback: {str(e)}")
            return False
    
    # Analytics operations
    
    def save_analytics(self, analytics: UserAnalyticsModel) -> bool:
        """Save session analytics"""
        if not self.is_connected:
            return False
        
        try:
            analytics_dict = analytics.dict()
            self._collections['analytics'].replace_one(
                {'session_id': analytics.session_id},
                analytics_dict,
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Error saving analytics: {str(e)}")
            return False
    
    def get_analytics(self, session_id: str) -> Optional[UserAnalyticsModel]:
        """Retrieve analytics for session"""
        if not self.is_connected:
            return None
        
        try:
            result = self._collections['analytics'].find_one({'session_id': session_id})
            if result:
                result.pop('_id', None)
                return UserAnalyticsModel(**result)
            return None
        except Exception as e:
            logger.error(f"Error retrieving analytics: {str(e)}")
            return None
    
    # System statistics
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get overall system statistics"""
        if not self.is_connected:
            return {}
        
        try:
            stats = {
                'total_sessions': self._collections['sessions'].count_documents({}),
                'total_queries': self._collections['queries'].count_documents({}),
                'total_simulations': self._collections['simulations'].count_documents({}),
                'total_feedback': self._collections['feedback'].count_documents({}),
            }
            
            # Mode distribution
            mode_dist = self._collections['queries'].aggregate([
                {'$group': {'_id': '$detected_mode', 'count': {'$sum': 1}}}
            ])
            stats['mode_distribution'] = {doc['_id']: doc['count'] for doc in mode_dist}
            
            # Risk distribution
            risk_dist = self._collections['simulations'].aggregate([
                {'$group': {'_id': '$risk_level', 'count': {'$sum': 1}}}
            ])
            stats['risk_distribution'] = {doc['_id']: doc['count'] for doc in risk_dist}
            
            # Average mode confidence
            mode_conf = self._collections['queries'].aggregate([
                {'$group': {'_id': None, 'avg_confidence': {'$avg': '$mode_confidence'}}}
            ])
            mode_conf_list = list(mode_conf)
            if mode_conf_list:
                stats['avg_mode_confidence'] = round(mode_conf_list[0]['avg_confidence'], 3)
            
            # Average risk score
            risk_score = self._collections['simulations'].aggregate([
                {'$group': {'_id': None, 'avg_score': {'$avg': '$risk_score'}}}
            ])
            risk_score_list = list(risk_score)
            if risk_score_list:
                stats['avg_risk_score'] = round(risk_score_list[0]['avg_score'], 1)
            
            return stats
        except Exception as e:
            logger.error(f"Error retrieving system stats: {str(e)}")
            return {}
    
    def health_check(self) -> bool:
        """Check database connection health"""
        if not self.is_connected:
            return False
        
        try:
            self.client.admin.command('ping')
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
            self.is_connected = False
            return False
    
    def close(self):
        """Close database connection"""
        if self.client:
            self.client.close()
            self.is_connected = False
            logger.info("Database connection closed")


# Global instance
_db_instance: Optional[DatabaseService] = None


def get_database_service() -> DatabaseService:
    """Get or create singleton database service instance"""
    global _db_instance
    if _db_instance is None:
        _db_instance = DatabaseService()
    return _db_instance
