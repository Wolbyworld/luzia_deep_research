from typing import List, Dict
import re
from ..config import Config

def split_text_into_chunks(text: str, chunk_size: int = Config.CHUNK_SIZE) -> List[str]:
    """
    Split text into chunks of approximately equal size while preserving sentence boundaries
    """
    # Clean the text
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Split into sentences (basic splitting)
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    chunks = []
    current_chunk = []
    current_length = 0
    
    for sentence in sentences:
        sentence_length = len(sentence)
        
        # If single sentence is longer than chunk_size, split it
        if sentence_length > chunk_size:
            if current_chunk:
                chunks.append(' '.join(current_chunk))
                current_chunk = []
                current_length = 0
            
            # Split long sentence into parts
            words = sentence.split()
            temp_chunk = []
            temp_length = 0
            
            for word in words:
                word_length = len(word) + 1  # +1 for space
                if temp_length + word_length > chunk_size:
                    if temp_chunk:
                        chunks.append(' '.join(temp_chunk))
                    temp_chunk = [word]
                    temp_length = word_length
                else:
                    temp_chunk.append(word)
                    temp_length += word_length
            
            if temp_chunk:
                chunks.append(' '.join(temp_chunk))
            
        # If adding the sentence exceeds chunk_size, start a new chunk
        elif current_length + sentence_length > chunk_size:
            chunks.append(' '.join(current_chunk))
            current_chunk = [sentence]
            current_length = sentence_length
            
        # Add sentence to current chunk
        else:
            current_chunk.append(sentence)
            current_length += sentence_length
    
    # Add the last chunk if it exists
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    
    return chunks

class ContentProcessor:
    def __init__(self):
        self.chunk_size = Config.CHUNK_SIZE
        self.min_chunk_length = Config.MIN_CHUNK_LENGTH
        self.chunk_overlap = Config.CHUNK_OVERLAP
        
    def process_contents(self, contents: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Process a list of content dictionaries and chunk their content
        """
        processed_contents = []
        
        for content in contents:
            if not content.get("content"):
                continue
                
            chunks = split_text_into_chunks(content["content"], self.chunk_size)
            
            # Create a new content entry for each chunk
            for chunk in chunks:
                if len(chunk.strip()) >= self.min_chunk_length:  # Minimum chunk size
                    processed_contents.append({
                        "title": content["title"],
                        "content": chunk,
                        "url": content["url"]
                    })
                
        return processed_contents
