"""
Field Manager - Manages all OCR fields
"""
from typing import List, Dict, Optional
from .field_region import FieldRegion, FieldType

class FieldManager:
    """Manages collection of field regions"""
    
    def __init__(self):
        self.fields: Dict[str, FieldRegion] = {}
        self.field_order: List[str] = []
    
    def add_field(self, name: str, display_name: str, bbox: tuple, 
                  field_type: FieldType = FieldType.NUMBER) -> FieldRegion:
        """Add a new field region"""
        field = FieldRegion(
            name=name,
            display_name=display_name,
            bbox=bbox,
            field_type=field_type
        )
        self.fields[name] = field
        if name not in self.field_order:
            self.field_order.append(name)
        return field
    
    def remove_field(self, name: str):
        """Remove a field"""
        if name in self.fields:
            del self.fields[name]
            self.field_order.remove(name)
    
    def get_field(self, name: str) -> Optional[FieldRegion]:
        """Get field by name"""
        return self.fields.get(name)
    
    def get_all_fields(self) -> List[FieldRegion]:
        """Get all fields in order"""
        return [self.fields[name] for name in self.field_order if name in self.fields]
    
    def update_field_position(self, name: str, new_bbox: tuple):
        """Update field's bounding box"""
        if name in self.fields:
            self.fields[name].update_position(new_bbox)
    
    def get_field_values(self) -> Dict[str, str]:
        """Get current values for all fields (for output)"""
        return {
            name: field.get_output_value() 
            for name, field in self.fields.items()
        }
    
    def reset_all(self):
        """Reset all fields"""
        for field in self.fields.values():
            field.reset()
    
    def create_default_fields(self, frame_width: int, frame_height: int):
        """Create default field layout (centered)"""
        # Default positions for typical scoreboard layout
        center_x = frame_width // 2
        center_y = frame_height // 2
        
        # Home score - left side
        self.add_field(
            "home_score", 
            "Home Score",
            (center_x - 200, center_y - 50, 100, 80),
            FieldType.NUMBER
        )
        
        # Away score - right side
        self.add_field(
            "away_score",
            "Away Score", 
            (center_x + 100, center_y - 50, 100, 80),
            FieldType.NUMBER
        )
        
        # Game clock - center top
        self.add_field(
            "game_clock",
            "Game Clock",
            (center_x - 75, center_y - 150, 150, 60),
            FieldType.TIME
        )
        
        # Period - center below clock
        self.add_field(
            "period",
            "Period",
            (center_x - 50, center_y - 80, 100, 40),
            FieldType.TEXT
        )
        
        # Shot clock - left of game clock
        self.add_field(
            "shot_clock",
            "Shot Clock",
            (center_x - 200, center_y - 150, 80, 60),
            FieldType.NUMBER
        )
