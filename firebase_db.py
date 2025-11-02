"""
Firebase Database Client for Backend

This module provides Firestore database access for the entire backend,
replacing PostgreSQL for unified real-time sync with Sahay ecosystem.

Usage:
    from firebase_db import get_firestore
    
    db = get_firestore()
    doc_ref = db.collection('users').document(user_id)
    doc_ref.set(user_data)
"""

import firebase_admin
from firebase_admin import credentials, firestore
import os
from pathlib import Path
from dotenv import load_dotenv
import json
import logging

# Load environment variables - try .env.production first (for Cloud Run), then .env (for local dev)
env_path = Path(".env.production")
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()  # Fallback to .env for local development

logger = logging.getLogger(__name__)

_app = None
_db = None


def initialize_firebase():
    """
    Initialize Firebase Admin SDK with service account credentials.
    
    Reads credentials from:
    1. SERVICE_ACCOUNT_KEY_PATH (path to JSON file)
    2. Or GOOGLE_APPLICATION_CREDENTIALS (environment variable)
    
    Raises:
        Exception: If Firebase initialization fails
    """
    global _app, _db
    
    if _app:
        logger.info("Firebase already initialized")
        return _app
    
    try:
        # Try SERVICE_ACCOUNT_KEY_PATH first
        service_account_path = os.getenv('SERVICE_ACCOUNT_KEY_PATH')
        
        if service_account_path:
            logger.info(f"Loading Firebase credentials from: {service_account_path}")
            with open(service_account_path, 'r') as f:
                service_account_info = json.load(f)
            
            cred = credentials.Certificate(service_account_info)
            _app = firebase_admin.initialize_app(cred)
            _db = firestore.client()
            
            logger.info("✅ Firebase Admin SDK initialized successfully")
            return _app
        
        # Fallback to GOOGLE_APPLICATION_CREDENTIALS
        google_creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        if google_creds_path and os.path.exists(google_creds_path):
            logger.info(f"Using GOOGLE_APPLICATION_CREDENTIALS: {google_creds_path}")
            cred = credentials.Certificate(google_creds_path)
            _app = firebase_admin.initialize_app(cred)
            _db = firestore.client()
            
            logger.info("✅ Firebase Admin SDK initialized from GOOGLE_APPLICATION_CREDENTIALS")
            return _app
        
        # Try default credentials (if running on GCP)
        try:
            _app = firebase_admin.initialize_app()
            _db = firestore.client()
            logger.info("✅ Firebase Admin SDK initialized with default credentials")
            return _app
        except Exception as default_error:
            raise Exception(
                f"Firebase initialization failed. Provide SERVICE_ACCOUNT_KEY_PATH or "
                f"GOOGLE_APPLICATION_CREDENTIALS. Error: {default_error}"
            )
            
    except FileNotFoundError as e:
        raise Exception(
            f"Firebase credentials file not found: {e}. "
            f"Set SERVICE_ACCOUNT_KEY_PATH or GOOGLE_APPLICATION_CREDENTIALS environment variable."
        )
    except json.JSONDecodeError as e:
        raise Exception(f"Invalid JSON in Firebase credentials file: {e}")
    except Exception as e:
        raise Exception(f"Firebase initialization failed: {e}")


def get_firestore():
    """
    Get Firestore database client instance.
    
    Returns:
        firestore.Client: Firestore database client
        
    Raises:
        Exception: If Firebase is not initialized
    """
    global _db
    
    if not _db:
        # Try to initialize if not already done
        initialize_firebase()
    
    if not _db:
        raise Exception(
            "Firebase not initialized. Call initialize_firebase() first or "
            "set SERVICE_ACCOUNT_KEY_PATH environment variable."
        )
    
    return _db


def close_firebase():
    """Close Firebase connection and cleanup"""
    global _app, _db
    
    if _app:
        firebase_admin.delete_app(_app)
        _app = None
        _db = None
        logger.info("Firebase connection closed")

