"""
OCR Engine - Tesseract-based text recognition with preprocessing
"""
import cv2
import numpy as np
import pytesseract
from typing import Tuple, Optional
import os
from src.processing.image_preprocessor import ImagePreprocessor

# Set Tesseract path for Windows
if os.name == 'nt':  # Windows
    # Try to find tesseract
    possible_paths = [
        r'C:\Program Files\Tesseract-OCR\tesseract.exe',
        r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
    ]
    
    tesseract_found = False
    for path in possible_paths:
        if os.path.exists(path):
            pytesseract.pytesseract.tesseract_cmd = path
            print(f"Tesseract found at: {path}")
            tesseract_found = True
            break
    
    if not tesseract_found:
        print("WARNING: Tesseract not found in standard locations.")
        print("Please ensure Tesseract is installed at C:\Program Files\Tesseract-OCR\\")

class OCREngine:
    """
    OCR engine optimized for scoreboard text recognition
    """
    
    def __init__(self):
        # Configure tesseract for digits and scoreboard characters
        self.custom_config = r'--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789:QOTPS1234 '
        self.preprocessor = ImagePreprocessor()
    
    def recognize(self, image: np.ndarray) -> Tuple[str, float]:
        """
        Recognize text in image
        Returns: (text, confidence)
        """
        if image is None or image.size == 0:
            return "", 0.0
        
        # Preprocess image
        processed = self._preprocess(image)
        
        # Run OCR
        try:
            # Get data including confidence
            data = pytesseract.image_to_data(
                processed, 
                config=self.custom_config,
                output_type=pytesseract.Output.DICT
            )
            
            # Extract text and average confidence
            text_parts = []
            confidences = []
            
            for i in range(len(data['text'])):
                if int(data['conf'][i]) > 0:  # Valid confidence
                    text_parts.append(data['text'][i])
                    confidences.append(float(data['conf'][i]))
            
            text = ''.join(text_parts).strip()
            avg_confidence = np.mean(confidences) / 100.0 if confidences else 0.0
            
            return text, avg_confidence
            
        except Exception as e:
            print(f"OCR Error: {e}")
            return "", 0.0
    
    def _preprocess(self, image: np.ndarray) -> np.ndarray:
        """
        Preprocess image for better OCR results
        Uses advanced preprocessing from ScoreSight
        """
        return self.preprocessor.preprocess(image, method='adaptive')
    
    def recognize_field(self, image: np.ndarray, field_type: str) -> Tuple[str, float]:
        """
        Recognize text with field-type specific processing
        """
        text, conf = self.recognize(image)
        
        # Clean up based on field type
        if field_type == "number":
            # Extract only digits
            text = ''.join(c for c in text if c.isdigit())
        elif field_type == "time":
            # Format as MM:SS
            text = self._format_time(text)
        
        return text, conf
    
    def _format_time(self, text: str) -> str:
        """Format time string to MM:SS"""
        # Remove all non-digit characters
        digits = ''.join(c for c in text if c.isdigit())
        
        if len(digits) >= 4:
            return f"{digits[-4:-2]}:{digits[-2:]}"
        elif len(digits) == 3:
            return f"{digits[0]}:{digits[1:]}"
        elif len(digits) == 2:
            return f"0:{digits}"
        
        return digits
