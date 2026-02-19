"""
Interactive Field Editor - Click and drag to move/resize fields
"""
import cv2
import numpy as np
from typing import Tuple, Optional, List
from PySide6.QtCore import Qt, QPoint, QRect, Signal
from PySide6.QtWidgets import QLabel
from PySide6.QtGui import QMouseEvent, QPainter, QPen, QColor, QBrush

class InteractiveVideoLabel(QLabel):
    """
    Video display with interactive field editing
    Supports: click to select, drag to move, resize handles
    """
    
    field_selected = Signal(str)  # Emits field name when selected
    field_moved = Signal(str, tuple)  # Emits field name and new bbox
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        
        # Field management
        self.fields = []  # List of field regions
        self.selected_field = None
        self.hovered_field = None
        
        # Interaction state
        self.is_dragging = False
        self.is_resizing = False
        self.drag_start_pos = None
        self.resize_handle = None  # 'tl', 'tr', 'bl', 'br' or None
        
        # Visual settings
        self.handle_size = 8
        self.selected_color = QColor(0, 255, 255)  # Cyan
        self.normal_color = QColor(0, 255, 0)      # Green
        self.lost_color = QColor(255, 0, 0)        # Red
        self.handle_color = QColor(255, 255, 0)    # Yellow
        
        # Scale factors (video to display)
        self.scale_x = 1.0
        self.scale_y = 1.0
        self.offset_x = 0
        self.offset_y = 0
        
        # Live AI detections
        self.detections = []
    
    def set_detections(self, detections):
        """Update live AI detections from YOLO"""
        self.detections = detections
        self.update()

    def set_fields(self, fields):
        """Update field list"""
        self.fields = fields
        self.update()
    
    def set_scale(self, video_width, video_height):
        """Calculate scale from video to display"""
        display_width = self.width()
        display_height = self.height()
        
        # Maintain aspect ratio
        video_aspect = video_width / video_height
        display_aspect = display_width / display_height
        
        if video_aspect > display_aspect:
            # Video is wider - fit to width
            self.scale_x = display_width / video_width
            self.scale_y = self.scale_x
            self.offset_x = 0
            self.offset_y = (display_height - (video_height * self.scale_y)) / 2
        else:
            # Video is taller - fit to height
            self.scale_y = display_height / video_height
            self.scale_x = self.scale_y
            self.offset_y = 0
            self.offset_x = (display_width - (video_width * self.scale_x)) / 2
    
    def video_to_display(self, x, y, w, h):
        """Convert video coordinates to display coordinates"""
        return (
            int(x * self.scale_x + self.offset_x),
            int(y * self.scale_y + self.offset_y),
            int(w * self.scale_x),
            int(h * self.scale_y)
        )
    
    def display_to_video(self, x, y):
        """Convert display coordinates to video coordinates"""
        return (
            int((x - self.offset_x) / self.scale_x),
            int((y - self.offset_y) / self.scale_y)
        )
    
    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press - select or start drag"""
        if not self.fields:
            return
        
        pos = event.pos()
        
        # Check if clicking on a resize handle
        for field in self.fields:
            handle = self._get_resize_handle(field, pos)
            if handle:
                self.selected_field = field
                self.is_resizing = True
                self.resize_handle = handle
                self.drag_start_pos = pos
                self.field_selected.emit(field.name)
                self.update()
                return
        
        # Check if clicking inside a field
        for field in reversed(self.fields):  # Top to bottom
            if self._is_inside_field(field, pos):
                self.selected_field = field
                self.is_dragging = True
                self.drag_start_pos = pos
                self.field_selected.emit(field.name)
                self.update()
                return
        
        # Clicked outside - deselect
        self.selected_field = None
        self.update()
    
    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle mouse move - drag or resize"""
        pos = event.pos()
        
        # Update cursor
        cursor_set = False
        for field in self.fields:
            handle = self._get_resize_handle(field, pos)
            if handle:
                if handle in ['tl', 'br']:
                    self.setCursor(Qt.SizeFDiagCursor)
                else:
                    self.setCursor(Qt.SizeBDiagCursor)
                cursor_set = True
                break
            elif self._is_inside_field(field, pos):
                self.setCursor(Qt.OpenHandCursor)
                cursor_set = True
                break
        
        if not cursor_set:
            self.setCursor(Qt.ArrowCursor)
        
        # Handle dragging
        if self.is_dragging and self.selected_field and self.drag_start_pos:
            dx = pos.x() - self.drag_start_pos.x()
            dy = pos.y() - self.drag_start_pos.y()
            
            # Convert to video coordinates
            dx_video = int(dx / self.scale_x)
            dy_video = int(dy / self.scale_y)
            
            # Update field position
            x, y, w, h = self.selected_field.bbox
            new_bbox = (x + dx_video, y + dy_video, w, h)
            self.selected_field.bbox = new_bbox
            
            self.drag_start_pos = pos
            self.field_moved.emit(self.selected_field.name, new_bbox)
            self.update()
        
        # Handle resizing
        elif self.is_resizing and self.selected_field and self.drag_start_pos:
            dx = pos.x() - self.drag_start_pos.x()
            dy = pos.y() - self.drag_start_pos.y()
            
            dx_video = int(dx / self.scale_x)
            dy_video = int(dy / self.scale_y)
            
            x, y, w, h = self.selected_field.bbox
            
            if self.resize_handle == 'br':  # Bottom-right
                new_bbox = (x, y, max(20, w + dx_video), max(20, h + dy_video))
            elif self.resize_handle == 'tr':  # Top-right
                new_bbox = (x, y + dy_video, max(20, w + dx_video), max(20, h - dy_video))
            elif self.resize_handle == 'bl':  # Bottom-left
                new_bbox = (x + dx_video, y, max(20, w - dx_video), max(20, h + dy_video))
            elif self.resize_handle == 'tl':  # Top-left
                new_bbox = (x + dx_video, y + dy_video, max(20, w - dx_video), max(20, h - dy_video))
            
            self.selected_field.bbox = new_bbox
            self.drag_start_pos = pos
            self.field_moved.emit(self.selected_field.name, new_bbox)
            self.update()
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        """Handle mouse release"""
        self.is_dragging = False
        self.is_resizing = False
        self.drag_start_pos = None
        self.resize_handle = None
    
    def _is_inside_field(self, field, pos: QPoint) -> bool:
        """Check if position is inside field bbox"""
        x, y, w, h = self.video_to_display(*field.bbox)
        return x <= pos.x() <= x + w and y <= pos.y() <= y + h
    
    def _get_resize_handle(self, field, pos: QPoint) -> Optional[str]:
        """Check if position is on a resize handle"""
        x, y, w, h = self.video_to_display(*field.bbox)
        hs = self.handle_size
        
        # Check each corner
        if QRect(x - hs, y - hs, hs*2, hs*2).contains(pos):
            return 'tl'
        if QRect(x + w - hs, y - hs, hs*2, hs*2).contains(pos):
            return 'tr'
        if QRect(x - hs, y + h - hs, hs*2, hs*2).contains(pos):
            return 'bl'
        if QRect(x + w - hs, y + h - hs, hs*2, hs*2).contains(pos):
            return 'br'
        
        return None
    
    def paintEvent(self, event):
        """Custom paint to draw fields on top of video"""
        super().paintEvent(event)
        
        if not self.fields:
            return
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        for field in self.fields:
            # Get display coordinates
            x, y, w, h = self.video_to_display(*field.bbox)
            
            # Choose color based on state
            if field == self.selected_field:
                color = self.selected_color
                pen_width = 3
            elif not field.is_visible:
                color = self.lost_color
                pen_width = 2
            else:
                color = self.normal_color
                pen_width = 2
            
            # Draw rectangle
            pen = QPen(color, pen_width)
            painter.setPen(pen)
            painter.drawRect(x, y, w, h)
            
            # Draw handles if selected
            if field == self.selected_field:
                painter.setBrush(QBrush(self.handle_color))
                hs = self.handle_size
                painter.drawRect(x - hs, y - hs, hs*2, hs*2)  # TL
                painter.drawRect(x + w - hs, y - hs, hs*2, hs*2)  # TR
                painter.drawRect(x - hs, y + h - hs, hs*2, hs*2)  # BL
                painter.drawRect(x + w - hs, y + h - hs, hs*2, hs*2)  # BR
            
            # Draw label
            label = f"{field.display_name}: {field.get_output_value() or '...'}"
            painter.setPen(QPen(color, 1))
            painter.drawText(x, y - 5, label)
        
        # Draw Live AI Detections (Elegant Overlay)
        if hasattr(self, 'detections') and self.detections:
            for i, det in enumerate(self.detections):
                x, y, w, h = self.video_to_display(*det['bbox'])
                
                # Dynamic color palette for different classes
                colors = [
                    QColor(0, 255, 255),   # Cyan
                    QColor(255, 255, 0),   # Yellow
                    QColor(255, 0, 255),   # Magenta
                    QColor(0, 255, 0),     # Lime
                    QColor(255, 128, 0),   # Orange
                ]
                base_color = colors[i % len(colors)]
                
                # 1. Draw Bounding Box (Solid with semi-transparent fill)
                box_pen = QPen(base_color, 2)
                painter.setPen(box_pen)
                painter.setBrush(QColor(base_color.red(), base_color.green(), base_color.blue(), 30))
                painter.drawRect(x, y, w, h)
                
                # 2. Draw Label with Background (Post-processing style)
                label_text = f"{det['display_name']} {int(det['confidence']*100)}%"
                font = QFont("Outfit", 9, QFont.Bold)
                painter.setFont(font)
                
                # Calculate text size for background box
                metrics = painter.fontMetrics()
                text_rect = metrics.boundingRect(label_text)
                bg_rect = QRect(x, y - text_rect.height() - 4, text_rect.width() + 10, text_rect.height() + 4)
                
                # Draw label background
                painter.setPen(Qt.NoPen)
                painter.setBrush(base_color)
                painter.drawRect(bg_rect)
                
                # Draw label text (Black/White depending on contrast)
                painter.setPen(QColor(0, 0, 0)) # Clean black text
                painter.drawText(x + 5, y - 5, label_text)
                
                # 3. Draw Corner Accents (Elegant touch)
                line_len = min(w, h, 20) // 2
                painter.setPen(QPen(base_color, 4))
                # TL
                painter.drawLine(x, y, x + line_len, y)
                painter.drawLine(x, y, x, y + line_len)
                # TR
                painter.drawLine(x + w, y, x + w - line_len, y)
                painter.drawLine(x + w, y, x + w, y + line_len)
                # BL
                painter.drawLine(x, y + h, x + line_len, y + h)
                painter.drawLine(x, y + h, x, y + h - line_len)
                # BR
                painter.drawLine(x + w, y + h, x + w - line_len, y + h)
                painter.drawLine(x + w, y + h, x + w, y + h - line_len)
        
        painter.end()
