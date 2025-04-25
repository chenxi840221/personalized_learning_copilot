# backend/rag/langchain_manager.py
"""
LangChain integration for the Personalized Learning Co-pilot.
This module provides a simplified interface to LangChain components
with Azure OpenAI integration.
"""

import logging
from typing import List, Dict, Any, Optional, Union
import os

from langchain.chat_models import AzureChatOpenAI
from langchain.embeddings import AzureOpenAIEmbeddings
from langchain.schema import HumanMessage, SystemMessage
from langchain.chains import ConversationalRetrievalChain, LLMChain
from langchain.memory import ConversationBufferMemory
from langchain.retrievers import AzureAISearchRetriever
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.callbacks.manager import CallbackManager
from langchain.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.document_loaders import TextLoader

from config.settings import Settings

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
        self.retriever = None
        self.conversation_chain = None
        self.conversation_memory = None
        self.vector_store = None
    
    def initialize(self):
        """Initialize LangChain components."""
        try:
            # Initialize Azure OpenAI LLM
            self.llm = AzureChatOpenAI(
                openai_api_version=settings.AZURE_OPENAI_API_VERSION,
                azure_deployment=settings.AZURE_OPENAI_DEPLOYMENT,
                azure_endpoint=settings.get_openai_endpoint(),
                openai_api_key=settings.get_openai_key(),
                temperature=0.7,
                streaming=True
            )
            
            # Initialize Azure OpenAI Embeddings
            self.embeddings = AzureOpenAIEmbeddings(
                openai_api_version=settings.AZURE_OPENAI_API_VERSION,
                azure_deployment=settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
                azure_endpoint=settings.get_openai_endpoint(),
                openai_api_key=settings.get_openai_key(),
            )
            
            # Initialize conversation memory
            self.conversation_memory = ConversationBufferMemory(
                memory_key="chat_history",
                return_messages=True
            )
            
            # Setup Azure AI Search retriever if settings are available
            if settings.AZURE_SEARCH_ENDPOINT and settings.AZURE_SEARCH_KEY:
                self.retriever = AzureAISearchRetriever(
                    service_name=settings.AZURE_SEARCH_ENDPOINT.replace("https://", "").replace(".search.windows.net", ""),
                    index_name=settings.AZURE_SEARCH_INDEX_NAME,
                    api_key=settings.AZURE_SEARCH_KEY,
                    content_key="content_text",
                    embedding_function=self.embeddings.embed_query
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
        
        Args:
            prompt: User prompt
            system_message: System message to set the context
            temperature: Temperature for generation (0-1)
            
        Returns:
            Generated text
        """
        if not self.llm:
            self.initialize()
            
        try:
            # Setup chat messages
            messages = [
                SystemMessage(content=system_message),
                HumanMessage(content=prompt)
            ]
            
            # Generate response
            response = await self.llm.agenerate([messages])
            
            # Extract and return the content
            if response and response.generations and response.generations[0]:
                return response.generations[0][0].text
            
            return "I apologize, but I couldn't generate a response."
            
        except Exception as e:
            logger.error(f"Error generating completion: {e}")
            return f"Error generating response: {str(e)}"
    
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for text using Azure OpenAI.
        
        Args:
            text: Text to embed
            
        Returns:
            List of embedding values
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
    
    async def generate_rag_response(
        self,
        query: str,
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Generate a response using Retrieval-Augmented Generation (RAG).
        
        Args:
            query: User query
            chat_history: Optional chat history
            
        Returns:
            Dictionary with response and source documents
        """
        if not self.conversation_chain:
            self.initialize()
            if not self.conversation_chain:
                # Fall back to regular completion if RAG is not available
                response = await self.generate_completion(query)
                return {
                    "answer": response,
                    "source_documents": []
                }
                
        try:
            # Format chat history if provided
            formatted_history = []
            if chat_history:
                for message in chat_history:
                    if message.get("role") == "user":
                        formatted_history.append((message.get("content"), ""))
                    elif message.get("role") == "assistant":
                        if formatted_history:
                            formatted_history[-1] = (formatted_history[-1][0], message.get("content"))
                        else:
                            formatted_history.append(("", message.get("content")))
            
            # Generate RAG response
            result = await self.conversation_chain.arun(
                question=query,
                chat_history=formatted_history
            )
            
            # Extract source documents
            source_documents = []
            if hasattr(result, "source_documents"):
                source_documents = result.source_documents
            
            return {
                "answer": result,
                "source_documents": source_documents
            }
            
        except Exception as e:
            logger.error(f"Error generating RAG response: {e}")
            # Fall back to regular completion
            response = await self.generate_completion(query)
            return {
                "answer": response,
                "source_documents": []
            }
    
    async def create_vector_store_from_texts(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None
    ) -> Any:
        """
        Create an in-memory vector store from texts.
        
        Args:
            texts: List of text content
            metadatas: Optional metadata for each text
            
        Returns:
            FAISS vector store
        """
        if not self.embeddings:
            self.initialize()
            
        try:
            # Create vector store
            self.vector_store = FAISS.from_texts(
                texts=texts,
                embedding=self.embeddings,
                metadatas=metadatas
            )
            
            return self.vector_store
            
        except Exception as e:
            logger.error(f"Error creating vector store: {e}")
            return None
    
    async def process_document(self, document_path: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> Any:
        """
        Process a document and create a vector store from its content.
        
        Args:
            document_path: Path to the document
            chunk_size: Size of text chunks for splitting
            chunk_overlap: Overlap between chunks
            
        Returns:
            FAISS vector store
        """
        if not self.embeddings:
            self.initialize()
            
        try:
            # Load document
            loader = TextLoader(document_path)
            documents = loader.load()
            
            # Split text
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
            
            texts = text_splitter.split_documents(documents)
            
            # Create vector store
            self.vector_store = FAISS.from_documents(texts, self.embeddings)
            
            return self.vector_store
            
        except Exception as e:
            logger.error(f"Error processing document: {e}")
            return None
    
    async def generate_personalized_learning_plan(
        self,
        student_profile: Dict[str, Any],
        subject: str,
        available_content: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate a personalized learning plan using LangChain.
        
        Args:
            student_profile: Student information
            subject: Subject for the learning plan
            available_content: Available content resources
            
        Returns:
            Personalized learning plan
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
            
            prompt = f"""
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
            prompt_template = ChatPromptTemplate.from_messages([
                SystemMessage(content="You are an expert educational assistant that creates personalized learning plans."),
                HumanMessage(content=prompt)
            ])
            
            # Create chain
            chain = LLMChain(llm=self.llm, prompt=prompt_template)
            
            # Run chain
            result = await chain.arun({})
            
            # Parse the JSON result
            import json
            try:
                # Extract JSON if it's within a code block
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