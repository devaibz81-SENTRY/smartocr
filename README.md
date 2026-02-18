# SmartOCR - Real-time Scoreboard OCR

SmartOCR reads scoreboard text from video files with intelligent field tracking. When fields are lost due to camera movement or occlusion, it holds the last good values until the fields are re-acquired.

## Features

- **Video File Input**: Load any MP4, AVI, MKV, or MOV file
- **5 Field Types**: Home Score, Away Score, Game Clock, Period, Shot Clock
- **Smart Tracking**: 
  - Optical flow tracks field movement when camera moves
  - Template matching re-acquires lost fields
  - Holds last good values indefinitely until field is found
- **Validation**: Prevents wild jumps (25 point threshold, 50 after feed loss)
- **CSV Output**: Real-time export for vMix data sources

## Installation

### 1. Install Python Dependencies
```bash
cd "C:\Users\suppo\Documents\YOLO BUILD\SmartOCR"
pip install -r requirements.txt
```

### 2. Install Tesseract OCR
Download and install Tesseract for Windows:
https://github.com/UB-Mannheim/tesseract/wiki

Add Tesseract to your system PATH or update the path in `src/ocr/ocr_engine.py`:
```python
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
```

## Usage

### 1. Run the Application
```bash
python main.py
```

### 2. Load Video
Click "Load Video" and select your scoreboard video file.

### 3. Configure Fields
Default fields are created automatically. To modify:
- Fields appear as colored boxes on the video
- Green = field visible and tracking
- Red = field lost, holding last value

### 4. Start Processing
- Click "Start" to begin OCR
- Video plays with real-time text recognition
- Field values update in the right panel

### 5. Record CSV
- Click "Start Recording" to save to CSV
- CSV format: `timestamp,home_score,away_score,game_clock,period,shot_clock`
- File saves as `scores_YYYYMMDD_HHMMSS.csv`

### 6. vMix Integration
In vMix:
1. Add Data Source → CSV
2. Select the generated CSV file
3. Map fields to title elements
4. Enable "Auto Reload" for real-time updates

## Field Behavior

### When Camera Moves
- Optical flow detects movement
- Field boxes follow the movement
- OCR continues on tracked positions

### When Field is Lost
- Box turns red
- Last good value is held
- Template matching searches for field
- When re-acquired: box turns green, OCR resumes

### Validation
- Score changes > 25 points are rejected (unless field was missing > 1 sec)
- Prevents OCR errors from causing graphic jumps

## Configuration

### Default Field Layout
Fields are positioned relative to video center:
- Home Score: Left side
- Away Score: Right side  
- Game Clock: Center top
- Period: Center below clock
- Shot Clock: Left of clock

### Customizing Fields
(Currently requires code modification)
Edit `field_manager.create_default_fields()` in `src/fields/field_manager.py`

## File Structure
```
SmartOCR/
├── main.py                 # Entry point
├── requirements.txt        # Python dependencies
├── src/
│   ├── core/
│   │   ├── app.py         # Main GUI
│   │   └── video_reader.py # Video capture
│   ├── fields/
│   │   ├── field_region.py # Field data model
│   │   ├── field_manager.py
│   │   └── field_tracker.py # Camera movement tracking
│   ├── ocr/
│   │   └── ocr_engine.py  # Tesseract wrapper
│   └── output/
│       └── csv_writer.py  # CSV export
```

## Troubleshooting

### "Tesseract not found"
Install Tesseract and add to PATH, or update path in ocr_engine.py

### Poor OCR accuracy
- Ensure scoreboard text is clear in video
- Adjust field boxes to tightly fit text
- Increase video resolution if possible

### Fields not tracking
- Enable "Auto-Track Fields" checkbox
- Ensure video has consistent lighting
- Check that template matching has good reference image

## Credits
Built with PySide6, OpenCV, and Tesseract OCR

## License
MIT
