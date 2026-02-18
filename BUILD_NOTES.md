# SmartOCR Build Notes

## Project Overview
Real-time OCR scoreboard reader with intelligent field tracking and state management.

## Field Types
- Home Score (number)
- Away Score (number)  
- Game Clock (time MM:SS)
- Period/Quarter (text)
- Shot Clock (number)

## Key Features
✅ Hold values until field is re-acquired (no timeout)
✅ Large jump threshold for feed recovery (25 points default, doubles to 50 after 1 sec missing)
✅ Optical flow tracking for camera movement
✅ Template matching to re-acquire lost fields
✅ CSV output for vMix

## Build Progress

### Phase 1: Foundation ✅ COMPLETE
- ✅ requirements.txt
- ✅ main.py
- ✅ Folder structure created

### Phase 2: Field System ✅ COMPLETE
- ✅ fields/field_region.py - Field data structure with validation
- ✅ fields/field_manager.py - Manage multiple fields
- ✅ fields/field_tracker.py - Optical flow + template matching

### Phase 3: Core Components ✅ COMPLETE
- ✅ core/video_reader.py - Threaded video capture
- ✅ core/app.py - Main application controller with GUI
- ✅ ocr/ocr_engine.py - Tesseract OCR with preprocessing
- ✅ output/csv_writer.py - CSV output for vMix

### Phase 4: Integration ✅ COMPLETE
- ✅ All __init__.py files created
- ✅ Module imports working
- ✅ GUI connected to processing pipeline

### Phase 5: Testing & Polish [IN PROGRESS]
- [ ] Test with sample video
- [ ] Verify CSV output format
- [ ] Test field tracking
- [ ] Error handling improvements

## Files Created
```
SmartOCR/
├── main.py
├── requirements.txt
├── BUILD_NOTES.md
├── README.md
├── src/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── app.py              # Main GUI application
│   │   └── video_reader.py     # Threaded video capture
│   ├── fields/
│   │   ├── __init__.py
│   │   ├── field_region.py     # Field data model
│   │   ├── field_manager.py    # Field collection manager
│   │   └── field_tracker.py    # Optical flow tracking
│   ├── ocr/
│   │   ├── __init__.py
│   │   └── ocr_engine.py       # Tesseract OCR wrapper
│   ├── output/
│   │   ├── __init__.py
│   │   └── csv_writer.py       # CSV output handler
│   └── gui/
│       └── __init__.py
```

## Next Steps
1. Install dependencies: `pip install -r requirements.txt`
2. Install Tesseract OCR (Windows: https://github.com/UB-Mannheim/tesseract/wiki)
3. Test with sample video
4. Create interactive region editor (Phase 6)

## Last Change
Created complete application structure with GUI, OCR, tracking, and CSV output. Ready for testing!
