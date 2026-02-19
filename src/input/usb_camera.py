"""
USB Camera Capture - Webcam input support
"""
import cv2
import numpy as np
from PySide6.QtCore import QThread, Signal

class USBCameraCapture(QThread):
    """
    USB Camera capture using OpenCV
    """
    frame_ready = Signal(np.ndarray)
    error_signal = Signal(str)
    
    @staticmethod
    def list_cameras(max_cameras=10):
        """List available USB cameras"""
        available_cameras = []
        for i in range(max_cameras):
            cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)  # Use DirectShow on Windows
            if cap.isOpened():
                ret, frame = cap.read()
                if ret:
                    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    fps = cap.get(cv2.CAP_PROP_FPS)
                    available_cameras.append({
                        'index': i,
                        'name': f'Camera {i} ({width}x{height} @ {fps}fps)'
                    })
                cap.release()
        return available_cameras
    
    def __init__(self, camera_index=0, width=1920, height=1080, fps=30):
        super().__init__()
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self.fps = fps
        self.cap = None
        self.is_running = False
    
    def run(self):
        """Main capture loop"""
        self.is_running = True
        
        try:
            # Open camera with DirectShow backend (Windows)
            self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
            
            if not self.cap.isOpened():
                self.error_signal.emit(f"Cannot open camera {self.camera_index}")
                return
            
            # Set properties
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self.cap.set(cv2.CAP_PROP_FPS, self.fps)
            
            # Get actual properties
            actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps = self.cap.get(cv2.CAP_PROP_FPS)
            
            print(f"Camera {self.camera_index} opened: {actual_width}x{actual_height} @ {actual_fps}fps")
            
            while self.is_running:
                ret, frame = self.cap.read()
                
                if not ret:
                    self.error_signal.emit("Camera frame capture failed")
                    break
                
                self.frame_ready.emit(frame)
                
                # Small delay to prevent overwhelming CPU
                cv2.waitKey(1)
                
        except Exception as e:
            self.error_signal.emit(f"Camera error: {e}")
        finally:
            if self.cap:
                self.cap.release()
    
    def stop(self):
        """Stop capture"""
        self.is_running = False
        if self.cap:
            self.cap.release()
        self.wait()
