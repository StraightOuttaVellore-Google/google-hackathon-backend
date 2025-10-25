#!/usr/bin/env python3
"""
Quota Management Utility for Hybrid RAG System
Provides information about Google Cloud quotas and usage
"""

import os
import logging
from typing import Dict, Any
from google.cloud import aiplatform
import vertexai
from vertexai import rag

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class QuotaManager:
    """Manages and monitors Google Cloud quotas for RAG operations"""
    
    def __init__(self, project_id: str, location: str = "us-east1"):
        self.project_id = project_id
        self.location = location
        
        # Initialize Vertex AI
        try:
            vertexai.init(project=self.project_id, location=self.location)
            logger.info(f"✅ Vertex AI initialized for quota management")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Vertex AI: {e}")
            raise
    
    def get_corpus_info(self) -> Dict[str, Any]:
        """Get information about available corpora"""
        try:
            corpora = rag.list_corpora()
            corpus_info = {
                "total_corpora": len(corpora),
                "corpora": []
            }
            
            for corpus in corpora:
                corpus_data = {
                    "name": corpus.display_name,
                    "corpus_id": corpus.name.split("/")[-1],
                    "description": getattr(corpus, 'description', 'No description'),
                    "state": getattr(corpus, 'state', 'Unknown')
                }
                corpus_info["corpora"].append(corpus_data)
            
            return corpus_info
            
        except Exception as e:
            logger.error(f"❌ Error getting corpus info: {e}")
            return {"error": str(e)}
    
    def check_quota_status(self) -> Dict[str, Any]:
        """Check current quota status"""
        try:
            # This is a simplified check - actual quota checking requires
            # Google Cloud Console or specific quota APIs
            return {
                "status": "quota_check_available",
                "message": "For detailed quota information, check Google Cloud Console",
                "console_url": f"https://console.cloud.google.com/iam-admin/quotas?project={self.project_id}",
                "recommendations": [
                    "Check 'aiplatform.googleapis.com/online_prediction_requests_per_base_model' quota",
                    "Consider requesting quota increase for textembedding-gecko model",
                    "Monitor usage in Google Cloud Console"
                ]
            }
            
        except Exception as e:
            logger.error(f"❌ Error checking quota status: {e}")
            return {"error": str(e)}
    
    def get_usage_recommendations(self) -> Dict[str, Any]:
        """Get recommendations for quota management"""
        return {
            "immediate_actions": [
                "Request quota increase for textembedding-gecko model",
                "Enable billing if not already enabled",
                "Check for any billing account issues"
            ],
            "optimization_tips": [
                "Use caching to reduce API calls",
                "Implement retry logic with exponential backoff",
                "Consider batch processing for multiple queries",
                "Monitor usage patterns and optimize query frequency"
            ],
            "fallback_strategies": [
                "System gracefully falls back to original input without RAG",
                "Conversation history is still maintained",
                "Core voice agent functionality remains available"
            ]
        }

def main():
    """Main function to check quota status"""
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT_ID")
    if not project_id:
        logger.error("❌ GOOGLE_CLOUD_PROJECT_ID not set")
        return
    
    logger.info(f"🔍 Checking quota status for project: {project_id}")
    
    try:
        quota_manager = QuotaManager(project_id)
        
        # Get corpus information
        logger.info("📋 Getting corpus information...")
        corpus_info = quota_manager.get_corpus_info()
        logger.info(f"📊 Found {corpus_info.get('total_corpora', 0)} corpora")
        
        for corpus in corpus_info.get('corpora', []):
            logger.info(f"   - {corpus['name']} (ID: {corpus['corpus_id']})")
        
        # Check quota status
        logger.info("🔍 Checking quota status...")
        quota_status = quota_manager.check_quota_status()
        logger.info(f"📊 Quota status: {quota_status.get('status', 'unknown')}")
        
        # Get recommendations
        logger.info("💡 Getting usage recommendations...")
        recommendations = quota_manager.get_usage_recommendations()
        
        logger.info("🎯 Immediate Actions:")
        for action in recommendations["immediate_actions"]:
            logger.info(f"   - {action}")
        
        logger.info("⚡ Optimization Tips:")
        for tip in recommendations["optimization_tips"]:
            logger.info(f"   - {tip}")
        
        logger.info("🔄 Fallback Strategies:")
        for strategy in recommendations["fallback_strategies"]:
            logger.info(f"   - {strategy}")
        
        logger.info("✅ Quota check completed")
        
    except Exception as e:
        logger.error(f"❌ Error during quota check: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

