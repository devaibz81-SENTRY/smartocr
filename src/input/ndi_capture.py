"""
NDI Capture - Live NDI video input with IP support
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
    NDI video capture thread with IP support
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
    
    def __init__(self, source_name: str = None, ip_address: str = None):
        super().__init__()
        self.source_name = source_name
        self.ip_address = ip_address
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
            
            # Try to get source - either by name or create from IP
            if source_name and source_name != "No NDI sources found":
                self.source = NDICapture.finder.get_source(source_name)
            elif ip_address:
                # Create source from IP address
                # Format: IP_ADDRESS (NDI_SOURCE_NAME)
                # or just IP_ADDRESS
                self.source = self._create_source_from_ip(ip_address)
            else:
                self.error_signal.emit("No NDI source or IP provided")
                return
            
            if self.source:
                self.receiver.set_source(self.source)
                
                self.video_frame = VideoRecvFrame()
                self.metadata_frame = MetadataRecvFrame()
                self.receiver.set_video_frame(self.video_frame)
                self.receiver.set_metadata_frame(self.metadata_frame)
                self.receiver.set_source_tally_program(True)
            else:
                self.error_signal.emit("Could not create NDI source")
                
        except Exception as e:
            self.error_signal.emit(f"NDI init error: {e}")
    
    def _create_source_from_ip(self, ip_address: str):
        """Create NDI source from IP address"""
        try:
            # NDI sources can be created from IP:PORT or just IP
            # Common NDI ports: 5960, 5961, etc.
            if ':' not in ip_address:
                # Try common NDI ports
                for port in [5960, 5961, 5962]:
                    try:
                        source_str = f"{ip_address}:{port}"
                        source = NDICapture.finder.get_source(source_str)
                        if source:
                            print(f"Connected to NDI at {source_str}")
                            return source
                    except:
                        continue
            
            # Try direct IP
            source = NDICapture.finder.get_source(ip_address)
            if source:
                print(f"Connected to NDI at {ip_address}")
                return source
            
            # If finder doesn't work, try creating a manual source
            # This is implementation-specific to cyndilib
            print(f"Attempting manual connection to {ip_address}")
            return NDICapture.finder.get_source(ip_address)
            
        except Exception as e:
            print(f"Error creating NDI source from IP: {e}")
            return None
    
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
