"""
Image Preprocessing - Borrowed from ScoreSight techniques
Advanced binarization and filtering for scoreboard OCR
"""
import cv2
import numpy as np
from typing import Tuple

class ImagePreprocessor:
    """
    Advanced image preprocessing optimized for scoreboard text
    Based on ScoreSight processing pipeline
    """
    
    def __init__(self):
        self.prev_frame = None
    
    def preprocess(self, image: np.ndarray, method: str = 'adaptive') -> np.ndarray:
        """
        Main preprocessing pipeline
        
        Args:
            image: Input image (BGR)
            method: 'adaptive', 'otsu', or 'local'
        
        Returns:
            Preprocessed binary image
        """
        if image is None or image.size == 0:
            return image
        
        # Step 1: Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # Step 2: Resize if too small (helps OCR)
        h, w = gray.shape
        if h < 40 or w < 40:
            scale = max(80 / h, 80 / w)
            new_w = int(w * scale)
            new_h = int(h * scale)
            gray = cv2.resize(gray, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
        
        # Step 3: Denoise
        denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
        
        # Step 4: Binarization
        if method == 'adaptive':
            binary = self._adaptive_threshold(denoised)
        elif method == 'otsu':
            binary = self._otsu_threshold(denoised)
        elif method == 'local':
            binary = self._local_threshold(denoised)
        else:
            binary = self._adaptive_threshold(denoised)
        
        # Step 5: Cleanup noise
        binary = self._cleanup_noise(binary)
        
        # Step 6: Dilation/erosion for font weight adjustment
        binary = self._adjust_font_weight(binary)
        
        return binary
    
    def _adaptive_threshold(self, gray: np.ndarray) -> np.ndarray:
        """
        Adaptive Gaussian thresholding
        Best for uneven lighting (stadium scoreboards)
        Based on ScoreSight implementation
        """
        h, w = gray.shape
        
        # Calculate block size based on image area (ScoreSight method)
        block_size = max(int((h * w) * 0.01), 3)
        block_size = block_size | 1  # Make it odd
        
        binary = cv2.adaptiveThreshold(
            gray, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            block_size,
            2
        )
        return binary
    
    def _otsu_threshold(self, gray: np.ndarray) -> np.ndarray:
        """
        Otsu's thresholding
        Good for high contrast images
        """
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return binary
    
    def _local_threshold(self, gray: np.ndarray) -> np.ndarray:
        """
        Local mean thresholding
        Alternative to adaptive Gaussian
        """
        h, w = gray.shape
        block_size = max(int(min(h, w) * 0.1), 11)
        if block_size % 2 == 0:
            block_size += 1
        
        binary = cv2.adaptiveThreshold(
            gray, 255,
            cv2.ADAPTIVE_THRESH_MEAN_C,
            cv2.THRESH_BINARY,
            block_size,
            10
        )
        return binary
    
    def _cleanup_noise(self, binary: np.ndarray, cleanup_thresh: float = 0.0001) -> np.ndarray:
        """
        Remove small artifacts that might confuse OCR
        Based on ScoreSight contour filtering
        """
        # Find contours
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Calculate area threshold (ScoreSight method)
        img_area_thresh = binary.shape[0] * binary.shape[1] * cleanup_thresh
        
        # Remove small artifacts
        for contour in contours:
            if cv2.contourArea(contour) < img_area_thresh:
                # Paint noise black
                cv2.drawContours(binary, [contour], 0, 0, -1)
        
        return binary
    
    def _adjust_font_weight(self, binary: np.ndarray, dilation: int = 1) -> np.ndarray:
        """
        Slight dilation to make text bolder (helps OCR)
        """
        if dilation > 0:
            kernel = np.ones((2, 2), np.uint8)
            binary = cv2.dilate(binary, kernel, iterations=dilation)
        return binary
    
    def deskew(self, image: np.ndarray) -> np.ndarray:
        """
        Deskew rotated text
        """
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # Detect skew angle
        coords = np.column_stack(np.where(gray > 0))
        if len(coords) < 100:
            return image
        
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
        
        # Rotate if significant skew
        if abs(angle) > 0.5:
            (h, w) = gray.shape
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            rotated = cv2.warpAffine(gray, M, (w, h),
                                    flags=cv2.INTER_CUBIC,
                                    borderMode=cv2.BORDER_REPLICATE)
            return rotated
        
        return gray
    
    def enhance_contrast(self, image: np.ndarray) -> np.ndarray:
        """
        Enhance contrast using CLAHE
        Good for low-light scoreboards
        """
        if len(image.shape) == 3:
            lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(l)
            
            enhanced = cv2.merge([enhanced, a, b])
            enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
        else:
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(image)
        
        return enhanced
