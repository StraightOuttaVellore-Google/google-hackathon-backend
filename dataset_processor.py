"""
Dataset Processor for RAG Integration
Processes enhanced datasets and uploads them to Google Cloud Storage for Vertex AI RAG Engine
"""

import os
import json
import logging
from typing import List, Dict, Any
from datetime import datetime
from pathlib import Path
import pandas as pd

# Google Cloud imports
from google.cloud import storage
from google.cloud import aiplatform
import vertexai
from vertexai import rag

logger = logging.getLogger(__name__)

class DatasetProcessor:
    """Processes datasets and uploads them to Google Cloud Storage for RAG"""
    
    def __init__(self, project_id: str, bucket_name: str = None):
        self.project_id = project_id
        self.bucket_name = bucket_name or f"{project_id}-rag-datasets"
        self.storage_client = storage.Client(project=project_id)
        self._ensure_bucket_exists()
        
    def _ensure_bucket_exists(self):
        """Ensure the GCS bucket exists for storing datasets"""
        try:
            bucket = self.storage_client.bucket(self.bucket_name)
            if not bucket.exists():
                bucket = self.storage_client.create_bucket(self.bucket_name)
                logger.info(f"Created bucket: {self.bucket_name}")
            else:
                logger.info(f"Using existing bucket: {self.bucket_name}")
        except Exception as e:
            logger.error(f"Error with bucket {self.bucket_name}: {e}")
            raise
    
    def process_academic_dataset(self, dataset_path: str) -> List[str]:
        """Process the academic success knowledge base and upload to GCS"""
        try:
            # Read the academic success knowledge base
            with open(dataset_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Split into logical sections for better retrieval
            sections = self._split_into_sections(content)
            
            uploaded_files = []
            for i, section in enumerate(sections):
                # Create a structured document
                doc = {
                    "title": f"Academic Success Guide Section {i+1}",
                    "content": section,
                    "type": "academic_guidance",
                    "metadata": {
                        "source": "academic_success_knowledge_base.md",
                        "section_id": i,
                        "created_at": datetime.now().isoformat(),
                        "agent_mode": "study"
                    }
                }
                
                # Upload to GCS
                filename = f"academic_dataset/section_{i+1}.json"
                gcs_uri = self._upload_to_gcs(doc, filename)
                uploaded_files.append(gcs_uri)
                
            logger.info(f"Processed academic dataset into {len(uploaded_files)} sections")
            return uploaded_files
            
        except Exception as e:
            logger.error(f"Failed to process academic dataset: {e}")
            return []
    
    def process_wellness_dataset(self, dataset_path: str) -> List[str]:
        """Process the enhanced wellness dataset and upload to GCS"""
        try:
            # Read the enhanced wellness dataset
            with open(dataset_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Split into logical sections for better retrieval
            sections = self._split_into_sections(content)
            
            uploaded_files = []
            for i, section in enumerate(sections):
                # Create a structured document
                doc = {
                    "title": f"Wellness Guide Section {i+1}",
                    "content": section,
                    "type": "wellness_counseling",
                    "metadata": {
                        "source": "enhanced_wellness_dataset.md",
                        "section_id": i,
                        "created_at": datetime.now().isoformat(),
                        "agent_mode": "wellness"
                    }
                }
                
                # Upload to GCS
                filename = f"wellness_dataset/section_{i+1}.json"
                gcs_uri = self._upload_to_gcs(doc, filename)
                uploaded_files.append(gcs_uri)
                
            logger.info(f"Processed wellness dataset into {len(uploaded_files)} sections")
            return uploaded_files
            
        except Exception as e:
            logger.error(f"Failed to process wellness dataset: {e}")
            return []
    
    def process_mental_health_dataset(self, dataset_path: str) -> List[str]:
        """Process the mental health knowledge base and upload to GCS"""
        try:
            # Read the mental health knowledge base
            with open(dataset_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Split into logical sections for better retrieval
            sections = self._split_into_sections(content)
            
            uploaded_files = []
            for i, section in enumerate(sections):
                # Create a structured document
                doc = {
                    "title": f"Mental Health Guide Section {i+1}",
                    "content": section,
                    "type": "mental_health_support",
                    "metadata": {
                        "source": "mental_health_knowledge_base.md",
                        "section_id": i,
                        "created_at": datetime.now().isoformat(),
                        "agent_mode": "wellness"
                    }
                }
                
                # Upload to GCS
                filename = f"mental_health_dataset/section_{i+1}.json"
                gcs_uri = self._upload_to_gcs(doc, filename)
                uploaded_files.append(gcs_uri)
                
            logger.info(f"Processed mental health dataset into {len(uploaded_files)} sections")
            return uploaded_files
            
        except Exception as e:
            logger.error(f"Failed to process mental health dataset: {e}")
            return []
    
    def process_counsel_chat_json_dataset(self, dataset_path: str) -> List[str]:
        """Process the counsel chat JSON dataset and upload to GCS"""
        try:
            # Read the counsel chat JSON file
            with open(dataset_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            uploaded_files = []
            
            # Process the training data
            if 'train' in data and isinstance(data['train'], list):
                conversations = data['train']
                
                # Process in batches to avoid memory issues and stay under 25-file limit
                batch_size = 20
                for batch_start in range(0, len(conversations), batch_size):
                    batch_end = min(batch_start + batch_size, len(conversations))
                    batch_conversations = conversations[batch_start:batch_end]
                    
                    batch_docs = []
                    for i, conversation in enumerate(batch_conversations):
                        if 'utterances' in conversation and conversation['utterances']:
                            for j, utterance in enumerate(conversation['utterances']):
                                if 'history' in utterance and 'candidates' in utterance:
                                    history = utterance['history']
                                    candidates = utterance['candidates']
                                    
                                    # Create Q&A pairs from the conversation data
                                    if history and candidates:
                                        # Use the last history item as the question
                                        question = history[-1] if history else "Mental health support needed"
                                        
                                        # Use the first candidate as the answer
                                        answer = candidates[0] if candidates else "I'm here to help you."
                                        
                                        doc = {
                                            "title": f"Counsel Chat Conversation {batch_start + i + 1}-{j + 1}",
                                            "content": f"Question: {question}\n\nAnswer: {answer}",
                                            "type": "therapy_conversation",
                                            "metadata": {
                                                "source": "counsel_chat_250-tokens_full.json",
                                                "conversation_id": batch_start + i,
                                                "utterance_id": j,
                                                "created_at": datetime.now().isoformat(),
                                                "agent_mode": "wellness"
                                            }
                                        }
                                        batch_docs.append(doc)
                    
                    # Upload batch to GCS
                    if batch_docs:
                        filename = f"counsel_chat_json/batch_{batch_start//batch_size + 1}.json"
                        gcs_uri = self._upload_batch_to_gcs(batch_docs, filename)
                        uploaded_files.append(gcs_uri)
            
            logger.info(f"Processed counsel chat JSON dataset into {len(uploaded_files)} batches")
            return uploaded_files
            
        except Exception as e:
            logger.error(f"Failed to process counsel chat JSON dataset: {e}")
            return []
    
    def _split_into_sections(self, content: str) -> List[str]:
        """Split content into logical sections based on headers"""
        sections = []
        current_section = []
        
        lines = content.split('\n')
        for line in lines:
            # Check if this is a header (starts with #)
            if line.strip().startswith('#'):
                # Save current section if it has content
                if current_section:
                    sections.append('\n'.join(current_section))
                    current_section = []
            
            current_section.append(line)
        
        # Add the last section
        if current_section:
            sections.append('\n'.join(current_section))
        
        # Filter out very short sections
        sections = [section for section in sections if len(section.strip()) > 200]
        
        return sections
    
    def _upload_to_gcs(self, doc: Dict[str, Any], filename: str) -> str:
        """Upload a single document to Google Cloud Storage"""
        try:
            bucket = self.storage_client.bucket(self.bucket_name)
            blob = bucket.blob(filename)
            
            # Convert to JSON string
            json_content = json.dumps(doc, indent=2, ensure_ascii=False)
            
            # Upload
            blob.upload_from_string(json_content, content_type='application/json')
            
            gcs_uri = f"gs://{self.bucket_name}/{filename}"
            logger.debug(f"Uploaded document to: {gcs_uri}")
            return gcs_uri
            
        except Exception as e:
            logger.error(f"Failed to upload document {filename}: {e}")
            raise
    
    def _upload_batch_to_gcs(self, docs: List[Dict[str, Any]], filename: str) -> str:
        """Upload a batch of documents to Google Cloud Storage"""
        try:
            bucket = self.storage_client.bucket(self.bucket_name)
            blob = bucket.blob(filename)
            
            # Convert to JSON array
            json_content = json.dumps(docs, indent=2, ensure_ascii=False)
            
            # Upload
            blob.upload_from_string(json_content, content_type='application/json')
            
            gcs_uri = f"gs://{self.bucket_name}/{filename}"
            logger.debug(f"Uploaded batch to: {gcs_uri}")
            return gcs_uri
            
        except Exception as e:
            logger.error(f"Failed to upload batch {filename}: {e}")
            raise

class RAGCorpusManager:
    """Manages RAG corpora creation and document upload using high-level vertexai.rag API"""
    
    def __init__(self, project_id: str, location: str = "us-east1"):
        self.project_id = project_id
        self.location = location
        
    async def create_corpus(self, corpus_name: str, description: str) -> str:
        """Create a new RAG corpus using high-level API"""
        try:
            # Initialize Vertex AI
            vertexai.init(project=self.project_id, location=self.location)
            
            # Check if corpus already exists
            existing_corpus_id = await self._find_existing_corpus(corpus_name)
            if existing_corpus_id:
                logger.info(f"📋 Using existing corpus: {corpus_name} with ID: {existing_corpus_id}")
                return existing_corpus_id
            
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
            logger.info(f"✅ Created new RAG corpus: {corpus_name} with ID: {corpus_id}")
            return corpus_id
            
        except Exception as e:
            logger.error(f"Failed to create RAG corpus: {e}")
            raise
    
    async def _find_existing_corpus(self, corpus_name: str) -> str:
        """Find existing corpus by name"""
        try:
            vertexai.init(project=self.project_id, location=self.location)
            
            # List all corpora in the project
            corpora = rag.list_corpora()
            
            for corpus in corpora:
                if corpus.display_name == corpus_name:
                    corpus_id = corpus.name.split("/")[-1]
                    logger.info(f"🔍 Found existing corpus: {corpus_name} (ID: {corpus_id})")
                    return corpus_id
            
            logger.info(f"🔍 No existing corpus found with name: {corpus_name}")
            return None
            
        except Exception as e:
            logger.warning(f"Could not check for existing corpora: {e}")
            return None
    
    async def upload_documents_to_corpus(self, corpus_id: str, gcs_uris: List[str]) -> bool:
        """Upload documents from GCS to a RAG corpus using high-level API"""
        try:
            corpus_name = f"projects/{self.project_id}/locations/{self.location}/ragCorpora/{corpus_id}"
            
            # Handle the 25-file limit by batching uploads
            max_files_per_batch = 20  # Stay under the 25-file limit
            total_imported = 0
            
            logger.info(f"🚀 Starting import of {len(gcs_uris)} files to corpus {corpus_id}...")
            logger.info("⏳ This may take several minutes depending on file count and size...")
            logger.info("📊 Processing: chunking, embedding, and indexing documents...")
            
            # Process files in batches
            for batch_start in range(0, len(gcs_uris), max_files_per_batch):
                batch_end = min(batch_start + max_files_per_batch, len(gcs_uris))
                batch_uris = gcs_uris[batch_start:batch_end]
                
                logger.info(f"📦 Processing batch {batch_start//max_files_per_batch + 1}: files {batch_start+1}-{batch_end}")
                
                # Import files using high-level API
                response = rag.import_files(
                    corpus_name=corpus_name,
                    paths=batch_uris,
                    transformation_config=rag.TransformationConfig(
                        rag.ChunkingConfig(chunk_size=512, chunk_overlap=100)
                    ),
                    max_embedding_requests_per_min=900,
                )
                
                total_imported += response.imported_rag_files_count
                logger.info(f"✅ Batch {batch_start//max_files_per_batch + 1}: imported {response.imported_rag_files_count} files")
            
            logger.info(f"✅ Successfully imported {total_imported} files total to corpus {corpus_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to upload documents to corpus: {e}")
            return False

# Global instances
dataset_processor = None
corpus_manager = None

async def initialize_dataset_processing(project_id: str, location: str = "us-east1") -> bool:
    """Initialize dataset processing and RAG corpus management"""
    global dataset_processor, corpus_manager
    
    try:
        # Initialize dataset processor
        dataset_processor = DatasetProcessor(project_id)
        
        # Initialize corpus manager (no client initialization needed with high-level API)
        corpus_manager = RAGCorpusManager(project_id, location)
        
        logger.info("Dataset processing system initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error initializing dataset processing: {e}")
        return False

async def process_and_upload_datasets() -> Dict[str, str]:
    """Process all datasets and upload them to RAG corpora"""
    global dataset_processor, corpus_manager
    
    if not dataset_processor or not corpus_manager:
        raise RuntimeError("Dataset processing system not initialized")
    
    try:
        corpus_ids = {}
        
        # Process academic success dataset
        academic_files = dataset_processor.process_academic_dataset(
            "/home/vatsal/Hackathons/GenAIExchange/FullStackR2/backend/rag_dataset/academic_success_knowledge_base.md"
        )
        
        if academic_files:
            academic_corpus_id = await corpus_manager.create_corpus(
                "academic-success-corpus",
                "RAG corpus for academic success and study support"
            )
            await corpus_manager.upload_documents_to_corpus(academic_corpus_id, academic_files)
            corpus_ids["study"] = academic_corpus_id
        
        # Process mental health knowledge base
        mental_health_files = dataset_processor.process_mental_health_dataset(
            "/home/vatsal/Hackathons/GenAIExchange/FullStackR2/backend/rag_dataset/mental_health_knowledge_base.md"
        )
        
        if mental_health_files:
            wellness_corpus_id = await corpus_manager.create_corpus(
                "mental-health-wellness-corpus",
                "RAG corpus for mental health and wellness support"
            )
            await corpus_manager.upload_documents_to_corpus(wellness_corpus_id, mental_health_files)
            corpus_ids["wellness"] = wellness_corpus_id
        
        # Process counsel chat JSON dataset (additional wellness content)
        counsel_chat_files = dataset_processor.process_counsel_chat_json_dataset(
            "/home/vatsal/Hackathons/GenAIExchange/FullStackR2/backend/rag_dataset/counsel_chat_250-tokens_full.json"
        )
        
        if counsel_chat_files and "wellness" in corpus_ids:
            # Add counsel chat data to existing wellness corpus
            await corpus_manager.upload_documents_to_corpus(corpus_ids["wellness"], counsel_chat_files)
            logger.info(f"Added {len(counsel_chat_files)} counsel chat batches to wellness corpus")
        
        logger.info(f"Successfully processed datasets and created corpora: {corpus_ids}")
        return corpus_ids
        
    except Exception as e:
        logger.error(f"Error processing and uploading datasets: {e}")
        return {}
