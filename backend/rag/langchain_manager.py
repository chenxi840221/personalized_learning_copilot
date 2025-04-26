# backend/rag/langchain_manager.py
"""
LangChain integration for the Personalized Learning Co-pilot.
This module provides a simplified interface to LangChain components
with Azure OpenAI integration and handles all vector operations.
"""

import logging
from typing import List, Dict, Any, Optional, Union
import os
import sys
import json
import uuid
from datetime import datetime

# Fix import paths for relative imports
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(backend_dir)
sys.path.insert(0, project_root)  # Add project root to path

from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from langchain_community.vectorstores import AzureSearch
from langchain.chains import ConversationalRetrievalChain, LLMChain
from langchain.memory import ConversationBufferMemory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_text_splitters import RecursiveCharacterTextSplitter

from backend.config.settings import Settings
import aiohttp

# Initialize settings
settings = Settings()

# Initialize logger
logger = logging.getLogger(__name__)

class LangChainManager:
    """
    Manager for LangChain components using Azure OpenAI.
    Provides access to language models, embeddings, and vector stores.
    """
    
    def __init__(self):
        """Initialize the LangChain manager with configured settings."""
        self.llm = None
        self.embeddings = None
        self.vector_store = None
        self.retriever = None
        self.conversation_chain = None
        self.conversation_memory = None
        self.azure_search_endpoint = settings.AZURE_SEARCH_ENDPOINT
        self.azure_search_key = settings.AZURE_SEARCH_KEY
        self.azure_search_index = settings.AZURE_SEARCH_INDEX_NAME
    
    def initialize(self):
        """Initialize LangChain components."""
        try:
            # Initialize Azure OpenAI LLM
            self.llm = AzureChatOpenAI(
                openai_api_version=settings.AZURE_OPENAI_API_VERSION,
                azure_deployment=settings.AZURE_OPENAI_DEPLOYMENT,
                azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
                api_key=settings.AZURE_OPENAI_KEY,
                temperature=0.7,
                streaming=True
            )
            
            # Initialize Azure OpenAI Embeddings
            self.embeddings = AzureOpenAIEmbeddings(
                openai_api_version=settings.AZURE_OPENAI_API_VERSION,
                azure_deployment=settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
                azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
                api_key=settings.AZURE_OPENAI_KEY,
            )
            
            # Initialize conversation memory
            self.conversation_memory = ConversationBufferMemory(
                memory_key="chat_history",
                return_messages=True
            )
            
            # Setup Azure AI Search vector store if settings are available
            if self.azure_search_endpoint and self.azure_search_key:
                self.vector_store = AzureSearch(
                    azure_search_endpoint=self.azure_search_endpoint,
                    azure_search_key=self.azure_search_key,
                    index_name=self.azure_search_index,
                    embedding_function=self.embeddings.embed_query,
                    vector_field_name="embedding",
                    text_field_name="page_content"
                )
                
                # Create retriever
                self.retriever = self.vector_store.as_retriever(
                    search_kwargs={"k": 5}
                )
                
                # Initialize the RAG conversation chain
                self.conversation_chain = ConversationalRetrievalChain.from_llm(
                    llm=self.llm,
                    retriever=self.retriever,
                    memory=self.conversation_memory
                )
                
            logger.info("LangChain components initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing LangChain components: {e}")
            raise
    
    async def generate_completion(
        self, 
        prompt: str, 
        system_message: str = "You are a helpful educational assistant.",
        temperature: float = 0.7
    ) -> str:
        """
        Generate text completion using Azure OpenAI.
        """
        if not self.llm:
            self.initialize()
            
        try:
            # Setup chat messages
            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ]
            
            # Generate response
            response = await self.llm.ainvoke(messages)
            return response.content
            
        except Exception as e:
            logger.error(f"Error generating completion: {e}")
            return f"Error generating response: {str(e)}"
    
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for text using LangChain's embedding model.
        """
        if not self.embeddings:
            self.initialize()
            
        try:
            # Generate embedding
            embedding = await self.embeddings.aembed_query(text)
            return embedding
            
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            # Return an empty embedding of the correct dimension
            return [0.0] * 1536  # Default dimension for text-embedding-ada-002
    
    async def add_documents(self, texts: List[str], metadatas: Optional[List[Dict[str, Any]]] = None) -> bool:
        """
        Add documents to the vector store, using a minimal approach with only essential fields.
        """
        if not self.azure_search_endpoint or not self.azure_search_key:
            logger.error("Azure Search settings not available")
            return False
        
        try:
            # Create minimal documents with only essential fields
            documents = []
            
            for i, text in enumerate(texts):
                # Create a unique ID
                doc_id = str(uuid.uuid4())
                
                # Get embedding
                embedding = await self.generate_embedding(text)
                
                # Create a minimal document with just the essential fields
                doc = {
                    "@search.action": "upload",
                    "id": doc_id,
                    "page_content": text,
                    "embedding": embedding,
                    "title": f"Document {i+1}",
                    "subject": "General",
                    "content_type": "article",
                    "created_at": datetime.utcnow().isoformat() + "Z",
                    "updated_at": datetime.utcnow().isoformat() + "Z"
                }
                
                # Add only a subset of metadata fields that are known to be in the schema
                if metadatas and i < len(metadatas):
                    metadata = metadatas[i]
                    
                    # Add safe fields
                    for field in ["title", "description", "subject", "content_type", "difficulty_level", "url"]:
                        if field in metadata and metadata[field] is not None:
                            doc[field] = metadata[field]
                    
                    # Handle topics and keywords as arrays
                    for array_field in ["topics", "keywords"]:
                        if array_field in metadata and metadata[array_field] is not None:
                            if isinstance(metadata[array_field], list):
                                doc[array_field] = metadata[array_field]
                            elif isinstance(metadata[array_field], str):
                                doc[array_field] = [metadata[array_field]]
                    
                    # Handle grade_level as array of integers
                    if "grade_level" in metadata and metadata["grade_level"] is not None:
                        if isinstance(metadata["grade_level"], list):
                            doc["grade_level"] = [int(g) for g in metadata["grade_level"] if isinstance(g, (int, str)) and str(g).isdigit()]
                        elif isinstance(metadata["grade_level"], (int, str)) and str(metadata["grade_level"]).isdigit():
                            doc["grade_level"] = [int(metadata["grade_level"])]
                    
                    # Handle duration_minutes as integer
                    if "duration_minutes" in metadata and metadata["duration_minutes"] is not None:
                        try:
                            doc["duration_minutes"] = int(metadata["duration_minutes"])
                        except (ValueError, TypeError):
                            pass
                
                documents.append(doc)
            
            # Index documents using the Azure Search REST API
            async with aiohttp.ClientSession() as session:
                # Format URL for batch upload
                url = f"{self.azure_search_endpoint}/indexes/{self.azure_search_index}/docs/index?api-version=2023-11-01"
                
                # Set headers
                headers = {
                    "Content-Type": "application/json",
                    "api-key": self.azure_search_key
                }
                
                # Prepare payload
                payload = {"value": documents}
                
                # Log sample document (exclude embedding for readability)
                if documents:
                    sample_doc = {k: ("..." if k == "embedding" else v) for k, v in documents[0].items()}
                    logger.info(f"Indexing document sample: {json.dumps(sample_doc, default=str)}")
                
                # Make the request
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status == 200 or response.status == 201:
                        logger.info(f"Successfully indexed {len(documents)} documents")
                        return True
                    else:
                        response_text = await response.text()
                        logger.error(f"Error indexing documents: {response.status} - {response_text}")
                        return False
        
        except Exception as e:
            logger.error(f"Error adding documents to vector store: {e}")
            return False
    
    async def search_documents(self, query: str, filter: Optional[str] = None, k: int = 5) -> List[Document]:
        """
        Search for documents using a query string.
        """
        if not self.vector_store:
            self.initialize()
            if not self.vector_store:
                logger.error("Vector store not initialized")
                return []
            
        try:
            # Generate embedding for the query
            embedding = await self.generate_embedding(query)
            
            # Search using REST API if the query is empty (filter-only search)
            if not query and filter:
                return await self._search_by_filter(filter, k)
            
            # Search for documents with vector similarity
            search_kwargs = {"k": k}
            if filter:
                search_kwargs["filter"] = filter
                
            # Use the existing vector store for search
            documents = self.vector_store.similarity_search_by_vector(
                embedding, 
                **search_kwargs
            )
            
            return documents
            
        except Exception as e:
            logger.error(f"Error searching documents: {e}")
            return []
    
    async def _search_by_filter(self, filter: str, k: int = 5) -> List[Document]:
        """
        Perform a search using only a filter expression.
        """
        try:
            async with aiohttp.ClientSession() as session:
                # Format URL for search
                url = f"{self.azure_search_endpoint}/indexes/{self.azure_search_index}/docs/search?api-version=2023-11-01"
                
                # Set headers
                headers = {
                    "Content-Type": "application/json",
                    "api-key": self.azure_search_key
                }
                
                # Prepare payload
                payload = {
                    "filter": filter,
                    "top": k,
                    "select": "id,page_content,title,description,subject,content_type,difficulty_level,grade_level,url"
                }
                
                # Make the request
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        documents = []
                        
                        # Convert results to Document objects
                        for item in result.get("value", []):
                            # Extract page_content
                            page_content = item.pop("page_content", "")
                            
                            # Use remaining fields as metadata
                            metadata = {k: v for k, v in item.items() if k != "@search.score"}
                            
                            # Create Document object
                            doc = Document(page_content=page_content, metadata=metadata)
                            documents.append(doc)
                        
                        return documents
                    else:
                        response_text = await response.text()
                        logger.error(f"Error in filter search: {response.status} - {response_text}")
                        return []
                        
        except Exception as e:
            logger.error(f"Error in filter search: {e}")
            return []
    
    async def process_document(self, document_path: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> bool:
        """
        Process a document and add it to the vector store.
        """
        try:
            from langchain_community.document_loaders import TextLoader
            
            # Load document
            loader = TextLoader(document_path)
            documents = loader.load()
            
            # Split text
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
            
            chunks = text_splitter.split_documents(documents)
            
            # Extract texts and metadata
            texts = [doc.page_content for doc in chunks]
            metadatas = [doc.metadata for doc in chunks]
            
            # Add to vector store using our custom method
            return await self.add_documents(texts, metadatas)
            
        except Exception as e:
            logger.error(f"Error processing document: {e}")
            return False
    
    async def generate_personalized_learning_plan(
        self,
        student_profile: Dict[str, Any],
        subject: str,
        available_content: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate a personalized learning plan using LangChain.
        """
        if not self.llm:
            self.initialize()
            
        try:
            # Format content resources for the prompt
            resources_text = ""
            for i, content in enumerate(available_content):
                resources_text += f"""
                Content {i+1}:
                - ID: {content.get('id', 'unknown')}
                - Title: {content.get('title', 'Untitled')}
                - Type: {content.get('content_type', 'unknown')}
                - Difficulty: {content.get('difficulty_level', 'unknown')}
                - Description: {content.get('description', 'No description')}
                """
                
            # Construct the prompt
            profile_text = f"""
            Student Profile:
            - Name: {student_profile.get('full_name', student_profile.get('username', 'Student'))}
            - Grade Level: {student_profile.get('grade_level', 'Unknown')}
            - Learning Style: {student_profile.get('learning_style', 'Mixed')}
            - Interests: {', '.join(student_profile.get('subjects_of_interest', []))}
            """
            
            prompt_template = f"""
            Create a personalized learning plan for the following student:
            
            {profile_text}
            
            The learning plan should focus on: {subject}
            
            Available resources:
            {resources_text}
            
            The learning plan should include:
            1. A title
            2. A brief description
            3. 4-5 learning activities that use the available resources
            4. Each activity should include a title, description, duration, and reference to a resource ID if applicable
            
            Format the response as JSON with the following structure:
            {{
                "title": "Learning Plan Title",
                "description": "Brief description of the plan",
                "subject": "{subject}",
                "activities": [
                    {{
                        "title": "Activity Title",
                        "description": "Activity description",
                        "content_id": "reference to resource ID or null",
                        "duration_minutes": time in minutes,
                        "order": order number
                    }}
                ]
            }}
            """
            
            # Create prompt template
            messages = [
                {"role": "system", "content": "You are an expert educational assistant that creates personalized learning plans."},
                {"role": "user", "content": prompt_template}
            ]
            
            # Generate learning plan
            response = await self.llm.ainvoke(messages)
            
            # Parse the JSON result
            import json
            try:
                # Extract JSON if it's within a code block
                result = response.content
                if "```json" in result:
                    json_start = result.find("```json") + 7
                    json_end = result.find("```", json_start)
                    result = result[json_start:json_end].strip()
                elif "```" in result:
                    json_start = result.find("```") + 3
                    json_end = result.find("```", json_start)
                    result = result[json_start:json_end].strip()
                    
                learning_plan = json.loads(result)
                return learning_plan
                
            except json.JSONDecodeError:
                logger.error(f"Error parsing learning plan JSON: {result}")
                # Return the raw text as a fallback
                return {
                    "title": f"{subject} Learning Plan",
                    "description": f"A learning plan for {subject}",
                    "subject": subject,
                    "raw_response": result,
                    "activities": []
                }
            
        except Exception as e:
            logger.error(f"Error generating learning plan: {e}")
            return {
                "title": f"{subject} Learning Plan",
                "description": f"An error occurred while generating the learning plan: {str(e)}",
                "subject": subject,
                "activities": []
            }

# Singleton instance
langchain_manager = None

def get_langchain_manager():
    """Get or create the LangChain manager singleton."""
    global langchain_manager
    if langchain_manager is None:
        langchain_manager = LangChainManager()
        langchain_manager.initialize()
    return langchain_manager