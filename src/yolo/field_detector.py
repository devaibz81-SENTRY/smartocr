"""
YOLO Field Detector - Auto-detect scoreboard fields using YOLO
"""
import cv2
import numpy as np
from pathlib import Path
from typing import List, Dict
import sys

# Add YOLO path
YOLO_PATH = r"C:\Users\suppo\Documents\YOLO BUILD\YOLOv8-Object-Detection-on-Video-with-OpenCV-main"
if YOLO_PATH not in sys.path:
    sys.path.insert(0, YOLO_PATH)

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    print("Warning: ultralytics not installed. YOLO detection disabled.")

class YOLOFieldDetector:
    """
    Detect scoreboard fields using YOLO
    Falls back to manual detection if model not available
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
        self.conf_threshold = 0.5
        
        if not YOLO_AVAILABLE:
            print("YOLO not available. Install with: pip install ultralytics")
            return
        
        # Try to load model
        try:
            # Look for trained scoreboard model first
            trained_model = Path(r"C:\Users\suppo\Documents\YOLO BUILD\YOLOv8-Object-Detection-on-Video-with-OpenCV-main\scoreboard_yolov5.pt")
            
            if trained_model.exists():
                print(f"Loading trained scoreboard model: {trained_model}")
                self.model = YOLO(str(trained_model))
            elif model_path:
                # Try provided path
                yolo_dir = Path(model_path)
                model_files = list(yolo_dir.glob("*.pt"))
                
                if model_files:
                    model_file = model_files[0]
                    print(f"Loading YOLO model: {model_file}")
                    self.model = YOLO(str(model_file))
                else:
                    print("No custom model found. Using default YOLOv8n.")
                    self.model = YOLO('yolov8n.pt')
            else:
                print("No trained model found. Please train first or use manual fields.")
                self.model = None
                
        except Exception as e:
            print(f"Error loading YOLO model: {e}")
            self.model = None
    
    def detect(self, frame: np.ndarray) -> List[Dict]:
        """
        Detect scoreboard fields in frame
        Returns list of field dictionaries
        """
        if self.model is None:
            print("YOLO model not loaded. Using manual field placement.")
            return []
        
        try:
            # Run detection
            results = self.model(frame, conf=self.conf_threshold)
            
            detections = []
            
            for result in results:
                if result.boxes is None:
                    continue
                
                boxes = result.boxes.xyxy.cpu().numpy()
                confs = result.boxes.conf.cpu().numpy()
                classes = result.boxes.cls.cpu().numpy().astype(int)
                
                for box, conf, cls in zip(boxes, confs, classes):
                    # Map class to field type
                    if cls in self.FIELD_CLASSES:
                        field_id, display_name, field_type = self.FIELD_CLASSES[cls]
                    else:
                        # Unknown class, treat as generic text
                        field_id = f"field_{len(detections)}"
                        display_name = f"Field {len(detections)}"
                        field_type = "text"
                    
                    x1, y1, x2, y2 = box
                    bbox = (int(x1), int(y1), int(x2-x1), int(y2-y1))
                    
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
    
    def train_info(self) -> str:
        """Return training instructions"""
        return """
To train a custom YOLO model for scoreboards:

1. Collect images of your scoreboards (50-100+ recommended)
2. Label them with bounding boxes for each field:
   - 0: home_score
   - 1: away_score  
   - 2: game_clock
   - 3: shot_clock
   - 4: period

3. Use a tool like LabelImg or Roboflow to annotate
4. Train with: yolo detect train data=your_data.yaml model=yolov8n.pt epochs=100
5. Place the trained .pt file in: 
   C:\\Users\\suppo\\Documents\\YOLO BUILD\\YOLOv8-Object-Detection-on-Video-with-OpenCV-main

For now, you can manually place fields by clicking "Add Field"
"""
