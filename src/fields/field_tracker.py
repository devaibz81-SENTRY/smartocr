"""
Field Tracker - Tracks field positions across frames using optical flow
and re-acquires lost fields using template matching
"""
import cv2
import numpy as np
from typing import List, Tuple, Optional
from .field_region import FieldRegion

class FieldTracker:
    """
    Tracks field regions across video frames
    Uses optical flow for smooth tracking and template matching for re-acquisition
    """
    
    def __init__(self):
        self.prev_gray = None
        self.lk_params = dict(
            winSize=(21, 21),
            maxLevel=3,
            criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03)
        )
        self.feature_params = dict(
            maxCorners=100,
            qualityLevel=0.01,
            minDistance=10,
            blockSize=7
        )
    
    def process_frame(self, frame: np.ndarray, fields: List[FieldRegion]) -> bool:
        """
        Process a new frame and update field positions
        Returns True if camera movement was detected
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        if self.prev_gray is None:
            # First frame - initialize templates
            self.prev_gray = gray
            for field in fields:
                self._update_template(frame, field)
            return False
        
        # Detect overall camera movement using optical flow
        camera_moved = self._detect_motion(gray)
        
        if camera_moved:
            # Update all field positions
            for field in fields:
                if field.is_visible:
                    new_bbox = self._track_field_optical_flow(field, gray)
                    if new_bbox:
                        field.update_position(new_bbox)
                else:
                    # Try to re-acquire lost field
                    new_bbox = self._reacquire_field(frame, field)
                    if new_bbox:
                        field.update_position(new_bbox)
                        field.is_visible = True
                        field.frames_missing = 0
                        self._update_template(frame, field)
        
        self.prev_gray = gray
        return camera_moved
    
    def _detect_motion(self, gray: np.ndarray) -> bool:
        """Detect if camera has moved significantly"""
        if self.prev_gray is None:
            return False
        
        # Calculate optical flow for sparse features
        prev_pts = cv2.goodFeaturesToTrack(self.prev_gray, mask=None, **self.feature_params)
        
        if prev_pts is None:
            return False
        
        next_pts, status, error = cv2.calcOpticalFlowPyrLK(
            self.prev_gray, gray, prev_pts, None, **self.lk_params
        )
        
        if next_pts is None:
            return False
        
        # Calculate average movement
        good_prev = prev_pts[status == 1]
        good_next = next_pts[status == 1]
        
        if len(good_prev) < 5:
            return False
        
        movements = np.linalg.norm(good_next - good_prev, axis=1)
        avg_movement = np.mean(movements)
        
        # Return True if movement > 2 pixels
        return avg_movement > 2.0
    
    def _track_field_optical_flow(self, field: FieldRegion, gray: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
        """Track a single field using optical flow"""
        x, y, w, h = field.bbox
        
        # Extract ROI from previous frame
        roi_prev = self.prev_gray[y:y+h, x:x+w]
        
        # Find features in ROI
        prev_pts = cv2.goodFeaturesToTrack(roi_prev, mask=None, **self.feature_params)
        
        if prev_pts is None:
            return None
        
        # Adjust points to global coordinates
        prev_pts[:, 0, 0] += x
        prev_pts[:, 0, 1] += y
        
        # Calculate optical flow
        next_pts, status, error = cv2.calcOpticalFlowPyrLK(
            self.prev_gray, gray, prev_pts, None, **self.lk_params
        )
        
        if next_pts is None or status is None:
            return None
        
        # Calculate median offset
        good_prev = prev_pts[status == 1]
        good_next = next_pts[status == 1]
        
        if len(good_prev) < 3:
            return None
        
        dx = int(np.median(good_next[:, 0, 0] - good_prev[:, 0, 0]))
        dy = int(np.median(good_next[:, 0, 1] - good_prev[:, 0, 1]))
        
        # Update bbox
        new_x = max(0, x + dx)
        new_y = max(0, y + dy)
        
        return (new_x, new_y, w, h)
    
    def _reacquire_field(self, frame: np.ndarray, field: FieldRegion) -> Optional[Tuple[int, int, int, int]]:
        """Try to re-acquire a lost field using template matching"""
        if field.template is None:
            return None
        
        # Search in larger area around last known position
        x, y, w, h = field.bbox
        search_margin = 100
        
        frame_h, frame_w = frame.shape[:2]
        
        sx1 = max(0, x - search_margin)
        sy1 = max(0, y - search_margin)
        sx2 = min(frame_w, x + w + search_margin)
        sy2 = min(frame_h, y + h + search_margin)
        
        search_area = frame[sy1:sy2, sx1:sx2]
        
        if search_area.size == 0:
            return None
        
        # Template matching
        result = cv2.matchTemplate(search_area, field.template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        
        if max_val > 0.6:  # Threshold for match
            new_x = sx1 + max_loc[0]
            new_y = sy1 + max_loc[1]
            return (new_x, new_y, w, h)
        
        return None
    
    def _update_template(self, frame: np.ndarray, field: FieldRegion):
        """Update the template image for a field"""
        x, y, w, h = field.bbox
        frame_h, frame_w = frame.shape[:2]
        
        # Ensure bounds
        x = max(0, min(x, frame_w - w))
        y = max(0, min(y, frame_h - h))
        
        template = frame[y:y+h, x:x+w].copy()
        field.set_template(template)
    
    def reset(self):
        """Reset tracker state"""
        self.prev_gray = None
