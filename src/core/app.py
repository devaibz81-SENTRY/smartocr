"""
SmartOCR App - Full System with Live Video I/O and ScoreSight UI
"""
import cv2
import numpy as np
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QListWidget,
    QListWidgetItem, QGroupBox, QCheckBox, QSlider,
    QProgressBar, QSplitter, QFrame, QTabWidget,
    QComboBox, QLineEdit, QMessageBox, QSpinBox,
    QDoubleSpinBox, QScrollArea
)
from PySide6.QtCore import Qt, QTimer, QThread, Signal
from PySide6.QtGui import QImage, QPixmap, QFont

from src.core.video_reader import VideoReader
from src.fields.field_manager import FieldManager
from src.fields.field_tracker import FieldTracker
from src.ocr.ocr_engine import OCREngine
from src.output.csv_writer import CSVWriter
from src.output.ndi_output import NDIOutput
from src.output.xml_output import XMLOutput
from src.gui.interactive_video import InteractiveVideoLabel
from src.yolo.field_detector import YOLOFieldDetector
from src.http.server import HTTPServerThread
from src.input.ndi_capture import NDICapture
from src.input.stream_capture import StreamCapture
from src.input.usb_camera import USBCameraCapture

class ProcessingThread(QThread):
    """Separate thread for video processing"""
    frame_processed = Signal(np.ndarray, dict)
    
    def __init__(self, field_manager, field_tracker, ocr_engine):
        super().__init__()
        self.field_manager = field_manager
        self.field_tracker = field_tracker
        self.ocr_engine = ocr_engine
        self.current_frame = None
        self.is_running = False
        self.frame_count = 0
        self.process_every_n_frames = 2
    
    def set_frame(self, frame):
        self.current_frame = frame
    
    def run(self):
        self.is_running = True
        while self.is_running:
            if self.current_frame is not None:
                frame = self.current_frame.copy()
                self.frame_count += 1
                
                self.field_tracker.process_frame(frame, self.field_manager.get_all_fields())
                
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
                
                values = self.field_manager.get_field_values()
                self.frame_processed.emit(frame, values)
            
            self.msleep(33)
    
    def stop(self):
        self.is_running = False
        self.wait()

class SmartOCRApp(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SmartOCR - Live Scoreboard OCR")
        self.setGeometry(100, 100, 1800, 1000)
        
        # Core components
        self.video_reader = None
        self.ndi_capture = None
        self.stream_capture = None
        self.usb_capture = None
        self.processing_thread = None
        self.field_manager = FieldManager()
        self.field_tracker = FieldTracker()
        self.ocr_engine = OCREngine()
        self.csv_writer = CSVWriter()
        self.xml_output = XMLOutput()
        self.ndi_output = None
        self.yolo_detector = None
        self.http_server = None
        
        # State
        self.current_frame = None
        self.is_processing = False
        self.is_recording = False
        self.video_width = 960
        self.video_height = 540
        self.current_source_type = "file"  # file, ndi, stream
        
        self.setup_ui()
        self.start_http_server()
        self.refresh_ndi_sources()
    
    def setup_ui(self):
        """Setup comprehensive UI"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QHBoxLayout(central_widget)
        
        # Horizontal splitter
        splitter = QSplitter(Qt.Horizontal)
        
        # Left panel - Video and Source Selection
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(5, 5, 5, 5)
        
        # Source Selection Tabs (ScoreSight style)
        source_tabs = QTabWidget()
        source_tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #444; }
            QTabBar::tab { padding: 10px 20px; font-size: 12px; }
        """)
        
        # Tab 1: File
        file_tab = QWidget()
        file_layout = QVBoxLayout(file_tab)
        self.file_btn = QPushButton("📁 Browse Video File")
        self.file_btn.setStyleSheet("font-size: 14px; padding: 10px;")
        self.file_btn.clicked.connect(self.load_video_file)
        file_layout.addWidget(self.file_btn)
        file_layout.addStretch()
        source_tabs.addTab(file_tab, "📹 File")
        
        # Tab 2: NDI
        ndi_tab = QWidget()
        ndi_layout = QVBoxLayout(ndi_tab)
        
        ndi_top = QHBoxLayout()
        self.ndi_refresh_btn = QPushButton("🔄 Refresh")
        self.ndi_refresh_btn.clicked.connect(self.refresh_ndi_sources)
        ndi_top.addWidget(self.ndi_refresh_btn)
        ndi_layout.addLayout(ndi_top)
        
        self.ndi_combo = QComboBox()
        self.ndi_combo.setStyleSheet("font-size: 12px; padding: 5px;")
        self.ndi_combo.addItem("Click Refresh to find NDI sources...")
        ndi_layout.addWidget(QLabel("NDI Sources (Auto-discover):"))
        ndi_layout.addWidget(self.ndi_combo)
        
        # IP Address input for manual connection
        ndi_layout.addWidget(QLabel("OR Connect by IP:"))
        self.ndi_ip_input = QLineEdit()
        self.ndi_ip_input.setPlaceholderText("10.10.10.161 or 10.10.10.161:5960")
        self.ndi_ip_input.setStyleSheet("font-size: 12px; padding: 5px;")
        ndi_layout.addWidget(self.ndi_ip_input)
        
        ip_help = QLabel("Enter IP address of NDI device (e.g., 10.10.10.161)")
        ip_help.setStyleSheet("font-size: 10px; color: #666;")
        ndi_layout.addWidget(ip_help)
        
        self.ndi_connect_btn = QPushButton("🔗 Connect NDI")
        self.ndi_connect_btn.setStyleSheet("font-size: 14px; padding: 10px; background-color: #4CAF50;")
        self.ndi_connect_btn.clicked.connect(self.connect_ndi)
        ndi_layout.addWidget(self.ndi_connect_btn)
        ndi_layout.addStretch()
        source_tabs.addTab(ndi_tab, "📡 NDI")
        
        # Tab 3: Stream
        stream_tab = QWidget()
        stream_layout = QVBoxLayout(stream_tab)
        
        stream_layout.addWidget(QLabel("Stream URL:"))
        self.stream_url = QLineEdit()
        self.stream_url.setPlaceholderText("srt://192.168.1.100:8080 or rtsp://...")
        self.stream_url.setStyleSheet("font-size: 12px; padding: 5px;")
        stream_layout.addWidget(self.stream_url)
        
        presets = QHBoxLayout()
        srt_preset = QPushButton("SRT Preset")
        srt_preset.clicked.connect(lambda: self.stream_url.setText("srt://0.0.0.0:8080"))
        presets.addWidget(srt_preset)
        
        rtsp_preset = QPushButton("RTSP Preset")
        rtsp_preset.clicked.connect(lambda: self.stream_url.setText("rtsp://username:password@ip:554/stream"))
        presets.addWidget(rtsp_preset)
        stream_layout.addLayout(presets)
        
        self.stream_connect_btn = QPushButton("🔗 Connect Stream")
        self.stream_connect_btn.setStyleSheet("font-size: 14px; padding: 10px; background-color: #2196F3;")
        self.stream_connect_btn.clicked.connect(self.connect_stream)
        stream_layout.addWidget(self.stream_connect_btn)
        stream_layout.addStretch()
        source_tabs.addTab(stream_tab, "🌐 Stream")
        
        # Tab 4: USB Camera
        usb_tab = QWidget()
        usb_layout = QVBoxLayout(usb_tab)
        
        usb_top = QHBoxLayout()
        self.usb_refresh_btn = QPushButton("🔄 Refresh")
        self.usb_refresh_btn.clicked.connect(self.refresh_usb_cameras)
        usb_top.addWidget(self.usb_refresh_btn)
        usb_layout.addLayout(usb_top)
        
        self.usb_combo = QComboBox()
        self.usb_combo.setStyleSheet("font-size: 12px; padding: 5px;")
        self.usb_combo.addItem("Click Refresh to find USB cameras...")
        usb_layout.addWidget(QLabel("USB Cameras:"))
        usb_layout.addWidget(self.usb_combo)
        
        # Resolution selector
        usb_layout.addWidget(QLabel("Resolution:"))
        self.usb_resolution = QComboBox()
        self.usb_resolution.addItems(["1920x1080", "1280x720", "640x480", "320x240"])
        self.usb_resolution.setCurrentIndex(1)  # Default to 720p
        usb_layout.addWidget(self.usb_resolution)
        
        self.usb_connect_btn = QPushButton("📷 Connect Camera")
        self.usb_connect_btn.setStyleSheet("font-size: 14px; padding: 10px; background-color: #FF9800;")
        self.usb_connect_btn.clicked.connect(self.connect_usb_camera)
        usb_layout.addWidget(self.usb_connect_btn)
        usb_layout.addStretch()
        source_tabs.addTab(usb_tab, "📷 USB")
        
        left_layout.addWidget(source_tabs)
        
        # Video display container (fixed size)
        video_container = QFrame()
        video_container.setFrameStyle(QFrame.StyledPanel)
        video_container.setFixedSize(960, 600)
        video_container.setStyleSheet("background-color: #000000;")
        video_layout = QVBoxLayout(video_container)
        video_layout.setContentsMargins(2, 2, 2, 2)
        
        self.video_label = InteractiveVideoLabel()
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setMinimumSize(956, 540)
        self.video_label.setMaximumSize(956, 540)
        self.video_label.field_moved.connect(self.on_field_moved)
        video_layout.addWidget(self.video_label)
        
        left_layout.addWidget(video_container)
        
        # Playback controls
        controls_frame = QFrame()
        controls_layout = QHBoxLayout(controls_frame)
        
        self.play_btn = QPushButton("▶️ Play")
        self.play_btn.setEnabled(False)
        self.play_btn.setStyleSheet("font-size: 14px; padding: 8px; min-width: 80px;")
        self.play_btn.clicked.connect(self.toggle_playback)
        controls_layout.addWidget(self.play_btn)
        
        self.pause_btn = QPushButton("⏸️ Pause")
        self.pause_btn.setEnabled(False)
        self.pause_btn.setStyleSheet("font-size: 14px; padding: 8px; min-width: 80px;")
        self.pause_btn.clicked.connect(self.pause_video)
        controls_layout.addWidget(self.pause_btn)
        
        self.record_btn = QPushButton("🔴 Record")
        self.record_btn.setEnabled(False)
        self.record_btn.setStyleSheet("font-size: 14px; padding: 8px; min-width: 80px;")
        self.record_btn.clicked.connect(self.toggle_recording)
        controls_layout.addWidget(self.record_btn)
        
        controls_layout.addStretch()
        
        # NDI Output toggle
        self.ndi_out_btn = QPushButton("📤 NDI Out: OFF")
        self.ndi_out_btn.setCheckable(True)
        self.ndi_out_btn.clicked.connect(self.toggle_ndi_output)
        controls_layout.addWidget(self.ndi_out_btn)
        
        left_layout.addWidget(controls_frame)
        
        # Progress and timeline
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        left_layout.addWidget(self.progress_bar)
        
        self.time_slider = QSlider(Qt.Horizontal)
        self.time_slider.setRange(0, 100)
        self.time_slider.setEnabled(False)
        self.time_slider.sliderReleased.connect(self.seek_video)
        left_layout.addWidget(self.time_slider)
        
        splitter.addWidget(left_panel)
        
        # Right panel - Controls (ScoreSight style)
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(10, 10, 10, 10)
        
        # Status section
        status_group = QGroupBox("Status")
        status_layout = QVBoxLayout(status_group)
        
        self.source_status = QLabel("Source: Not connected")
        self.source_status.setStyleSheet("font-size: 12px; color: #666;")
        status_layout.addWidget(self.source_status)
        
        self.fps_label = QLabel("FPS: 0")
        self.fps_label.setStyleSheet("font-size: 12px; color: #666;")
        status_layout.addWidget(self.fps_label)
        
        right_layout.addWidget(status_group)
        
        # YOLO Detection section
        yolo_group = QGroupBox("🤖 YOLO Auto-Detection")
        yolo_layout = QVBoxLayout(yolo_group)
        
        self.detect_btn = QPushButton("🔍 Auto-Detect Fields")
        self.detect_btn.setStyleSheet("font-size: 13px; padding: 8px;")
        self.detect_btn.clicked.connect(self.auto_detect_fields)
        self.detect_btn.setEnabled(False)
        yolo_layout.addWidget(self.detect_btn)
        
        self.yolo_status = QLabel("Status: Not loaded")
        self.yolo_status.setStyleSheet("font-size: 11px; color: #888;")
        yolo_layout.addWidget(self.yolo_status)
        
        yolo_info = QLabel("Train YOLO on labeled images for automatic detection")
        yolo_info.setStyleSheet("font-size: 10px; color: #666; font-style: italic;")
        yolo_info.setWordWrap(True)
        yolo_layout.addWidget(yolo_info)
        
        right_layout.addWidget(yolo_group)
        
        # Fields section (ScoreSight style)
        fields_group = QGroupBox("📝 Detection Fields")
        fields_layout = QVBoxLayout(fields_group)
        
        self.fields_list = QListWidget()
        self.fields_list.setStyleSheet("font-size: 12px;")
        fields_layout.addWidget(self.fields_list)
        
        # Field controls
        field_btns = QHBoxLayout()
        self.add_field_btn = QPushButton("➕ Add")
        self.add_field_btn.clicked.connect(self.add_field)
        field_btns.addWidget(self.add_field_btn)
        
        self.clear_fields_btn = QPushButton("🗑️ Clear")
        self.clear_fields_btn.clicked.connect(self.clear_fields)
        field_btns.addWidget(self.clear_fields_btn)
        fields_layout.addLayout(field_btns)
        
        # Auto-track
        self.auto_track_checkbox = QCheckBox("Auto-Track Fields")
        self.auto_track_checkbox.setChecked(True)
        self.auto_track_checkbox.setStyleSheet("font-size: 11px;")
        fields_layout.addWidget(self.auto_track_checkbox)
        
        right_layout.addWidget(fields_group)
        
        # Output section
        output_group = QGroupBox("📤 Output")
        output_layout = QVBoxLayout(output_group)
        
        self.output_label = QLabel("Output: Not recording")
        self.output_label.setStyleSheet("font-size: 12px;")
        output_layout.addWidget(self.output_label)
        
        self.csv_path_label = QLabel("")
        self.csv_path_label.setWordWrap(True)
        self.csv_path_label.setStyleSheet("font-size: 10px; color: #666;")
        output_layout.addWidget(self.csv_path_label)
        
        self.xml_path_label = QLabel("")
        self.xml_path_label.setWordWrap(True)
        self.xml_path_label.setStyleSheet("font-size: 10px; color: #666;")
        output_layout.addWidget(self.xml_path_label)
        
        # HTTP Server info
        http_frame = QFrame()
        http_frame.setStyleSheet("background-color: #f0f0f0; padding: 5px; border-radius: 3px;")
        http_layout = QVBoxLayout(http_frame)
        
        http_title = QLabel("🌐 HTTP Server")
        http_title.setStyleSheet("font-weight: bold; font-size: 11px;")
        http_layout.addWidget(http_title)
        
        http_urls = QLabel("http://localhost:8080<br>http://localhost:8080/json<br>http://localhost:8080/xml")
        http_urls.setStyleSheet("font-size: 10px; color: #2196F3;")
        http_layout.addWidget(http_urls)
        
        output_layout.addWidget(http_frame)
        
        right_layout.addWidget(output_group)
        right_layout.addStretch()
        
        right_scroll.setWidget(right_panel)
        splitter.addWidget(right_scroll)
        splitter.setSizes([1100, 500])
        
        main_layout.addWidget(splitter)
        
        # FPS counter timer
        self.fps_timer = QTimer()
        self.fps_timer.timeout.connect(self.update_fps)
        self.fps_timer.start(1000)
        self.frame_count_display = 0
    
    def start_http_server(self):
        """Start HTTP server"""
        try:
            self.http_server = HTTPServerThread(self.field_manager)
            self.http_server.start()
        except Exception as e:
            print(f"HTTP Server error: {e}")
    
    def refresh_ndi_sources(self):
        """Refresh NDI source list"""
        try:
            sources = NDICapture.get_sources()
            self.ndi_combo.clear()
            
            if sources:
                self.ndi_combo.addItems(sources)
                self.yolo_status.setText("NDI sources found")
            else:
                self.ndi_combo.addItem("No NDI sources found")
                self.yolo_status.setText("No NDI sources")
        except Exception as e:
            self.ndi_combo.clear()
            self.ndi_combo.addItem(f"Error: {e}")
    
    def load_video_file(self):
        """Load video file"""
        path, _ = QFileDialog.getOpenFileName(
            self, "Load Video", "",
            "Video Files (*.mp4 *.avi *.mkv *.mov);;All Files (*)"
        )
        
        if path:
            self.current_source_type = "file"
            self.setup_video_source(path)
    
    def connect_ndi(self):
        """Connect to NDI source by name or IP"""
        # Check if IP address is provided
        ip_address = self.ndi_ip_input.text().strip()
        source_name = self.ndi_combo.currentText()
        
        self.current_source_type = "ndi"
        
        # Stop existing
        self.stop_current_source()
        
        # Start NDI capture
        try:
            if ip_address:
                # Connect by IP
                self.ndi_capture = NDICapture(ip_address=ip_address)
                display_name = f"IP: {ip_address}"
            elif source_name and source_name != "No NDI sources found" and source_name != "Click Refresh to find NDI sources...":
                # Connect by discovered source name
                self.ndi_capture = NDICapture(source_name=source_name)
                display_name = source_name
            else:
                QMessageBox.warning(self, "No NDI Source", "Please select an NDI source from the dropdown or enter an IP address.")
                return
            
            self.ndi_capture.frame_ready.connect(self.on_frame_ready)
            self.ndi_capture.error_signal.connect(self.on_source_error)
            self.ndi_capture.start()
            
            self.source_status.setText(f"Source: NDI - {display_name}")
            self.source_status.setStyleSheet("color: #4CAF50;")
            self.enable_playback_controls()
            
        except Exception as e:
            QMessageBox.critical(self, "NDI Error", f"Failed to connect: {str(e)}\n\nMake sure cyndilib is installed:\npip install cyndilib")
    
    def connect_stream(self):
        """Connect to network stream"""
        url = self.stream_url.text().strip()
        if url:
            self.current_source_type = "stream"
            
            # Stop existing
            self.stop_current_source()
            
            # Start stream capture
            try:
                self.stream_capture = StreamCapture(url)
                self.stream_capture.frame_ready.connect(self.on_frame_ready)
                self.stream_capture.error_signal.connect(self.on_source_error)
                self.stream_capture.start()
                
                self.source_status.setText(f"Source: Stream - {url}")
                self.source_status.setStyleSheet("color: #2196F3;")
                self.enable_playback_controls()
                
            except Exception as e:
                QMessageBox.critical(self, "Stream Error", str(e))
    
    def refresh_usb_cameras(self):
        """Refresh USB camera list"""
        try:
            cameras = USBCameraCapture.list_cameras()
            self.usb_combo.clear()
            
            if cameras:
                for cam in cameras:
                    self.usb_combo.addItem(cam['name'], cam['index'])
                self.yolo_status.setText(f"Found {len(cameras)} USB camera(s)")
            else:
                self.usb_combo.addItem("No USB cameras found")
                self.yolo_status.setText("No USB cameras detected")
        except Exception as e:
            self.usb_combo.clear()
            self.usb_combo.addItem(f"Error: {e}")
    
    def connect_usb_camera(self):
        """Connect to USB camera"""
        camera_idx = self.usb_combo.currentData()
        if camera_idx is None:
            QMessageBox.warning(self, "No Camera", "Please select a camera first")
            return
        
        # Parse resolution
        res_text = self.usb_resolution.currentText()
        width, height = map(int, res_text.split('x'))
        
        self.current_source_type = "usb"
        
        # Stop existing
        self.stop_current_source()
        
        # Start USB capture
        try:
            self.usb_capture = USBCameraCapture(camera_idx, width, height)
            self.usb_capture.frame_ready.connect(self.on_frame_ready)
            self.usb_capture.error_signal.connect(self.on_source_error)
            self.usb_capture.start()
            
            self.source_status.setText(f"Source: USB Camera {camera_idx} ({width}x{height})")
            self.source_status.setStyleSheet("color: #FF9800;")
            self.enable_playback_controls()
            
        except Exception as e:
            QMessageBox.critical(self, "Camera Error", str(e))
    
    def setup_video_source(self, path):
        """Setup video file source"""
        self.stop_current_source()
        
        self.video_reader = VideoReader(path)
        self.video_reader.frame_ready.connect(self.on_frame_ready)
        self.video_reader.finished_signal.connect(self.on_video_finished)
        
        # Get first frame
        cap = cv2.VideoCapture(path)
        ret, frame = cap.read()
        if ret:
            self.current_frame = frame
            self.video_height, self.video_width = frame.shape[:2]
            
            # Create default fields
            self.field_manager.create_default_fields(self.video_width, self.video_height)
            self.update_fields_list()
            
            # Display first frame
            self.display_frame(frame)
            
            self.source_status.setText(f"Source: File - {path.split('/')[-1]}")
            self.source_status.setStyleSheet("color: #666;")
            self.enable_playback_controls()
        
        cap.release()
    
    def stop_current_source(self):
        """Stop current video source"""
        if self.video_reader:
            self.video_reader.stop()
            self.video_reader = None
        if self.ndi_capture:
            self.ndi_capture.stop()
            self.ndi_capture = None
        if self.stream_capture:
            self.stream_capture.stop()
            self.stream_capture = None
        if self.usb_capture:
            self.usb_capture.stop()
            self.usb_capture = None
        if self.processing_thread:
            self.processing_thread.stop()
            self.processing_thread = None
        
        self.is_processing = False
    
    def enable_playback_controls(self):
        """Enable playback controls"""
        self.play_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.record_btn.setEnabled(True)
        self.detect_btn.setEnabled(True)
        self.time_slider.setEnabled(True)
    
    def on_frame_ready(self, frame):
        """Handle new frame"""
        self.current_frame = frame
        self.frame_count_display += 1
        
        if self.processing_thread:
            self.processing_thread.set_frame(frame)
        
        # NDI output
        if self.ndi_output and self.ndi_out_btn.isChecked():
            self.ndi_output.send_frame(frame)
    
    def on_frame_processed(self, frame, values):
        """Handle processed frame"""
        self.display_frame(frame)
        self.update_fields_list()
        
        if self.http_server:
            self.http_server.update_data(values)
        
        if self.is_recording:
            self.csv_writer.write(values)
            self.xml_output.write(values)
    
    def display_frame(self, frame):
        """Display frame"""
        display_frame = cv2.resize(frame, (956, 540), interpolation=cv2.INTER_LINEAR)
        rgb_frame = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
        
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
        
        pixmap = QPixmap.fromImage(qt_image)
        self.video_label.setPixmap(pixmap)
        self.video_label.set_scale(956, 540)
        self.video_label.set_fields(self.field_manager.get_all_fields())
        self.video_label.update()
    
    def toggle_playback(self):
        """Start playback"""
        if not self.is_processing:
            if self.video_reader:
                self.video_reader.start()
            
            self.processing_thread = ProcessingThread(
                self.field_manager, self.field_tracker, self.ocr_engine
            )
            self.processing_thread.frame_processed.connect(self.on_frame_processed)
            self.processing_thread.start()
            
            self.is_processing = True
            self.play_btn.setEnabled(False)
            self.pause_btn.setEnabled(True)
    
    def pause_video(self):
        """Pause playback"""
        if self.video_reader:
            self.video_reader.stop()
        if self.processing_thread:
            self.processing_thread.stop()
        
        self.is_processing = False
        self.play_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
    
    def seek_video(self):
        """Seek in video"""
        if self.video_reader:
            frame_num = self.time_slider.value()
            self.video_reader.seek(frame_num)
    
    def on_video_finished(self):
        """Video ended"""
        self.is_processing = False
        self.play_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
    
    def on_source_error(self, error_msg):
        """Handle source error"""
        print(f"Source error: {error_msg}")
    
    def toggle_ndi_output(self):
        """Toggle NDI output"""
        if self.ndi_out_btn.isChecked():
            self.ndi_output = NDIOutput("SmartOCR Output")
            self.ndi_out_btn.setText("📤 NDI Out: ON")
            self.ndi_out_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        else:
            if self.ndi_output:
                self.ndi_output.stop()
                self.ndi_output = None
            self.ndi_out_btn.setText("📤 NDI Out: OFF")
            self.ndi_out_btn.setStyleSheet("")
    
    def auto_detect_fields(self):
        """Auto-detect with YOLO"""
        if not self.yolo_detector:
            try:
                # Use the trained model path
                model_path = r"C:\Users\suppo\Documents\YOLO BUILD\yolov5\runs\train\scoreboard_detection\weights\best.pt"
                self.yolo_detector = YOLOFieldDetector(model_path)
                self.yolo_status.setText("YOLO: Loaded")
            except Exception as e:
                self.yolo_status.setText(f"YOLO Error: {e}")
                return
        
        if self.current_frame is not None:
            detections = self.yolo_detector.detect(self.current_frame)
            
            if detections:
                self.field_manager.fields.clear()
                self.field_manager.field_order.clear()
                
                for det in detections:
                    self.field_manager.add_field(
                        det['name'],
                        det['display_name'],
                        det['bbox'],
                        det['field_type']
                    )
                
                self.update_fields_list()
                self.yolo_status.setText(f"Detected {len(detections)} fields")
            else:
                self.yolo_status.setText("No fields detected")
    
    def toggle_recording(self):
        """Toggle CSV/XML recording"""
        if not self.is_recording:
            fieldnames = [f.name for f in self.field_manager.get_all_fields()]
            self.csv_writer.open(fieldnames)
            self.xml_output = XMLOutput()  # Create new XML file
            self.is_recording = True
            self.record_btn.setText("⏹️ Stop")
            self.record_btn.setStyleSheet("background-color: #f44336; color: white;")
            self.output_label.setText("Recording...")
            self.csv_path_label.setText(f"CSV: {self.csv_writer.get_path()}")
            self.xml_path_label.setText(f"XML: {self.xml_output.get_path()}")
        else:
            self.csv_writer.close()
            self.is_recording = False
            self.record_btn.setText("🔴 Record")
            self.record_btn.setStyleSheet("")
            self.output_label.setText("Saved ✓")
    
    def update_fields_list(self):
        """Update fields list"""
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
        """Add field"""
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
        """Handle field moved"""
        self.field_manager.update_field_position(field_name, new_bbox)
        field = self.field_manager.get_field(field_name)
        if field and self.current_frame is not None:
            x, y, w, h = new_bbox
            frame_h, frame_w = self.current_frame.shape[:2]
            x = max(0, min(x, frame_w - w))
            y = max(0, min(y, frame_h - h))
            template = self.current_frame[y:y+h, x:x+w].copy()
            field.set_template(template)
    
    def update_fps(self):
        """Update FPS counter"""
        self.fps_label.setText(f"FPS: {self.frame_count_display}")
        self.frame_count_display = 0
    
    def closeEvent(self, event):
        """Cleanup"""
        self.stop_current_source()
        if self.ndi_output:
            self.ndi_output.stop()
        if self.http_server:
            self.http_server.stop()
        if self.is_recording:
            self.csv_writer.close()
        event.accept()
