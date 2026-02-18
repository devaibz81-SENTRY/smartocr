"""
Video Reader - Threaded video capture for smooth playback
"""
import cv2
import numpy as np
from PySide6.QtCore import QThread, Signal
from typing import Optional, Callable

class VideoReader(QThread):
    """
    Threaded video reader for smooth playback
    """
    frame_ready = Signal(np.ndarray)  # Emits frame
    finished_signal = Signal()
    error_signal = Signal(str)
    
    def __init__(self, video_path: str):
        super().__init__()
        self.video_path = video_path
        self.cap: Optional[cv2.VideoCapture] = None
        self.is_running = False
        self.frame_delay = 33  # ~30fps default
        self.current_frame = 0
        self.total_frames = 0
        self.fps = 30
    
    def run(self):
        """Main video reading loop"""
        self.cap = cv2.VideoCapture(self.video_path)
        
        if not self.cap.isOpened():
            self.error_signal.emit(f"Could not open video: {self.video_path}")
            return
        
        # Get video properties
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        if self.fps > 0:
            self.frame_delay = int(1000 / self.fps)
        
        self.is_running = True
        
        while self.is_running:
            ret, frame = self.cap.read()
            
            if not ret:
                # End of video
                break
            
            self.current_frame += 1
            
            # Emit frame
            self.frame_ready.emit(frame)
            
            # Control playback speed
            self.msleep(self.frame_delay)
        
        self.cap.release()
        self.finished_signal.emit()
    
    def stop(self):
        """Stop video reading"""
        self.is_running = False
        self.wait()
    
    def seek(self, frame_number: int):
        """Seek to specific frame"""
        if self.cap:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            self.current_frame = frame_number
    
    def get_progress(self) -> float:
        """Get playback progress (0-100)"""
        if self.total_frames > 0:
            return (self.current_frame / self.total_frames) * 100
        return 0.0
