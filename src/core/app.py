"""
SmartOCR App - Main application controller
"""
import cv2
import numpy as np
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QListWidget,
    QListWidgetItem, QGroupBox, QCheckBox
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap

from src.core.video_reader import VideoReader
from src.fields.field_manager import FieldManager
from src.fields.field_tracker import FieldTracker
from src.ocr.ocr_engine import OCREngine
from src.output.csv_writer import CSVWriter
from src.gui.interactive_video import InteractiveVideoLabel

class SmartOCRApp(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SmartOCR - Scoreboard Reader")
        self.setGeometry(100, 100, 1400, 900)
        
        # Core components
        self.video_reader: VideoReader = None
        self.field_manager = FieldManager()
        self.field_tracker = FieldTracker()
        self.ocr_engine = OCREngine()
        self.csv_writer = CSVWriter()
        
        # State
        self.current_frame = None
        self.is_processing = False
        self.is_recording = False
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QHBoxLayout(central_widget)
        
        # Left panel - Video display
        video_group = QGroupBox("Video")
        video_layout = QVBoxLayout(video_group)
        
        self.video_label = InteractiveVideoLabel()
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setMinimumSize(960, 540)
        self.video_label.setStyleSheet("background-color: #1a1a1a; color: white;")
        self.video_label.field_moved.connect(self.on_field_moved)
        video_layout.addWidget(self.video_label)
        
        # Video controls
        controls_layout = QHBoxLayout()
        
        self.load_btn = QPushButton("Load Video")
        self.load_btn.clicked.connect(self.load_video)
        controls_layout.addWidget(self.load_btn)
        
        self.play_btn = QPushButton("Start")
        self.play_btn.clicked.connect(self.toggle_processing)
        self.play_btn.setEnabled(False)
        controls_layout.addWidget(self.play_btn)
        
        self.record_btn = QPushButton("Start Recording")
        self.record_btn.clicked.connect(self.toggle_recording)
        self.record_btn.setEnabled(False)
        controls_layout.addWidget(self.record_btn)
        
        video_layout.addLayout(controls_layout)
        main_layout.addWidget(video_group, stretch=2)
        
        # Right panel - Fields and output
        right_panel = QVBoxLayout()
        
        # Fields list
        fields_group = QGroupBox("Detection Fields")
        fields_layout = QVBoxLayout(fields_group)
        
        self.fields_list = QListWidget()
        fields_layout.addWidget(self.fields_list)
        
        # Auto-track checkbox
        self.auto_track_checkbox = QCheckBox("Auto-Track Fields")
        self.auto_track_checkbox.setChecked(True)
        fields_layout.addWidget(self.auto_track_checkbox)
        
        # Field controls
        fields_btn_layout = QHBoxLayout()
        
        self.add_field_btn = QPushButton("Add Field")
        self.add_field_btn.clicked.connect(self.add_field)
        fields_btn_layout.addWidget(self.add_field_btn)
        
        self.clear_fields_btn = QPushButton("Clear All")
        self.clear_fields_btn.clicked.connect(self.clear_fields)
        fields_btn_layout.addWidget(self.clear_fields_btn)
        
        fields_layout.addLayout(fields_btn_layout)
        right_panel.addWidget(fields_group)
        
        # Output info
        output_group = QGroupBox("Output")
        output_layout = QVBoxLayout(output_group)
        
        self.output_label = QLabel("CSV: Not recording")
        output_layout.addWidget(self.output_label)
        
        self.csv_path_label = QLabel("")
        self.csv_path_label.setWordWrap(True)
        output_layout.addWidget(self.csv_path_label)
        
        right_panel.addWidget(output_group)
        right_panel.addStretch()
        
        main_layout.addLayout(right_panel, stretch=1)
        
        # Setup frame processing timer
        self.process_timer = QTimer()
        self.process_timer.timeout.connect(self.process_current_frame)
        self.process_timer.start(33)  # ~30fps
    
    def load_video(self):
        """Load video file"""
        path, _ = QFileDialog.getOpenFileName(
            self, "Load Video", "", 
            "Video Files (*.mp4 *.avi *.mkv *.mov);;All Files (*)"
        )
        
        if path:
            self.video_path = path
            
            # Initialize video reader
            if self.video_reader:
                self.video_reader.stop()
            
            self.video_reader = VideoReader(path)
            self.video_reader.frame_ready.connect(self.on_frame_ready)
            self.video_reader.error_signal.connect(self.on_video_error)
            
            # Get first frame to initialize
            cap = cv2.VideoCapture(path)
            ret, frame = cap.read()
            cap.release()
            
            if ret:
                self.current_frame = frame
                h, w = frame.shape[:2]
                
                # Create default fields
                self.field_manager.create_default_fields(w, h)
                self.update_fields_list()
                
                # Display frame
                self.display_frame(frame)
                
                self.play_btn.setEnabled(True)
                self.record_btn.setEnabled(True)
                self.load_btn.setText("Change Video")
    
    def on_frame_ready(self, frame):
        """Handle new video frame"""
        self.current_frame = frame
    
    def on_video_error(self, error_msg):
        """Handle video error"""
        self.video_label.setText(f"Error: {error_msg}")
    
    def toggle_processing(self):
        """Start/stop video processing"""
        if not self.is_processing:
            # Start
            if self.video_reader:
                self.video_reader.start()
                self.is_processing = True
                self.play_btn.setText("Pause")
        else:
            # Pause
            if self.video_reader:
                self.video_reader.stop()
            self.is_processing = False
            self.play_btn.setText("Start")
    
    def toggle_recording(self):
        """Start/stop CSV recording"""
        if not self.is_recording:
            # Start recording
            fieldnames = [f.name for f in self.field_manager.get_all_fields()]
            self.csv_writer.open(fieldnames)
            self.is_recording = True
            self.record_btn.setText("Stop Recording")
            self.output_label.setText("CSV: Recording...")
            self.csv_path_label.setText(f"Output: {self.csv_writer.get_path()}")
        else:
            # Stop recording
            self.csv_writer.close()
            self.is_recording = False
            self.record_btn.setText("Start Recording")
            self.output_label.setText("CSV: Saved")
    
    def process_current_frame(self):
        """Process current frame (OCR + tracking)"""
        if self.current_frame is None:
            return
        
        frame = self.current_frame.copy()
        
        # Track fields if camera moved
        if self.auto_track_checkbox.isChecked():
            self.field_tracker.process_frame(frame, self.field_manager.get_all_fields())
        
        # Process each field
        for field in self.field_manager.get_all_fields():
            x, y, w, h = field.bbox
            
            # Ensure bounds
            frame_h, frame_w = frame.shape[:2]
            x = max(0, min(x, frame_w - w))
            y = max(0, min(y, frame_h - h))
            
            # Extract ROI
            roi = frame[y:y+h, x:x+w]
            
            if roi.size > 0:
                # OCR
                text, confidence = self.ocr_engine.recognize_field(
                    roi, field.field_type.value
                )
                
                # Update field
                field.update_value(text, confidence)
        
        # Update fields list
        self.update_fields_list()
        
        # Update interactive video widget
        self.video_label.set_scale(frame.shape[1], frame.shape[0])
        self.video_label.set_fields(self.field_manager.get_all_fields())
        
        # Write to CSV if recording
        if self.is_recording:
            values = self.field_manager.get_field_values()
            self.csv_writer.write(values)
        
        # Display
        self.display_frame(frame)
    
    def display_frame(self, frame):
        """Display frame in UI"""
        # Convert BGR to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Convert to QImage
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
        
        # Create pixmap and set it
        pixmap = QPixmap.fromImage(qt_image)
        self.video_label.setPixmap(pixmap)
        
        # Trigger repaint to draw fields on top
        self.video_label.update()
    
    def update_fields_list(self):
        """Update fields list widget"""
        self.fields_list.clear()
        
        for field in self.field_manager.get_all_fields():
            value = field.get_output_value() or "..."
            status = "✓" if field.is_visible else "✗"
            item_text = f"{status} {field.display_name}: {value}"
            
            item = QListWidgetItem(item_text)
            if not field.is_visible:
                item.setForeground(Qt.red)
            
            self.fields_list.addItem(item)
    
    def add_field(self):
        """Add a new field (simplified - would open dialog)"""
        # For now, just add a default field
        import random
        x = random.randint(100, 500)
        y = random.randint(100, 300)
        
        self.field_manager.add_field(
            f"field_{len(self.field_manager.fields)}",
            "New Field",
            (x, y, 100, 60),
        )
        self.update_fields_list()
    
    def clear_fields(self):
        """Clear all fields"""
        self.field_manager.fields.clear()
        self.field_manager.field_order.clear()
        self.update_fields_list()
    
    def on_field_moved(self, field_name, new_bbox):
        """Handle field being moved by user"""
        self.field_manager.update_field_position(field_name, new_bbox)
        # Update template for tracker
        field = self.field_manager.get_field(field_name)
        if field and self.current_frame is not None:
            x, y, w, h = new_bbox
            frame_h, frame_w = self.current_frame.shape[:2]
            x = max(0, min(x, frame_w - w))
            y = max(0, min(y, frame_h - h))
            template = self.current_frame[y:y+h, x:x+w].copy()
            field.set_template(template)
    
    def closeEvent(self, event):
        """Clean up on close"""
        if self.video_reader:
            self.video_reader.stop()
        if self.is_recording:
            self.csv_writer.close()
        event.accept()
