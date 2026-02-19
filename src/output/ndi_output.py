"""
NDI Output - Send video with OCR overlay via NDI
"""
import cv2
import numpy as np
try:
    from cyndilib.sender import Sender
    from cyndilib.video_frame import VideoSendFrame
    NDI_AVAILABLE = True
except ImportError:
    NDI_AVAILABLE = False

class NDIOutput:
    """
    NDI output sender for live streaming with OCR overlay
    """
    
    def __init__(self, source_name: str = "SmartOCR Output"):
        self.source_name = source_name
        self.sender = None
        self.video_frame = None
        self.is_running = False
        
        if not NDI_AVAILABLE:
            print("Warning: cyndilib not installed. NDI output disabled.")
            return
        
        try:
            self.sender = Sender()
            self.sender.create(source_name)
            self.video_frame = VideoSendFrame()
            print(f"NDI Output created: {source_name}")
        except Exception as e:
            print(f"NDI Output error: {e}")
    
    def send_frame(self, frame: np.ndarray):
        """Send frame via NDI"""
        if not NDI_AVAILABLE or self.sender is None:
            return
        
        try:
            # Ensure frame is RGBA for NDI
            if len(frame.shape) == 3 and frame.shape[2] == 3:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2BGRA)
            
            h, w = frame.shape[:2]
            self.video_frame.set_resolution(w, h)
            self.video_frame.set_frame_data(frame)
            self.sender.send_video(self.video_frame)
        except Exception as e:
            print(f"NDI send error: {e}")
    
    def stop(self):
        """Stop NDI output"""
        if self.sender:
            self.sender.destroy()
            self.sender = None
