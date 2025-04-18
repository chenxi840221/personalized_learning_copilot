# Personalized Learning Co-pilot POC

A proof-of-concept for a Personalized Learning Co-pilot that provides tailored educational content and learning plans based on student profiles using Retrieval-Augmented Generation (RAG).

## Overview

This project implements a personalized learning system that:
- Scrapes educational content from ABC Education (https://www.abc.net.au/education/subjects-and-topics)
- Creates vector embeddings of educational content for semantic search
- Generates personalized learning plans using LLMs
- Recommends relevant educational resources based on student profiles
- Provides a user-friendly interface for students to access content and track progress

## Architecture

The system consists of:

1. **Backend**: FastAPI application with LangChain for RAG implementation
2. **Frontend**: React application with TailwindCSS for UI
3. **Database**: MongoDB for storing user data, content, and learning plans
4. **Vector Store**: FAISS for efficient similarity search of content embeddings
5. **LLM Integration**: Azure OpenAI integration for content generation and embeddings

## Setup and Installation

### Prerequisites

- Docker and Docker Compose
- Python 3.8+
- Node.js 16+
- Azure OpenAI Service API access

### Environment Setup

1. Clone the repository
```bash
git clone https://github.com/yourusername/personalized-learning-copilot.git
cd personalized-learning-copilot
```

2. Set up environment variables
```bash
cp .env.example .env
# Edit .env with your Azure OpenAI credentials
```

3. Generate file structure (if starting from scratch)
```bash
chmod +x file_structure.sh
./file_structure.sh
```

### Running with Docker

Start the entire application stack using Docker Compose:

```bash
docker-compose up -d
```

This will start:
- Backend API on port 8000
- Frontend on port 3000
- MongoDB on port 27017
- Qdrant vector database on port 6333

### Manual Setup (Development)

#### Backend

1. Set up a Python virtual environment
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. Run the backend server
```bash
python -m uvicorn app:app --reload
```

#### Frontend

1. Install dependencies
```bash
cd frontend
npm install
```

2. Run the development server
```bash
npm start
```

#### Initial Data

To populate the database with initial data from ABC Education:

```bash
# Make sure the backend is running
cd backend
python -m scrapers.abc_edu_scraper
```

## Usage

1. Access the application at http://localhost:3000
2. Register a new student account
3. Browse available content or get recommendations
4. Create personalized learning plans
5. Track your progress through learning activities

## API Documentation

Once the backend is running, you can access the FastAPI documentation at:
- http://localhost:8000/docs (Swagger UI)
- http://localhost:8000/redoc (ReDoc)

## Project Structure

```
personalized_learning_copilot/
├── backend/                  # FastAPI backend
│   ├── api/                  # API routes and endpoints
│   ├── auth/                 # Authentication logic
│   ├── models/               # Pydantic models
│   ├── rag/                  # RAG implementation
│   ├── utils/                # Utility functions
│   ├── config/               # Configuration
│   ├── data/                 # Data storage
│   └── scrapers/             # Web scrapers
├── frontend/                 # React frontend
│   ├── src/
│   │   ├── components/       # React components
│   │   ├── pages/            # Page components
│   │   ├── services/         # API services
│   │   ├── utils/            # Utility functions
│   │   ├── hooks/            # Custom React hooks
│   │   └── context/          # React context
│   └── public/               # Static assets
└── deployment/               # Deployment configuration
```

## Technical Details

### RAG Implementation

The system uses Retrieval-Augmented Generation to:
1. Create embeddings for educational content using Azure OpenAI embeddings
2. Store embeddings in a vector database (FAISS)
3. Retrieve relevant content based on semantic similarity to user queries and profiles
4. Generate personalized learning plans using retrieved content and LLM

### Authentication

The system implements JWT-based authentication to:
1. Register and authenticate users
2. Secure API endpoints
3. Maintain user sessions

### Personalization Features

- Learning style detection and adaptation
- Subject interest-based recommendations
- Grade-level appropriate content filtering
- Progress tracking and analytics

## Future Enhancements

- Integration with more content sources
- Advanced analytics for learning patterns
- Gamification features for improved engagement
- Mobile application for on-the-go learning
- Expanded subject coverage

## License

This project is licensed under the MIT License - see the LICENSE file for details.# personalized_learning_copilot
# personalized_learning_copilot
