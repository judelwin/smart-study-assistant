import re
import logging
from typing import List

logger = logging.getLogger(__name__)

def split_into_sentences(text: str) -> List[str]:
    """Split text into sentences using regex."""
    # Simple sentence splitter (can be improved with nltk or spacy)
    sentence_endings = re.compile(r'(?<=[.!?])\s+')
    sentences = sentence_endings.split(text.strip())
    return [s.strip() for s in sentences if s.strip()]

def chunk_text(text: str, chunk_size: int = 2500, overlap: int = 250) -> List[str]:
    """
    Split text into chunks optimized for RAG and OpenAI API.
    
    Args:
        text: Input text to chunk
        chunk_size: Target chunk size in characters (default 2500 for scalability)
        overlap: Overlap between chunks in characters (default 250)
    
    Returns:
        List of text chunks
    """
    try:
        # Clean and normalize text
        text = text.strip()
        if not text:
            return []
        
        logger.info(f"Text has {len(text)} characters")
        
        # If text is smaller than chunk size, return as single chunk
        if len(text) <= chunk_size:
            logger.info(f"Text fits in single chunk ({len(text)} chars), returning as-is")
            return [text]
        
        # Split into sentences first to preserve semantic boundaries
        sentences = split_into_sentences(text)
        logger.info(f"Split into {len(sentences)} sentences")
        
        chunks = []
        current_chunk = ""
        sentence_index = 0
        
        while sentence_index < len(sentences):
            sentence = sentences[sentence_index]
            
            # Check if adding this sentence would exceed chunk size
            if len(current_chunk) + len(sentence) + 1 <= chunk_size:
                # Add sentence to current chunk
                if current_chunk:
                    current_chunk += " " + sentence
                else:
                    current_chunk = sentence
                sentence_index += 1
            else:
                # Current chunk is full, save it and start new chunk
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    logger.info(f"Created chunk {len(chunks)} with {len(current_chunk)} chars")
                    
                    # Start new chunk with overlap from previous chunk
                    if overlap > 0 and chunks:
                        # Find last sentence boundary within overlap
                        overlap_text = chunks[-1][-overlap:] if len(chunks[-1]) > overlap else chunks[-1]
                        # Find last sentence in overlap
                        overlap_sentences = split_into_sentences(overlap_text)
                        if overlap_sentences:
                            current_chunk = overlap_sentences[-1]
                        else:
                            current_chunk = ""
                    else:
                        current_chunk = ""
                else:
                    # Single sentence is too long, split it
                    if len(sentence) > chunk_size:
                        # Split long sentence at word boundaries
                        words = sentence.split()
                        current_chunk = ""
                        for word in words:
                            if len(current_chunk) + len(word) + 1 <= chunk_size:
                                if current_chunk:
                                    current_chunk += " " + word
                                else:
                                    current_chunk = word
                            else:
                                if current_chunk:
                                    chunks.append(current_chunk.strip())
                                    logger.info(f"Created chunk {len(chunks)} with {len(current_chunk)} chars")
                                current_chunk = word
                        sentence_index += 1
                    else:
                        # Start new chunk with this sentence
                        current_chunk = sentence
                        sentence_index += 1
        
        # Add the last chunk if it has content
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
            logger.info(f"Created chunk {len(chunks)} with {len(current_chunk)} chars")
        
        # Log chunk statistics
        if chunks:
            chunk_sizes = [len(chunk) for chunk in chunks]
            avg_size = sum(chunk_sizes) / len(chunk_sizes)
            logger.info(f"Total chunks created: {len(chunks)}")
            logger.info(f"Average chunk size: {avg_size:.0f} chars")
            logger.info(f"Chunk size range: {min(chunk_sizes)} - {max(chunk_sizes)} chars")
        
        return chunks
        
    except Exception as e:
        logger.error(f"Error in chunk_text: {e}")
        # Return the original text as a single chunk if chunking fails
        return [text] 