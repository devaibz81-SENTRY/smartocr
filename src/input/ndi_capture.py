"""
NDI Capture - Live NDI video input
Based on ScoreSight implementation
"""
import time
import cv2
import numpy as np
from PySide6.QtCore import QThread, Signal
from typing import Optional, List

try:
    from cyndilib.wrapper.ndi_recv import RecvColorFormat, RecvBandwidth
    from cyndilib.finder import Finder
    from cyndilib.receiver import Receiver, ReceiveFrameType
    from cyndilib.video_frame import VideoRecvFrame
    from cyndilib.metadata_frame import MetadataRecvFrame
    NDI_AVAILABLE = True
except ImportError:
    NDI_AVAILABLE = False
    print("Warning: cyndilib not installed. NDI support disabled.")
    print("Install with: pip install cyndilib")

class NDICapture(QThread):
    """
    NDI video capture thread
    """
    frame_ready = Signal(np.ndarray)
    error_signal = Signal(str)
    
    finder = None
    
    @staticmethod
    def get_sources() -> List[str]:
        """Get list of available NDI sources"""
        if not NDI_AVAILABLE:
            return []
        
        if NDICapture.finder is None:
            NDICapture.finder = Finder()
        
        sources = []
        if NDICapture.finder.wait_for_sources(1.0):
            sources = NDICapture.finder.get_source_names()
        
        return sources
    
    def __init__(self, source_name: str):
        super().__init__()
        self.source_name = source_name
        self.receiver = None
        self.is_running = False
        
        if not NDI_AVAILABLE:
            self.error_signal.emit("NDI not available. Install cyndilib.")
            return
        
        try:
            self.receiver = Receiver(
                color_format=RecvColorFormat.BGRX_BGRA,
                bandwidth=RecvBandwidth.highest,
            )
            
            if NDICapture.finder is None:
                NDICapture.finder = Finder()
            
            self.source = NDICapture.finder.get_source(source_name)
            self.receiver.set_source(self.source)
            
            self.video_frame = VideoRecvFrame()
            self.metadata_frame = MetadataRecvFrame()
            self.receiver.set_video_frame(self.video_frame)
            self.receiver.set_metadata_frame(self.metadata_frame)
            self.receiver.set_source_tally_program(True)
            
        except Exception as e:
            self.error_signal.emit(f"NDI init error: {e}")
    
    def run(self):
        """Main capture loop"""
        if not NDI_AVAILABLE or self.receiver is None:
            return
        
        self.is_running = True
        
        while self.is_running:
            try:
                if not self.receiver.is_connected():
                    time.sleep(0.1)
                    continue
                
                ret = self.receiver.receive(ReceiveFrameType.recv_all, 1000)
                
                if ret == ReceiveFrameType.recv_video:
                    if min(self.video_frame.xres, self.video_frame.yres) != 0:
                        # Create numpy array from frame
                        frame = np.empty(
                            self.video_frame.get_buffer_size(), dtype=np.uint8
                        )
                        self.video_frame.fill_p_data(frame)
                        frame = frame.reshape(
                            self.video_frame.yres, self.video_frame.xres, 4
                        )
                        # Convert BGRA to BGR for OpenCV
                        frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                        self.frame_ready.emit(frame)
                        
                elif ret == ReceiveFrameType.recv_error:
                    self.receiver.reconnect()
                    
            except Exception as e:
                self.error_signal.emit(f"NDI capture error: {e}")
                time.sleep(1)
    
    def stop(self):
        """Stop capture"""
        self.is_running = False
        if self.receiver:
            self.receiver.disconnect()
        self.wait()
