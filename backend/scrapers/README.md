# Two-Step Education Resource Scraper

A robust, modular system for collecting educational content from the ABC Education website and indexing it for use in the Personalized Learning Co-pilot.

## Overview

This scraper has been refactored into a two-step process for better modularity and reliability:

1. **Indexing Step**: Discovers and catalogs educational resources across subjects, creating a comprehensive index of available content.
2. **Extraction Step**: Processes each resource in the index to extract detailed content (text, video, audio) and store it in the vector database.

This approach offers several advantages:
- Better fault tolerance (steps can be run independently)
- Progress tracking between steps
- Ability to verify the index before proceeding with content extraction
- Easier debugging and maintenance

## Components

### 1. Education Resource Indexer (`edu_resource_indexer.py`)

This component:
- Navigates to subject pages on the ABC Education website
- Identifies educational resources (articles, videos, interactive content)
- Extracts basic metadata (title, URL, subject)
- Creates a structured index of all discovered resources
- Handles pagination via "Load More" buttons
- Saves the index as JSON for verification

### 2. Content Extractor (`content_extractor.py`)

This component:
- Reads the resource index created in step 1
- Visits each resource URL
- Extracts detailed content based on resource type (text, video, audio)
- Determines content properties (difficulty, grade level, topics)
- Processes content for vector embedding
- Stores enriched content in the vector store for recommendation

### 3. Two-Step Scraper (`two_step_scraper.py`)

A unified interface that:
- Coordinates the indexing and extraction steps
- Provides command-line arguments for flexibility
- Handles logging and error reporting
- Outputs summary statistics

## Setup

### Prerequisites

- Python 3.8+
- Azure OpenAI access (for embeddings)
- Azure AI Search service (for vector storage)

### Installation

1. Install dependencies:

```bash
pip install -r requirements.txt