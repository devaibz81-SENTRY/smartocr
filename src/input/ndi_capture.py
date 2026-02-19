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
        """Main capture loop using ScoreSight's read/drain logic"""
        if not NDI_AVAILABLE or self.receiver is None:
            return
        
        self.is_running = True
        
        while self.is_running:
            if self.receiver is not None and self.receiver.is_connected():
                # ScoreSight pattern: Try to "drain" or find the latest frame within 30ms window
                video_grab_start_time = time.time()
                frame_found = False
                
                while (
                    self.is_running
                    and self.receiver is not None
                    and self.receiver.is_connected()
                    and time.time() - video_grab_start_time < 0.03
                ):
                    try:
                        ret = self.receiver.receive(ReceiveFrameType.recv_all, 1000)
                    except Exception as e:
                        print(f"Error receiving NDI frame: {e}")
                        time.sleep(1)
                        if self.receiver: self.receiver.reconnect()
                        break
                    
                    if ret == ReceiveFrameType.recv_video:
                        if min(self.video_frame.xres, self.video_frame.yres) != 0:
                            # Allocate buffer
                            frame = np.empty(
                                self.video_frame.get_buffer_size(), dtype=np.uint8
                            )
                            # Copy from NDI to numpy
                            self.video_frame.fill_p_data(frame)
                            # Reshape to 4-channel image
                            frame = frame.reshape(
                                self.video_frame.yres, self.video_frame.xres, 4
                            )
                            
                            # EXACT Scoresight conversion: 
                            # ScoreSight uses cvtColor(frame, cv2.COLOR_RGBA2RGB) 
                            # on a BGRX_BGRA input, effectively swapping R and B.
                            # We'll use the same to be consistent with their "correct" behavior.
                            frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2RGB)
                            
                            self.frame_ready.emit(frame)
                            frame_found = True
                            # We found a frame, but ScoreSight loop continues for 30ms 
                            # to get the absolute newest one.
                            
                        else:
                            print("NDI Capture video frame is empty")
                    
                    elif ret == ReceiveFrameType.recv_metadata:
                        continue
                    elif ret == ReceiveFrameType.recv_error:
                        if self.receiver: self.receiver.reconnect()
                        break
                    else:
                        # Nothing or status change
                        pass
                
                if not frame_found:
                    # Small sleep if no frame found in the 30ms window 
                    # to prevent CPU pinning
                    time.sleep(0.001)
            else:
                # Not connected
                if self.receiver:
                    self.receiver.reconnect()
                time.sleep(1)

    def stop(self):
        """Stop capture"""
        self.is_running = False
        if self.receiver:
            self.receiver.disconnect()
        self.wait()
