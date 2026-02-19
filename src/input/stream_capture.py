"""
Stream Capture - SRT, RTSP, RTMP video input
"""
import cv2
import numpy as np
import time
from PySide6.QtCore import QThread, Signal

class StreamCapture(QThread):
    """
    Network stream capture (SRT, RTSP, RTMP)
    """
    frame_ready = Signal(np.ndarray)
    error_signal = Signal(str)
    
    def __init__(self, url: str):
        super().__init__()
        self.url = url
        self.cap = None
        self.is_running = False
        self.reconnect_delay = 5  # Seconds between reconnection attempts
    
    def run(self):
        """Main capture loop with auto-reconnect"""
        self.is_running = True
        
        while self.is_running:
            try:
                # Open stream
                self.cap = cv2.VideoCapture(self.url)
                
                if not self.cap.isOpened():
                    self.error_signal.emit(f"Cannot open stream: {self.url}")
                    time.sleep(self.reconnect_delay)
                    continue
                
                # Get stream info
                fps = self.cap.get(cv2.CAP_PROP_FPS)
                width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                
                print(f"Stream opened: {width}x{height} @ {fps}fps")
                
                # Capture loop
                while self.is_running:
                    ret, frame = self.cap.read()
                    
                    if not ret:
                        self.error_signal.emit("Stream disconnected, reconnecting...")
                        break
                    
                    self.frame_ready.emit(frame)
                
                # Clean up
                if self.cap:
                    self.cap.release()
                    self.cap = None
                
                if self.is_running:
                    time.sleep(self.reconnect_delay)
                    
            except Exception as e:
                self.error_signal.emit(f"Stream error: {e}")
                time.sleep(self.reconnect_delay)
    
    def stop(self):
        """Stop capture"""
        self.is_running = False
        if self.cap:
            self.cap.release()
        self.wait()
