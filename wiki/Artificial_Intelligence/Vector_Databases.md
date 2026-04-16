---
tags: [artificial_intelligence, databases, architecture, scalability]
date_created: 2026-04-16
sources:
  - "[[Akitando 148 - O que IAs podem fazer]] (Clipper)"
---
# Vector Databases

A **Vector Database** is a specialized storage system designed to manage and query data represented as multi-dimensional vectors, known as **Embeddings**. These databases are critical for modern [[AI_and_LLMs|AI applications]] that require semantic search and long-term memory.

## The Semantic Representation

### 1. Embeddings
An embedding is a vector (a list of numbers) that represents the semantic meaning of a data point (text, image, audio).
- **Dense Vectors**: Unlike traditional "sparse" keyword indices, embeddings capture relationships. For example, the vectors for "King" and "Queen" will be mathematically closer than "King" and "Apple."
- **Dimensions**: High-quality models typically use vectors with 384, 768, or 1536 dimensions.

### 2. Distance Metrics
The "similarity" between two vectors is calculated using mathematical metrics:
- **Cosine Similarity**: Measures the angle between vectors. Most common for text semantics.
- **Euclidean Distance (L2)**: Measures the straight-line distance between points.
- **Dot Product**: Measures the magnitude and direction of similarity.

## Retrieval-Augmented Generation (RAG)

LLMs have a finite **Context Window** (e.g., 2048 or 4096 tokens). RAG is a technique to bypass this limitation by "injecting" relevant knowledge into the prompt at runtime.

### The RAG Workflow:
1.  **Ingestion**: Documents are broken into "chunks," converted into embeddings, and stored in a Vector Database.
2.  **Querying**: When a user asks a question, the question is also converted into an embedding.
3.  **Retrieval**: The Vector Database performs a **Similarity Search** to find the most relevant chunks.
4.  **Augmentation**: The retrieved chunks are added to the LLM's prompt as "context."
5.  **Generation**: The LLM answers the question based on the provided context, reducing hallucinations.

## Key Technologies

### 1. Vector Search Libraries
- **FAISS (Facebook AI Similarity Search)**: An industry-standard C++ library for efficient similarity search.
- **HNSW (Hierarchical Navigable Small Worlds)**: A popular algorithm/graph structure for fast approximate nearest neighbor search.

### 2. Standalone Vector Databases
- **Pinecone**: A managed, cloud-native vector database.
- **Milvus**: An open-source, highly scalable vector database.
- **Weaviate**: A vector search engine with GraphQL and REST interfaces.
- **Chroma**: An open-source embedding database optimized for local AI workflows.

### 3. Integrated Solutions
Many traditional databases have added vector support:
- **pgvector**: An extension for [[PostgreSQL]] that allows storing and querying vectors.
- **RedisVSS**: Vector similarity search for Redis.

## See Also
- [[AI_and_LLMs]]
- [[Database_Fundamentals]]
- [[Complexity_and_Evolution]]
