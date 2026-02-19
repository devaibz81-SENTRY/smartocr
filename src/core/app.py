"""
SmartOCR App - Optimized with YOLO and HTTP Server
"""
import cv2
import numpy as np
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QListWidget,
    QListWidgetItem, QGroupBox, QCheckBox, QSlider,
    QProgressBar, QSplitter, QFrame
)
from PySide6.QtCore import Qt, QTimer, QThread, Signal
from PySide6.QtGui import QImage, QPixmap

from src.core.video_reader import VideoReader
from src.fields.field_manager import FieldManager
from src.fields.field_tracker import FieldTracker
from src.ocr.ocr_engine import OCREngine
from src.output.csv_writer import CSVWriter
from src.gui.interactive_video import InteractiveVideoLabel
from src.yolo.field_detector import YOLOFieldDetector
from src.http.server import HTTPServerThread

class ProcessingThread(QThread):
    """Separate thread for video processing to keep UI smooth"""
    frame_processed = Signal(np.ndarray, dict)
    
    def __init__(self, field_manager, field_tracker, ocr_engine):
        super().__init__()
        self.field_manager = field_manager
        self.field_tracker = field_tracker
        self.ocr_engine = ocr_engine
        self.current_frame = None
        self.is_running = False
        self.frame_count = 0
        self.process_every_n_frames = 2  # OCR every 2nd frame for performance
    
    def set_frame(self, frame):
        self.current_frame = frame
    
    def run(self):
        self.is_running = True
        while self.is_running:
            if self.current_frame is not None:
                frame = self.current_frame.copy()
                self.frame_count += 1
                
                # Track fields
                self.field_tracker.process_frame(frame, self.field_manager.get_all_fields())
                
                # OCR only every N frames for performance
                if self.frame_count % self.process_every_n_frames == 0:
                    for field in self.field_manager.get_all_fields():
                        x, y, w, h = field.bbox
                        frame_h, frame_w = frame.shape[:2]
                        x = max(0, min(x, frame_w - w))
                        y = max(0, min(y, frame_h - h))
                        
                        roi = frame[y:y+h, x:x+w]
                        if roi.size > 0:
                            text, confidence = self.ocr_engine.recognize_field(
                                roi, field.field_type.value
                            )
                            field.update_value(text, confidence)
                
                # Get field values for output
                values = self.field_manager.get_field_values()
                self.frame_processed.emit(frame, values)
            
            self.msleep(33)  # ~30fps
    
    def stop(self):
        self.is_running = False
        self.wait()

class SmartOCRApp(QMainWindow):
    """Main application window with optimizations"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SmartOCR - Scoreboard Reader (Optimized)")
        self.setGeometry(100, 100, 1600, 900)
        
        # Core components
        self.video_reader = None
        self.processing_thread = None
        self.field_manager = FieldManager()
        self.field_tracker = FieldTracker()
        self.ocr_engine = OCREngine()
        self.csv_writer = CSVWriter()
        self.yolo_detector = None
        self.http_server = None
        
        # State
        self.current_frame = None
        self.is_processing = False
        self.is_recording = False
        self.video_width = 960
        self.video_height = 540
        
        self.setup_ui()
        self.start_http_server()
    
    def setup_ui(self):
        """Setup optimized UI"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main horizontal splitter
        splitter = QSplitter(Qt.Horizontal)
        
        # Left panel - Video (fixed size)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # Video container with fixed aspect ratio
        video_container = QFrame()
        video_container.setFrameStyle(QFrame.StyledPanel)
        video_container.setFixedSize(960, 600)
        video_layout = QVBoxLayout(video_container)
        video_layout.setContentsMargins(2, 2, 2, 2)
        
        self.video_label = InteractiveVideoLabel()
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setMinimumSize(956, 540)
        self.video_label.setMaximumSize(956, 540)
        self.video_label.setStyleSheet("background-color: #000000;")
        self.video_label.field_moved.connect(self.on_field_moved)
        video_layout.addWidget(self.video_label)
        
        left_layout.addWidget(video_container)
        
        # Video controls
        controls_frame = QFrame()
        controls_layout = QHBoxLayout(controls_frame)
        
        self.load_btn = QPushButton("📁 Load Video")
        self.load_btn.setStyleSheet("font-size: 12px; padding: 5px;")
        self.load_btn.clicked.connect(self.load_video)
        controls_layout.addWidget(self.load_btn)
        
        self.play_btn = QPushButton("▶️ Play")
        self.play_btn.setEnabled(False)
        self.play_btn.setStyleSheet("font-size: 12px; padding: 5px;")
        self.play_btn.clicked.connect(self.toggle_playback)
        controls_layout.addWidget(self.play_btn)
        
        self.pause_btn = QPushButton("⏸️ Pause")
        self.pause_btn.setEnabled(False)
        self.pause_btn.setStyleSheet("font-size: 12px; padding: 5px;")
        self.pause_btn.clicked.connect(self.pause_video)
        controls_layout.addWidget(self.pause_btn)
        
        self.record_btn = QPushButton("🔴 Start Recording")
        self.record_btn.setEnabled(False)
        self.record_btn.setStyleSheet("font-size: 12px; padding: 5px;")
        self.record_btn.clicked.connect(self.toggle_recording)
        controls_layout.addWidget(self.record_btn)
        
        left_layout.addWidget(controls_frame)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        left_layout.addWidget(self.progress_bar)
        
        # Time slider
        self.time_slider = QSlider(Qt.Horizontal)
        self.time_slider.setRange(0, 100)
        self.time_slider.setEnabled(False)
        self.time_slider.sliderReleased.connect(self.seek_video)
        left_layout.addWidget(self.time_slider)
        
        splitter.addWidget(left_panel)
        
        # Right panel - Controls
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # YOLO Detection
        yolo_group = QGroupBox("YOLO Auto-Detection")
        yolo_layout = QVBoxLayout(yolo_group)
        
        self.detect_btn = QPushButton("🔍 Auto-Detect Scoreboard")
        self.detect_btn.clicked.connect(self.auto_detect_fields)
        self.detect_btn.setEnabled(False)
        yolo_layout.addWidget(self.detect_btn)
        
        self.yolo_status = QLabel("YOLO: Not loaded")
        yolo_layout.addWidget(self.yolo_status)
        
        right_layout.addWidget(yolo_group)
        
        # Fields list
        fields_group = QGroupBox("Detection Fields")
        fields_layout = QVBoxLayout(fields_group)
        
        self.fields_list = QListWidget()
        fields_layout.addWidget(self.fields_list)
        
        # Field controls
        self.auto_track_checkbox = QCheckBox("Auto-Track Fields")
        self.auto_track_checkbox.setChecked(True)
        fields_layout.addWidget(self.auto_track_checkbox)
        
        fields_btn_layout = QHBoxLayout()
        self.add_field_btn = QPushButton("➕ Add Field")
        self.add_field_btn.clicked.connect(self.add_field)
        fields_btn_layout.addWidget(self.add_field_btn)
        
        self.clear_fields_btn = QPushButton("🗑️ Clear All")
        self.clear_fields_btn.clicked.connect(self.clear_fields)
        fields_btn_layout.addWidget(self.clear_fields_btn)
        
        fields_layout.addLayout(fields_btn_layout)
        right_layout.addWidget(fields_group)
        
        # Output info
        output_group = QGroupBox("Output")
        output_layout = QVBoxLayout(output_group)
        
        self.output_label = QLabel("CSV: Not recording")
        output_layout.addWidget(self.output_label)
        
        self.csv_path_label = QLabel("")
        self.csv_path_label.setWordWrap(True)
        output_layout.addWidget(self.csv_path_label)
        
        # HTTP Server status
        self.http_status = QLabel("HTTP Server: http://localhost:8080")
        self.http_status.setStyleSheet("color: green;")
        output_layout.addWidget(self.http_status)
        
        right_layout.addWidget(output_group)
        right_layout.addStretch()
        
        splitter.addWidget(right_panel)
        splitter.setSizes([1000, 400])
        
        # Set main layout
        main_layout = QHBoxLayout(central_widget)
        main_layout.addWidget(splitter)
    
    def start_http_server(self):
        """Start HTTP server for localhost output"""
        try:
            self.http_server = HTTPServerThread(self.field_manager)
            self.http_server.start()
        except Exception as e:
            print(f"HTTP Server error: {e}")
    
    def load_video(self):
        """Load video file"""
        path, _ = QFileDialog.getOpenFileName(
            self, "Load Video", "",
            "Video Files (*.mp4 *.avi *.mkv *.mov);;All Files (*)"
        )
        
        if path:
            self.video_path = path
            
            # Stop existing
            if self.video_reader:
                self.video_reader.stop()
            if self.processing_thread:
                self.processing_thread.stop()
            
            # Initialize video
            self.video_reader = VideoReader(path)
            self.video_reader.frame_ready.connect(self.on_frame_ready)
            self.video_reader.finished_signal.connect(self.on_video_finished)
            
            # Get video info
            cap = cv2.VideoCapture(path)
            ret, frame = cap.read()
            if ret:
                self.current_frame = frame
                self.video_height, self.video_width = frame.shape[:2]
                fps = cap.get(cv2.CAP_PROP_FPS)
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                
                # Setup UI
                self.time_slider.setRange(0, total_frames)
                self.time_slider.setEnabled(True)
                
                # Create default fields
                self.field_manager.create_default_fields(self.video_width, self.video_height)
                self.update_fields_list()
                
                # Display first frame
                self.display_frame(frame)
                
                # Enable controls
                self.play_btn.setEnabled(True)
                self.record_btn.setEnabled(True)
                self.detect_btn.setEnabled(True)
                self.load_btn.setText("📁 Change Video")
                
                # Start processing thread
                self.processing_thread = ProcessingThread(
                    self.field_manager, self.field_tracker, self.ocr_engine
                )
                self.processing_thread.frame_processed.connect(self.on_frame_processed)
            
            cap.release()
    
    def on_frame_ready(self, frame):
        """Receive frame from video reader"""
        self.current_frame = frame
        if self.processing_thread:
            self.processing_thread.set_frame(frame)
        
        # Update progress
        if self.video_reader:
            progress = self.video_reader.get_progress()
            self.progress_bar.setValue(int(progress))
            self.time_slider.setValue(self.video_reader.current_frame)
    
    def on_frame_processed(self, frame, values):
        """Receive processed frame"""
        self.display_frame(frame)
        self.update_fields_list()
        
        # Update HTTP server data
        if self.http_server:
            self.http_server.update_data(values)
        
        # Write CSV
        if self.is_recording:
            self.csv_writer.write(values)
    
    def display_frame(self, frame):
        """Display frame with locked size"""
        # Resize to fixed display size
        display_frame = cv2.resize(frame, (956, 540), interpolation=cv2.INTER_LINEAR)
        
        # Convert to RGB
        rgb_frame = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
        
        # Create QImage
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
        
        # Set pixmap
        pixmap = QPixmap.fromImage(qt_image)
        self.video_label.setPixmap(pixmap)
        self.video_label.set_scale(956, 540)
        self.video_label.set_fields(self.field_manager.get_all_fields())
        self.video_label.update()
    
    def toggle_playback(self):
        """Start video playback"""
        if self.video_reader and not self.is_processing:
            self.video_reader.start()
            self.processing_thread.start()
            self.is_processing = True
            self.play_btn.setEnabled(False)
            self.pause_btn.setEnabled(True)
    
    def pause_video(self):
        """Pause video"""
        if self.video_reader:
            self.video_reader.stop()
            self.processing_thread.stop()
            self.is_processing = False
            self.play_btn.setEnabled(True)
            self.pause_btn.setEnabled(False)
    
    def seek_video(self):
        """Seek to slider position"""
        if self.video_reader:
            frame_num = self.time_slider.value()
            self.video_reader.seek(frame_num)
    
    def on_video_finished(self):
        """Handle video end"""
        self.is_processing = False
        self.play_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
    
    def auto_detect_fields(self):
        """Use YOLO to auto-detect scoreboard fields"""
        if not self.yolo_detector:
            # Initialize YOLO
            try:
                self.yolo_detector = YOLOFieldDetector(
                    r"C:\Users\suppo\Documents\YOLO BUILD\YOLOv8-Object-Detection-on-Video-with-OpenCV-main"
                )
                self.yolo_status.setText("YOLO: Loaded ✓")
                self.yolo_status.setStyleSheet("color: green;")
            except Exception as e:
                self.yolo_status.setText(f"YOLO Error: {e}")
                return
        
        if self.current_frame is not None:
            # Detect fields
            detections = self.yolo_detector.detect(self.current_frame)
            
            # Clear existing fields
            self.field_manager.fields.clear()
            self.field_manager.field_order.clear()
            
            # Add detected fields
            for det in detections:
                self.field_manager.add_field(
                    det['name'],
                    det['display_name'],
                    det['bbox'],
                    det['field_type']
                )
            
            self.update_fields_list()
    
    def toggle_recording(self):
        """Start/stop CSV recording"""
        if not self.is_recording:
            fieldnames = [f.name for f in self.field_manager.get_all_fields()]
            self.csv_writer.open(fieldnames)
            self.is_recording = True
            self.record_btn.setText("⏹️ Stop Recording")
            self.output_label.setText("CSV: Recording...")
            self.csv_path_label.setText(f"Output: {self.csv_writer.get_path()}")
        else:
            self.csv_writer.close()
            self.is_recording = False
            self.record_btn.setText("🔴 Start Recording")
            self.output_label.setText("CSV: Saved ✓")
    
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
        """Add a new field"""
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
        """Handle field being moved"""
        self.field_manager.update_field_position(field_name, new_bbox)
        field = self.field_manager.get_field(field_name)
        if field and self.current_frame is not None:
            x, y, w, h = new_bbox
            frame_h, frame_w = self.current_frame.shape[:2]
            x = max(0, min(x, frame_w - w))
            y = max(0, min(y, frame_h - h))
            template = self.current_frame[y:y+h, x:x+w].copy()
            field.set_template(template)
    
    def closeEvent(self, event):
        """Clean up"""
        if self.video_reader:
            self.video_reader.stop()
        if self.processing_thread:
            self.processing_thread.stop()
        if self.http_server:
            self.http_server.stop()
        if self.is_recording:
            self.csv_writer.close()
        event.accept()
