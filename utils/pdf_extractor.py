"""
RegDelta PDF Text Extraction
Fallback extraction with PyMuPDF (primary) and pdfplumber (fallback)
"""

import logging
from pathlib import Path
from typing import Optional, Tuple
import re

logger = logging.getLogger(__name__)


def extract_text(pdf_path: Path, skip_on_error: bool = True) -> Tuple[Optional[str], str]:
    """
    Extract text from PDF using fallback strategy
    
    Args:
        pdf_path: Path to PDF file
        skip_on_error: If True, return partial results on error; if False, raise exception
    
    Returns:
        (extracted_text, extractor_used)
    """
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    extractors = [
        ('pymupdf', _extract_with_pymupdf),
        ('pdfplumber', _extract_with_pdfplumber)
    ]
    
    last_error = None
    
    for extractor_name, extractor_func in extractors:
        try:
            logger.info(f"Attempting extraction with {extractor_name}: {pdf_path.name}")
            text = extractor_func(pdf_path)
            
            if text and len(text.strip()) > 0:
                logger.info(f"Successfully extracted {len(text)} chars with {extractor_name}")
                return text, extractor_name
            else:
                logger.warning(f"{extractor_name} returned empty text")
                
        except Exception as e:
            last_error = e
            logger.warning(f"{extractor_name} failed: {str(e)}")
            continue
    
    # All extractors failed
    if skip_on_error:
        logger.error(f"All extractors failed for {pdf_path.name}, returning empty")
        return "", "none"
    else:
        raise RuntimeError(f"Failed to extract text from {pdf_path.name}") from last_error


def _extract_with_pymupdf(pdf_path: Path) -> str:
    """Extract text using PyMuPDF (fitz)"""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        raise ImportError("PyMuPDF not installed. Install with: pip install PyMuPDF")
    
    doc = fitz.open(pdf_path)
    text_parts = []
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        text_parts.append(page.get_text())
    
    doc.close()
    return "\n".join(text_parts)


def _extract_with_pdfplumber(pdf_path: Path) -> str:
    """Extract text using pdfplumber (fallback)"""
    try:
        import pdfplumber
    except ImportError:
        raise ImportError("pdfplumber not installed. Install with: pip install pdfplumber")
    
    text_parts = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)
    
    return "\n".join(text_parts)


def paragraphize(text: str, min_length: int = 50, max_length: int = 2000) -> list[str]:
    """
    Segment text into meaningful paragraphs for regulatory documents
    
    Args:
        text: Raw extracted text
        min_length: Minimum paragraph length in characters
        max_length: Maximum paragraph length (split if exceeded)
    
    Returns:
        List of paragraph strings
    """
    # First, normalize whitespace
    text = re.sub(r'\r\n', '\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)
    
    # Split on various section patterns common in regulatory docs
    # Patterns: "1.2.3 Title", "Requirement 1.1:", "Article 5:", etc.
    section_patterns = [
        r'\n(?=\d+\.\d+\.?\d*\s+[A-Z])',  # 1.2.3 Title
        r'\n(?=Requirement\s+\d+)',        # Requirement 1
        r'\n(?=Section\s+\d+)',            # Section 1
        r'\n(?=Article\s+\d+)',            # Article 1
        r'\n(?=\d+\.\s+[A-Z])',            # 1. Title
        r'\n(?=[A-Z][a-z]+\s+\d+:)',       # Clause 1:
        r'\n\n+'                            # Double newlines
    ]
    
    # Combine patterns and split
    combined_pattern = '|'.join(section_patterns)
    chunks = re.split(combined_pattern, text)
    
    paragraphs = []
    
    for chunk in chunks:
        chunk = chunk.strip()
        
        # Skip empty or very short chunks
        if len(chunk) < 10:
            continue
        
        # If chunk is too long, split by sentences
        if len(chunk) > max_length:
            # Split on sentence boundaries
            sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', chunk)
            current_para = []
            current_length = 0
            
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue
                
                # Add sentence to current paragraph
                current_para.append(sentence)
                current_length += len(sentence)
                
                # If paragraph is long enough, flush it
                if current_length >= min_length and current_length <= max_length:
                    para_text = ' '.join(current_para)
                    paragraphs.append(para_text)
                    current_para = []
                    current_length = 0
                elif current_length > max_length:
                    # Force flush even if not ideal
                    para_text = ' '.join(current_para)
                    paragraphs.append(para_text)
                    current_para = []
                    current_length = 0
            
            # Flush remaining sentences
            if current_para:
                para_text = ' '.join(current_para)
                if len(para_text) >= min_length:
                    paragraphs.append(para_text)
        else:
            # Chunk is reasonable size, add as-is if long enough
            if len(chunk) >= min_length:
                paragraphs.append(chunk)
    
    # If we got no paragraphs (very compact PDF), split by line breaks
    if not paragraphs:
        lines = text.split('\n')
        current_para = []
        current_length = 0
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            current_para.append(line)
            current_length += len(line)
            
            if current_length >= min_length:
                para_text = ' '.join(current_para)
                paragraphs.append(para_text)
                current_para = []
                current_length = 0
        
        # Flush remaining
        if current_para:
            para_text = ' '.join(current_para)
            if len(para_text) >= min_length:
                paragraphs.append(para_text)
    
    logger.info(f"Segmented text into {len(paragraphs)} paragraphs (min={min_length}, max={max_length})")
    return paragraphs


def extract_metadata(pdf_path: Path) -> dict:
    """Extract PDF metadata (title, author, creation date, etc.)"""
    try:
        import fitz
        doc = fitz.open(pdf_path)
        metadata = doc.metadata
        doc.close()
        return metadata
    except Exception as e:
        logger.warning(f"Failed to extract metadata: {e}")
        return {}


def check_extractors_available() -> dict:
    """Check which PDF extractors are available"""
    available = {}
    
    try:
        import fitz
        available['pymupdf'] = True
    except ImportError:
        available['pymupdf'] = False
    
    try:
        import pdfplumber
        available['pdfplumber'] = True
    except ImportError:
        available['pdfplumber'] = False
    
    return available
