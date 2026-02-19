"""
NDI Capture - Live NDI video input
Based exactly on ScoreSight implementation
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

def ReceiveFrameTypeToString(frame_type: 'ReceiveFrameType') -> str:
    if frame_type == ReceiveFrameType.recv_audio: return "recv_audio"
    if frame_type == ReceiveFrameType.recv_metadata: return "recv_metadata"
    if frame_type == ReceiveFrameType.recv_video: return "recv_video"
    if frame_type == ReceiveFrameType.recv_error: return "recv_error"
    if frame_type == ReceiveFrameType.nothing: return "nothing"
    if frame_type == ReceiveFrameType.recv_status_change: return "recv_status_change"
    if frame_type == ReceiveFrameType.recv_buffers_full: return "recv_buffers_full"
    return "recv_unknown"

class NDICapture(QThread):
    """
    NDI video capture thread - Wraps the ScoreSight-style pull logic into a QThread 
    for the SmartOCR architecture.
    """
    frame_ready = Signal(np.ndarray)
    error_signal = Signal(str)
    
    # Static finder shared across instances (ScoreSight pattern)
    finder = Finder() if NDI_AVAILABLE else None
    
    @staticmethod
    def get_sources() -> List[str]:
        """Get list of available NDI sources"""
        if not NDI_AVAILABLE:
            return []
        
        # Give it a bit more time than the default 1.0s if needed
        if NDICapture.finder.wait_for_sources(1.0):
            return NDICapture.finder.get_source_names()
        
        return []
    
    def __init__(self, source_name: str = None, ip_address: str = None):
        super().__init__()
        self.source_name = source_name
        self.ip_address = ip_address
        self.receiver = None
        self.is_running = False
        
        if not NDI_AVAILABLE:
            return

        try:
            self.receiver = Receiver(
                color_format=RecvColorFormat.BGRX_BGRA,
                bandwidth=RecvBandwidth.highest,
            )
            
            # Use IP if provided, otherwise use discovered name
            search_id = ip_address if ip_address else source_name
            
            if search_id:
                self.source = NDICapture.finder.get_source(search_id)
                if self.source:
                    self.receiver.set_source(self.source)
                    self.video_frame = VideoRecvFrame()
                    self.metadata_frame = MetadataRecvFrame()
                    self.receiver.set_video_frame(self.video_frame)
                    self.receiver.set_metadata_frame(self.metadata_frame)
                    self.receiver.set_source_tally_program(True)
                    self.receiver.set_source_tally_preview(False)
                    print(f"NDI Capture initialized for: {self.source.name}")
                else:
                    print(f"NDI Source not found: {search_id}")
            
        except Exception as e:
            self.error_signal.emit(f"NDI init error: {e}")

    def run(self):
        """Main capture loop - Simplified to fix 'video decoder not found'"""
        if not NDI_AVAILABLE or self.receiver is None:
            return
        
        self.is_running = True
        
        while self.is_running:
            try:
                # Check connection
                if self.receiver is None or not self.receiver.is_connected():
                    if self.receiver:
                        self.receiver.reconnect()
                    time.sleep(1)
                    continue
                
                # Receive frame (standard single receive)
                # This is more compatible with NDI|HX streams that might fail 
                # under rapid-fire 'drain' loops.
                ret = self.receiver.receive(ReceiveFrameType.recv_all, 1000)
                
                if ret == ReceiveFrameType.recv_video:
                    if min(self.video_frame.xres, self.video_frame.yres) != 0:
                        # Allocate and fill buffer
                        frame = np.empty(
                            self.video_frame.get_buffer_size(), dtype=np.uint8
                        )
                        self.video_frame.fill_p_data(frame)
                        
                        # Reshape to 4-channel BGRX
                        frame = frame.reshape(
                            self.video_frame.yres, self.video_frame.xres, 4
                        )
                        
                        # Standard conversion for OpenCV (BGRX to BGR)
                        frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                        
                        self.frame_ready.emit(frame)
                
                elif ret == ReceiveFrameType.recv_error:
                    self.receiver.reconnect()
                    time.sleep(0.5)
                
                # Small yield to keep UI responsive
                time.sleep(0.001)
                
            except Exception as e:
                print(f"NDI Runner Error: {e}")
                time.sleep(1)

    def stop(self):
        """Stop capture"""
        self.is_running = False
        if self.receiver:
            self.receiver.disconnect()
        self.wait()
