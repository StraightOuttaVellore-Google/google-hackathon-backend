"""
Vertex AI RAG Engine Integration for Voice Agents
This module provides RAG functionality for both wellness and study voice agents
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio
from pathlib import Path

# Google Cloud imports
from google.cloud import aiplatform
import vertexai
from vertexai import rag
from google.genai.types import VertexRagStore, VertexRagStoreRagResource, Tool, Retrieval

# Import dataset processor
from dataset_processor import initialize_dataset_processing, process_and_upload_datasets

logger = logging.getLogger(__name__)

class VertexRAGManager:
    """Manages Vertex AI RAG Engine integration for voice agents using high-level API"""
    
    def __init__(self, project_id: str, location: str = "us-east1"):
        self.project_id = project_id
        self.location = location
        self.corpora = {}  # Store corpus info locally
        
    async def create_rag_corpus(self, corpus_name: str, description: str) -> Optional[str]:
        """Create a new RAG corpus using high-level API"""
        try:
            # Initialize Vertex AI
            vertexai.init(project=self.project_id, location=self.location)
            
            # Configure backend config
            backend_config = rag.RagVectorDbConfig(
                rag_embedding_model_config=rag.RagEmbeddingModelConfig(
                    vertex_prediction_endpoint=rag.VertexPredictionEndpoint(
                        publisher_model="publishers/google/models/text-embedding-005"
                    )
                )
            )
            
            # Create corpus
            corpus = rag.create_corpus(
                display_name=corpus_name,
                description=description,
                backend_config=backend_config,
            )
            
            corpus_id = corpus.name.split("/")[-1]
            self.corpora[corpus_id] = {
                "name": corpus_name,
                "corpus_name": corpus.name,
                "description": description
            }
            
            logger.info(f"Created RAG corpus: {corpus_name} with ID: {corpus_id}")
            return corpus_id
            
        except Exception as e:
            logger.error(f"Failed to create RAG corpus: {e}")
            return None
    
    async def upload_documents_to_corpus(self, corpus_id: str, documents: List[Dict[str, Any]]) -> bool:
        """Upload documents to a RAG corpus using high-level API"""
        try:
            if corpus_id not in self.corpora:
                logger.error(f"Corpus {corpus_id} not found")
                return False
                
            corpus_name = self.corpora[corpus_id]["corpus_name"]
            
            # Convert documents to GCS URIs (assuming they're already uploaded)
            gcs_uris = []
            for doc in documents:
                if isinstance(doc, str) and doc.startswith("gs://"):
                    gcs_uris.append(doc)
                elif isinstance(doc, dict) and "gcs_uri" in doc:
                    gcs_uris.append(doc["gcs_uri"])
            
            if not gcs_uris:
                logger.warning("No GCS URIs found in documents")
                return False
            
            # Import files using high-level API
            response = rag.import_files(
                corpus_name=corpus_name,
                paths=gcs_uris,
                transformation_config=rag.TransformationConfig(
                    rag.ChunkingConfig(chunk_size=512, chunk_overlap=100)
                ),
                max_embedding_requests_per_min=900,
            )
            
            logger.info(f"Imported {response.imported_rag_files_count} files to corpus {corpus_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to upload documents to corpus: {e}")
            return False
    
    def get_rag_tool_config(self, corpus_id: str) -> Dict[str, Any]:
        """Get RAG tool configuration for Gemini Live API"""
        if corpus_id not in self.corpora:
            logger.error(f"Corpus {corpus_id} not found")
            return {}
            
        corpus_name = self.corpora[corpus_id]["corpus_name"]
        
        return {
            "retrieval": {
                "vertexRagStore": {
                    "ragResources": [
                        {
                            "ragCorpus": corpus_name
                        }
                    ]
                }
            }
        }

class DatasetProcessor:
    """Processes and prepares datasets for RAG integration"""
    
    def __init__(self, rag_manager: VertexRAGManager):
        self.rag_manager = rag_manager
        
    def process_study_dataset(self, dataset_path: str) -> List[Dict[str, Any]]:
        """Process the study dataset for RAG integration"""
        try:
            # Read the study document
            with open(dataset_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Split into chunks for better retrieval
            chunks = self._split_into_chunks(content, chunk_size=1000, overlap=200)
            
            documents = []
            for i, chunk in enumerate(chunks):
                doc = {
                    'title': f'Study Guide Section {i+1}',
                    'content': chunk,
                    'type': 'study_guidance',
                    'metadata': {
                        'source': 'study_doc.md',
                        'chunk_id': i,
                        'created_at': datetime.now().isoformat()
                    }
                }
                documents.append(doc)
            
            logger.info(f"Processed study dataset into {len(documents)} chunks")
            return documents
            
        except Exception as e:
            logger.error(f"Failed to process study dataset: {e}")
            return []
    
    def process_wellness_dataset(self, dataset_path: str) -> List[Dict[str, Any]]:
        """Process the wellness dataset for RAG integration"""
        try:
            documents = []
            
            # Process CSV data
            csv_path = os.path.join(dataset_path, 'data', 'counselchat-data.csv')
            if os.path.exists(csv_path):
                import pandas as pd
                df = pd.read_csv(csv_path)
                
                for idx, row in df.iterrows():
                    # Create Q&A pairs
                    question = row.get('questionText', '')
                    answer = row.get('answerText', '')
                    topics = row.get('topics', '')
                    
                    if question and answer:
                        doc = {
                            'title': f'Counseling Q&A {idx+1}',
                            'content': f"Question: {question}\n\nAnswer: {answer}",
                            'type': 'wellness_counseling',
                            'metadata': {
                                'source': 'counselchat-data.csv',
                                'topics': topics,
                                'question_id': row.get('questionID', ''),
                                'therapist': row.get('therapistName', ''),
                                'created_at': datetime.now().isoformat()
                            }
                        }
                        documents.append(doc)
            
            logger.info(f"Processed wellness dataset into {len(documents)} documents")
            return documents
            
        except Exception as e:
            logger.error(f"Failed to process wellness dataset: {e}")
            return []
    
    def _split_into_chunks(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """Split text into overlapping chunks"""
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # Try to break at sentence boundary
            if end < len(text):
                # Find last sentence ending within chunk
                last_period = text.rfind('.', start, end)
                last_question = text.rfind('?', start, end)
                last_exclamation = text.rfind('!', start, end)
                
                break_point = max(last_period, last_question, last_exclamation)
                if break_point > start + chunk_size // 2:  # Only if it's not too early
                    end = break_point + 1
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - overlap
            if start >= len(text):
                break
                
        return chunks

class RAGVoiceAgent:
    """RAG-enhanced voice agent that integrates with Vertex AI RAG Engine"""
    
    def __init__(self, project_id: str, location: str = "us-east1"):
        self.project_id = project_id
        self.location = location
        self.rag_manager = VertexRAGManager(project_id, location)
        self.dataset_processor = DatasetProcessor(self.rag_manager)
        
        # Corpus IDs (will be set after creation)
        self.study_corpus_id = None
        self.wellness_corpus_id = None
        
    async def initialize_corpora(self) -> bool:
        """Initialize RAG corpora for both study and wellness modes"""
        try:
            # Create study corpus
            self.study_corpus_id = await self.rag_manager.create_rag_corpus(
                corpus_name="study-voice-agent-corpus",
                description="RAG corpus for study voice agent with academic guidance content"
            )
            
            # Create wellness corpus
            self.wellness_corpus_id = await self.rag_manager.create_rag_corpus(
                corpus_name="wellness-voice-agent-corpus", 
                description="RAG corpus for wellness voice agent with counseling content"
            )
            
            if not self.study_corpus_id or not self.wellness_corpus_id:
                logger.error("Failed to create RAG corpora")
                return False
            
            # Process and upload datasets
            await self._upload_datasets()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize corpora: {e}")
            return False
    
    async def _upload_datasets(self):
        """Upload processed datasets to their respective corpora"""
        try:
            # Process study dataset
            study_docs = self.dataset_processor.process_study_dataset(
                "/home/vatsal/Hackathons/GenAIExchange/FullStackR2/backend/rag_dataset/study_doc.md"
            )
            
            # Process wellness dataset
            wellness_docs = self.dataset_processor.process_wellness_dataset(
                "/home/vatsal/Hackathons/GenAIExchange/FullStackR2/backend/rag_dataset/counsel_chat_dataset"
            )
            
            # Upload to respective corpora
            if study_docs and self.study_corpus_id:
                await self.rag_manager.upload_documents_to_corpus(
                    self.study_corpus_id, study_docs
                )
            
            if wellness_docs and self.wellness_corpus_id:
                await self.rag_manager.upload_documents_to_corpus(
                    self.wellness_corpus_id, wellness_docs
                )
                
        except Exception as e:
            logger.error(f"Failed to upload datasets: {e}")
    
    def get_rag_config_for_mode(self, mode: str) -> Dict[str, Any]:
        """Get RAG configuration for specific agent mode"""
        if mode == "study" and self.study_corpus_id:
            return self.rag_manager.get_rag_tool_config(self.study_corpus_id)
        elif mode == "wellness" and self.wellness_corpus_id:
            return self.rag_manager.get_rag_tool_config(self.wellness_corpus_id)
        else:
            logger.warning(f"No RAG corpus available for mode: {mode}")
            return {}

# Global RAG agent instance
rag_agent = None

async def initialize_rag_system(project_id: str, location: str = "us-east1") -> bool:
    """Initialize the RAG system for voice agents"""
    global rag_agent
    
    try:
        # Initialize dataset processing
        dataset_success = await initialize_dataset_processing(project_id, location)
        if not dataset_success:
            logger.error("Failed to initialize dataset processing")
            return False
        
        # Process and upload datasets
        corpus_ids = await process_and_upload_datasets()
        if not corpus_ids:
            logger.error("Failed to process and upload datasets")
            return False
        
        # Initialize RAG agent
        rag_agent = RAGVoiceAgent(project_id, location)
        rag_agent.study_corpus_id = corpus_ids.get("study")
        rag_agent.wellness_corpus_id = corpus_ids.get("wellness")
        
        # Populate the rag_manager's corpora dictionary
        if rag_agent.study_corpus_id:
            corpus_name = f"projects/{project_id}/locations/{location}/ragCorpora/{rag_agent.study_corpus_id}"
            rag_agent.rag_manager.corpora[rag_agent.study_corpus_id] = {
                "name": "academic-success-corpus",
                "corpus_name": corpus_name,
                "description": "RAG corpus for academic success and study support"
            }
        
        if rag_agent.wellness_corpus_id:
            corpus_name = f"projects/{project_id}/locations/{location}/ragCorpora/{rag_agent.wellness_corpus_id}"
            rag_agent.rag_manager.corpora[rag_agent.wellness_corpus_id] = {
                "name": "mental-health-wellness-corpus",
                "corpus_name": corpus_name,
                "description": "RAG corpus for mental health and wellness support"
            }
        
        logger.info("RAG system initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error initializing RAG system: {e}")
        return False

def get_rag_config(mode: str) -> Dict[str, Any]:
    """Get RAG configuration for the specified mode"""
    global rag_agent
    
    if not rag_agent:
        logger.warning("RAG agent not initialized")
        return {}
    
    return rag_agent.get_rag_config_for_mode(mode)
