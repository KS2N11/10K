"""
Text processing utilities for parsing and chunking SEC filings.
"""
import re
from typing import List, Dict, Tuple
from bs4 import BeautifulSoup
from pathlib import Path

from ..utils.logging import setup_logger

logger = setup_logger(__name__)


class TextProcessor:
    """Utilities for processing SEC filing text."""
    
    # Common 10-K section patterns
    SECTION_PATTERNS = {
        "Item 1": r"(?:^|\n)\s*(?:ITEM|Item)\s+1\b[.\s]*(?!A\b)",
        "Item 1A": r"(?:^|\n)\s*(?:ITEM|Item)\s+1A\b",
        "Item 1B": r"(?:^|\n)\s*(?:ITEM|Item)\s+1B\b",
        "Item 2": r"(?:^|\n)\s*(?:ITEM|Item)\s+2\b",
        "Item 3": r"(?:^|\n)\s*(?:ITEM|Item)\s+3\b",
        "Item 4": r"(?:^|\n)\s*(?:ITEM|Item)\s+4\b",
        "Item 5": r"(?:^|\n)\s*(?:ITEM|Item)\s+5\b",
        "Item 6": r"(?:^|\n)\s*(?:ITEM|Item)\s+6\b",
        "Item 7": r"(?:^|\n)\s*(?:ITEM|Item)\s+7\b[.\s]*(?!A\b)",
        "Item 7A": r"(?:^|\n)\s*(?:ITEM|Item)\s+7A\b",
        "Item 8": r"(?:^|\n)\s*(?:ITEM|Item)\s+8\b",
        "Item 9": r"(?:^|\n)\s*(?:ITEM|Item)\s+9\b[.\s]*(?!A\b|B\b)",
        "Item 9A": r"(?:^|\n)\s*(?:ITEM|Item)\s+9A\b",
        "Item 9B": r"(?:^|\n)\s*(?:ITEM|Item)\s+9B\b",
        "Item 10": r"(?:^|\n)\s*(?:ITEM|Item)\s+10\b",
        "Item 11": r"(?:^|\n)\s*(?:ITEM|Item)\s+11\b",
        "Item 12": r"(?:^|\n)\s*(?:ITEM|Item)\s+12\b",
        "Item 13": r"(?:^|\n)\s*(?:ITEM|Item)\s+13\b",
        "Item 14": r"(?:^|\n)\s*(?:ITEM|Item)\s+14\b",
        "Item 15": r"(?:^|\n)\s*(?:ITEM|Item)\s+15\b",
    }
    
    @staticmethod
    def html_to_text(html_content: str) -> str:
        """
        Convert HTML to clean text.
        
        Args:
            html_content: HTML content as string
        
        Returns:
            Cleaned text content
        """
        soup = BeautifulSoup(html_content, "lxml")
        
        # Remove script and style elements
        for element in soup(["script", "style"]):
            element.decompose()
        
        # Get text
        text = soup.get_text(separator="\n")
        
        # Clean up whitespace
        lines = [line.strip() for line in text.splitlines()]
        text = "\n".join(line for line in lines if line)
        
        return text
    
    @staticmethod
    def extract_sections(text: str) -> Dict[str, str]:
        """
        Extract major sections from 10-K text.
        
        Args:
            text: Full 10-K text
        
        Returns:
            Dict mapping section names to their content
        """
        sections = {}
        
        # Find all section positions
        section_positions = []
        for section_name, pattern in TextProcessor.SECTION_PATTERNS.items():
            matches = list(re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE))
            if matches:
                # Take the first match for each section
                pos = matches[0].start()
                section_positions.append((pos, section_name))
        
        # Sort by position
        section_positions.sort()
        
        # Extract content between sections
        for i, (pos, section_name) in enumerate(section_positions):
            if i + 1 < len(section_positions):
                next_pos = section_positions[i + 1][0]
                content = text[pos:next_pos].strip()
            else:
                content = text[pos:].strip()
            
            sections[section_name] = content
            logger.debug(f"Extracted {section_name}: {len(content)} chars")
        
        if not sections:
            logger.warning("No sections found, using full text as 'Full Document'")
            sections["Full Document"] = text
        
        return sections
    
    @staticmethod
    def chunk_text(
        text: str,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        section_name: str = "Unknown"
    ) -> List[Dict[str, any]]:
        """
        Split text into overlapping chunks.
        
        Args:
            text: Text to chunk
            chunk_size: Maximum characters per chunk
            chunk_overlap: Overlap between chunks
            section_name: Name of the section (for metadata)
        
        Returns:
            List of chunk dicts with text and metadata
        """
        chunks = []
        
        # Split into sentences (simple approach)
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        current_chunk = []
        current_length = 0
        chunk_index = 0
        
        for sentence in sentences:
            sentence_length = len(sentence)
            
            if current_length + sentence_length > chunk_size and current_chunk:
                # Save current chunk
                chunk_text = " ".join(current_chunk)
                chunks.append({
                    "text": chunk_text,
                    "metadata": {
                        "section": section_name,
                        "chunk_index": chunk_index,
                        "char_count": len(chunk_text)
                    }
                })
                
                # Start new chunk with overlap
                overlap_text = chunk_text[-chunk_overlap:] if len(chunk_text) > chunk_overlap else chunk_text
                overlap_sentences = overlap_text.split(". ")
                current_chunk = [s for s in overlap_sentences if s]
                current_length = sum(len(s) for s in current_chunk)
                chunk_index += 1
            
            current_chunk.append(sentence)
            current_length += sentence_length
        
        # Add final chunk
        if current_chunk:
            chunk_text = " ".join(current_chunk)
            chunks.append({
                "text": chunk_text,
                "metadata": {
                    "section": section_name,
                    "chunk_index": chunk_index,
                    "char_count": len(chunk_text)
                }
            })
        
        logger.info(f"Created {len(chunks)} chunks from {section_name}")
        return chunks
    
    @staticmethod
    def process_filing(
        file_path: Path,
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ) -> List[Dict[str, any]]:
        """
        Process a 10-K filing: HTML -> text -> sections -> chunks.
        
        Args:
            file_path: Path to the filing HTML file
            chunk_size: Maximum characters per chunk
            chunk_overlap: Overlap between chunks
        
        Returns:
            List of all chunks with metadata
        """
        logger.info(f"Processing filing: {file_path}")
        
        # Read file
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            html_content = f.read()
        
        # Convert to text
        text = TextProcessor.html_to_text(html_content)
        logger.info(f"Converted HTML to text: {len(text)} chars")
        
        # Extract sections
        sections = TextProcessor.extract_sections(text)
        logger.info(f"Extracted {len(sections)} sections")
        
        # Chunk each section
        all_chunks = []
        for section_name, section_text in sections.items():
            section_chunks = TextProcessor.chunk_text(
                section_text,
                chunk_size,
                chunk_overlap,
                section_name
            )
            all_chunks.extend(section_chunks)
        
        logger.info(f"Total chunks created: {len(all_chunks)}")
        return all_chunks
