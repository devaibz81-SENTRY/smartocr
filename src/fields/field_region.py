"""
Field Region - Defines a single OCR field/region on the scoreboard
"""
from dataclasses import dataclass, field
from typing import Optional, Tuple
from enum import Enum

class FieldType(Enum):
    NUMBER = "number"      # Scores, shot clock
    TIME = "time"          # Game clock (MM:SS)
    TEXT = "text"          # Period, team names

@dataclass
class FieldRegion:
    """
    Represents a single field to be OCR'd from the scoreboard
    """
    name: str                           # Field identifier (e.g., "home_score")
    display_name: str                   # Human-readable name (e.g., "Home Score")
    bbox: Tuple[int, int, int, int]    # (x, y, width, height)
    field_type: FieldType = FieldType.NUMBER
    
    # Current state
    current_value: str = ""
    confidence: float = 0.0
    
    # Tracking state
    is_visible: bool = True
    frames_missing: int = 0
    last_good_value: str = ""           # Hold this when field is lost
    
    # Template for re-acquisition
    template: Optional[object] = field(default=None, repr=False)
    
    # Validation
    max_jump: int = 25                  # Large threshold for feed recovery
    
    def update_value(self, new_value: str, confidence: float):
        """Update field value with validation"""
        if not new_value or confidence < 0.3:
            # Low confidence - mark as missing
            self.frames_missing += 1
            self.is_visible = False
            return False
        
        # Validate based on field type
        if self._is_valid_change(new_value):
            self.last_good_value = self.current_value if self.current_value else new_value
            self.current_value = new_value
            self.confidence = confidence
            self.frames_missing = 0
            self.is_visible = True
            return True
        else:
            # Invalid jump - hold last value
            self.frames_missing += 1
            return False
    
    def _is_valid_change(self, new_value: str) -> bool:
        """Check if value change is valid (prevents wild jumps)"""
        if not self.current_value:
            return True
        
        if self.field_type == FieldType.NUMBER:
            try:
                old_n = int(self.current_value) if self.current_value else 0
                new_n = int(new_value)
                diff = abs(new_n - old_n)
                
                # Large jump threshold for feed recovery
                # If we've been missing for many frames, allow bigger jumps
                if self.frames_missing > 30:  # ~1 second at 30fps
                    return diff <= self.max_jump * 2  # Double threshold after feed loss
                return diff <= self.max_jump
            except ValueError:
                return False
        
        elif self.field_type == FieldType.TIME:
            # Time should generally decrease or stay same
            # But allow some tolerance for feed issues
            return True  # Accept all time changes (validated elsewhere)
        
        return True
    
    def get_output_value(self) -> str:
        """Get value to output (holds last good if currently lost)"""
        if self.is_visible:
            return self.current_value
        else:
            # Return last good value until re-acquired
            return self.last_good_value if self.last_good_value else ""
    
    def update_position(self, new_bbox: Tuple[int, int, int, int]):
        """Update field position (from tracking)"""
        self.bbox = new_bbox
    
    def set_template(self, template_image):
        """Store template image for re-acquisition"""
        self.template = template_image
    
    def reset(self):
        """Reset field state"""
        self.current_value = ""
        self.last_good_value = ""
        self.confidence = 0.0
        self.is_visible = True
        self.frames_missing = 0
