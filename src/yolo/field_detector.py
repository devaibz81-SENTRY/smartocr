"""
YOLO Field Detector - Auto-detect scoreboard fields using YOLOv5
"""
import cv2
import numpy as np
from pathlib import Path
from typing import List, Dict
import sys
import torch

# Add YOLOv5 path
YOLOV5_PATH = r"C:\Users\suppo\Documents\YOLO BUILD\yolov5"
if YOLOV5_PATH not in sys.path:
    sys.path.insert(0, YOLOV5_PATH)

try:
    from models.common import DetectMultiBackend
    from utils.general import non_max_suppression, scale_boxes
    from utils.torch_utils import select_device
    from utils.augmentations import letterbox
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    print("Warning: YOLOv5 not found. Run training script first.")

class YOLOFieldDetector:
    """
    Detect scoreboard fields using YOLOv5
    """
    
    # Scoreboard field classes (from your trained model)
    FIELD_CLASSES = {
        0: ('away_fouls', 'Away Fouls', 'number'),
        1: ('away_team_name', 'Away Team Name', 'text'),
        2: ('away_score', 'Away Score', 'number'),
        3: ('game_clock', 'Game Clock', 'time'),
        4: ('home_fouls', 'Home Fouls', 'number'),
        5: ('home_team_name', 'Home Team Name', 'text'),
        6: ('home_score', 'Home Score', 'number'),
        7: ('period', 'Period', 'text'),
        8: ('shot_clock', 'Shot Clock', 'number'),
    }
    
    def __init__(self, model_path: str = None):
        self.model = None
        self.device = None
        self.conf_threshold = 0.25
        self.iou_threshold = 0.45
        
        if not YOLO_AVAILABLE:
            print("YOLOv5 not available.")
            return
        
        # Load model
        try:
            # Default to trained model
            if model_path is None:
                model_path = r"C:\Users\suppo\Documents\YOLO BUILD\yolov5\runs\train\scoreboard_detection\weights\best.pt"
            
            model_file = Path(model_path)
            if not model_file.exists():
                print(f"Model not found: {model_path}")
                return
            
            print(f"Loading YOLOv5 model: {model_file}")
            
            # Select device
            self.device = select_device('')
            
            # Load model
            self.model = DetectMultiBackend(str(model_file), device=self.device)
            self.stride = self.model.stride
            self.names = self.model.names
            
            print(f"Model loaded! Classes: {len(self.names)}")
            
        except Exception as e:
            print(f"Error loading YOLO model: {e}")
            self.model = None
    
    def detect(self, frame: np.ndarray) -> List[Dict]:
        """
        Detect scoreboard fields in frame
        """
        if self.model is None:
            return []
        
        try:
            # Preprocess
            img = letterbox(frame, 640, stride=self.stride)[0]
            img = img.transpose((2, 0, 1))[::-1]  # HWC to CHW, BGR to RGB
            img = np.ascontiguousarray(img)
            
            # Convert to tensor
            img = torch.from_numpy(img).to(self.device)
            img = img.float() / 255.0
            if img.ndimension() == 3:
                img = img.unsqueeze(0)
            
            # Inference
            pred = self.model(img, augment=False, visualize=False)
            
            # NMS
            pred = non_max_suppression(pred, self.conf_threshold, self.iou_threshold)
            
            detections = []
            
            for det in pred[0]:  # per image
                if det is None or len(det) == 0:
                    continue
                
                # Rescale boxes to original image
                det[:, :4] = scale_boxes(img.shape[2:], det[:, :4], frame.shape).round()
                
                for *xyxy, conf, cls in reversed(det):
                    cls = int(cls)
                    
                    # Map class to field type
                    if cls in self.FIELD_CLASSES:
                        field_id, display_name, field_type = self.FIELD_CLASSES[cls]
                    else:
                        field_id = f"field_{cls}"
                        display_name = f"Field {cls}"
                        field_type = "text"
                    
                    x1, y1, x2, y2 = map(int, xyxy)
                    bbox = (x1, y1, x2-x1, y2-y1)
                    
                    detections.append({
                        'name': field_id,
                        'display_name': display_name,
                        'bbox': bbox,
                        'field_type': field_type,
                        'confidence': float(conf)
                    })
            
            return detections
            
        except Exception as e:
            print(f"YOLO detection error: {e}")
            return []
    
    def is_available(self) -> bool:
        """Check if YOLO is available and loaded"""
        return self.model is not None and YOLO_AVAILABLE
