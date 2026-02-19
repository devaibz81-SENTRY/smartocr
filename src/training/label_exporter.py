"""
Label Export Tool - Convert manual annotations to YOLO format
"""
import json
import os
from pathlib import Path
from typing import List, Dict
import cv2

class YOLOLabelExporter:
    """
    Export field annotations to YOLO training format
    """
    
    # YOLO class mapping
    CLASS_NAMES = {
        0: 'home_score',
        1: 'away_score',
        2: 'game_clock',
        3: 'shot_clock',
        4: 'period'
    }
    
    def __init__(self, output_dir: str = "training_data"):
        self.output_dir = Path(output_dir)
        self.images_dir = self.output_dir / "images" / "train"
        self.labels_dir = self.output_dir / "labels" / "train"
        
        # Create directories
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.labels_dir.mkdir(parents=True, exist_ok=True)
    
    def export_frame(self, frame, fields: List[Dict], frame_number: int = None):
        """
        Export a single frame with field annotations
        
        Args:
            frame: OpenCV image (BGR)
            fields: List of field dicts with 'name', 'bbox' (x,y,w,h), 'class_id'
            frame_number: Optional frame number for naming
        """
        h, w = frame.shape[:2]
        
        # Generate filename
        if frame_number is not None:
            base_name = f"frame_{frame_number:06d}"
        else:
            import time
            base_name = f"capture_{int(time.time())}"
        
        # Save image
        img_path = self.images_dir / f"{base_name}.jpg"
        cv2.imwrite(str(img_path), frame)
        
        # Create YOLO format labels
        labels = []
        for field in fields:
            class_id = field.get('class_id', self._get_class_id(field['name']))
            x, y, bw, bh = field['bbox']
            
            # Convert to YOLO format (normalized center x, center y, width, height)
            x_center = (x + bw / 2) / w
            y_center = (y + bh / 2) / h
            width = bw / w
            height = bh / h
            
            labels.append(f"{class_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}")
        
        # Save labels
        label_path = self.labels_dir / f"{base_name}.txt"
        with open(label_path, 'w') as f:
            f.write('\n'.join(labels))
        
        return base_name
    
    def _get_class_id(self, field_name: str) -> int:
        """Map field name to class ID"""
        mapping = {
            'home_score': 0,
            'away_score': 1,
            'game_clock': 2,
            'shot_clock': 3,
            'period': 4
        }
        return mapping.get(field_name, 0)
    
    def create_data_yaml(self) -> str:
        """Create data.yaml for YOLO training"""
        yaml_content = f"""path: {self.output_dir.absolute()}
train: images/train
val: images/train  # Use same for now, split later

nc: 5
names:
  0: home_score
  1: away_score
  2: game_clock
  3: shot_clock
  4: period
"""
        yaml_path = self.output_dir / "data.yaml"
        with open(yaml_path, 'w') as f:
            f.write(yaml_content)
        
        return str(yaml_path)
    
    def get_stats(self) -> Dict:
        """Get training dataset statistics"""
        num_images = len(list(self.images_dir.glob("*.jpg")))
        num_labels = len(list(self.labels_dir.glob("*.txt")))
        
        return {
            'images': num_images,
            'labels': num_labels,
            'output_dir': str(self.output_dir)
        }
    
    def export_from_video(self, video_path: str, fields, interval: int = 30):
        """
        Export frames from video at regular intervals
        Useful for creating training dataset from existing footage
        
        Args:
            video_path: Path to video file
            fields: FieldManager with current field positions
            interval: Export every N frames
        """
        cap = cv2.VideoCapture(video_path)
        frame_count = 0
        exported = 0
        
        print(f"Exporting frames from {video_path}...")
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            if frame_count % interval == 0:
                # Get current field positions
                field_list = []
                for field in fields.get_all_fields():
                    field_list.append({
                        'name': field.name,
                        'bbox': field.bbox,
                        'class_id': self._get_class_id(field.name)
                    })
                
                self.export_frame(frame, field_list, frame_count)
                exported += 1
            
            frame_count += 1
        
        cap.release()
        
        # Create YAML
        yaml_path = self.create_data_yaml()
        
        print(f"Exported {exported} frames to {self.output_dir}")
        print(f"data.yaml created: {yaml_path}")
        print(f"\nTo train YOLO:")
        print(f"yolo detect train data={yaml_path} model=yolov8n.pt epochs=100")
        
        return exported
