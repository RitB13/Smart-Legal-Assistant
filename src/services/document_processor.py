import logging
import PyPDF2
import json
import os
import tempfile
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """
    Process uploaded documents (PDF, DOCX, images) and extract text.
    """
    
    def __init__(self):
        self.supported_extensions = {'.pdf', '.docx', '.doc', '.jpg', '.jpeg', '.png', '.txt'}
    
    def process_file(self, file_path: str) -> str:
        """
        Extract text from uploaded file.
        
        Args:
            file_path: Path to the uploaded file
            
        Returns:
            Extracted text content
            
        Raises:
            ValueError: If file type is not supported
        """
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext not in self.supported_extensions:
            raise ValueError(f"Unsupported file type: {file_ext}")
        
        if file_ext == '.pdf':
            return self._extract_from_pdf(file_path)
        elif file_ext in {'.docx', '.doc'}:
            return self._extract_from_docx(file_path)
        elif file_ext in {'.jpg', '.jpeg', '.png'}:
            return self._extract_from_image(file_path)
        elif file_ext == '.txt':
            return self._extract_from_text(file_path)
        else:
            raise ValueError(f"Cannot process file type: {file_ext}")
    
    def _extract_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF file."""
        try:
            text = []
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text.append(page.extract_text())
            
            extracted = '\n'.join(text)
            logger.info(f"Extracted {len(extracted)} characters from PDF")
            return extracted
            
        except Exception as e:
            logger.error(f"Error extracting from PDF: {str(e)}", exc_info=True)
            raise ValueError(f"Could not extract text from PDF: {str(e)}")
    
    def _extract_from_docx(self, file_path: str) -> str:
        """Extract text from DOCX/DOC file."""
        try:
            # For DOCX, we'll use python-docx library
            from docx import Document
            
            doc = Document(file_path)
            text = '\n'.join([paragraph.text for paragraph in doc.paragraphs])
            
            logger.info(f"Extracted {len(text)} characters from DOCX")
            return text
            
        except ImportError:
            logger.error("python-docx not installed. Install with: pip install python-docx")
            raise ValueError("DOCX processing requires python-docx library")
        except Exception as e:
            logger.error(f"Error extracting from DOCX: {str(e)}", exc_info=True)
            raise ValueError(f"Could not extract text from DOCX: {str(e)}")
    
    def _extract_from_image(self, file_path: str) -> str:
        """Extract text from image using OCR."""
        try:
            # For images, we'll use pytesseract for OCR
            import pytesseract
            from PIL import Image
            
            image = Image.open(file_path)
            text = pytesseract.image_to_string(image)
            
            logger.info(f"Extracted {len(text)} characters from image using OCR")
            return text
            
        except ImportError:
            logger.error("pytesseract/Pillow not installed. Install with: pip install pytesseract pillow")
            raise ValueError("Image OCR requires pytesseract and Pillow libraries")
        except Exception as e:
            logger.error(f"Error extracting from image: {str(e)}", exc_info=True)
            raise ValueError(f"Could not extract text from image: {str(e)}")
    
    def _extract_from_text(self, file_path: str) -> str:
        """Extract text from plain text file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                text = file.read()
            
            logger.info(f"Extracted {len(text)} characters from text file")
            return text
            
        except UnicodeDecodeError:
            # Try with different encoding
            with open(file_path, 'r', encoding='latin-1') as file:
                text = file.read()
            return text
        except Exception as e:
            logger.error(f"Error extracting from text file: {str(e)}", exc_info=True)
            raise ValueError(f"Could not read text file: {str(e)}")
