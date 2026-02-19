"""
System Test - Verify all SmartOCR components
"""
import sys
import os

print("=" * 60)
print("SmartOCR System Test")
print("=" * 60)

# Test 1: YOLO Model
print("\n[1/6] Testing YOLO Model...")
try:
    from src.yolo.field_detector import YOLOFieldDetector
    detector = YOLOFieldDetector()
    if detector.is_available():
        print("   ✅ YOLO Model: LOADED (9 classes)")
    else:
        print("   ❌ YOLO Model: Not available")
except Exception as e:
    print(f"   ❌ YOLO Error: {e}")

# Test 2: Tesseract OCR
print("\n[2/6] Testing Tesseract OCR...")
try:
    import pytesseract
    version = pytesseract.get_tesseract_version()
    print(f"   ✅ Tesseract: v{version}")
except Exception as e:
    print(f"   ❌ Tesseract Error: {e}")

# Test 3: USB Cameras
print("\n[3/6] Testing USB Camera Detection...")
try:
    from src.input.usb_camera import USBCameraCapture
    cameras = USBCameraCapture.list_cameras()
    if cameras:
        print(f"   ✅ Found {len(cameras)} camera(s):")
        for cam in cameras:
            print(f"      - {cam['name']}")
    else:
        print("   ⚠️  No USB cameras found")
except Exception as e:
    print(f"   ❌ Camera Error: {e}")

# Test 4: NDI Support
print("\n[4/6] Testing NDI Support...")
try:
    import cyndilib
    print("   ✅ cyndilib: INSTALLED")
    from src.input.ndi_capture import NDICapture
    sources = NDICapture.get_sources()
    if sources:
        print(f"   ✅ Found {len(sources)} NDI source(s):")
        for src in sources:
            print(f"      - {src}")
    else:
        print("   ⚠️  No NDI sources found (check network)")
except ImportError:
    print("   ❌ cyndilib: NOT INSTALLED")
    print("      Run: pip install cyndilib")
except Exception as e:
    print(f"   ❌ NDI Error: {e}")

# Test 5: HTTP Server
print("\n[5/6] Testing HTTP Server...")
try:
    from src.http.server import HTTPServerThread
    print("   ✅ HTTP Server: Available")
except Exception as e:
    print(f"   ❌ HTTP Error: {e}")

# Test 6: File Outputs
print("\n[6/6] Testing Output Modules...")
try:
    from src.output.csv_writer import CSVWriter
    from src.output.xml_output import XMLOutput
    from src.output.ndi_output import NDIOutput
    print("   ✅ CSV Output: Available")
    print("   ✅ XML Output: Available")
    print("   ✅ NDI Output: Available")
except Exception as e:
    print(f"   ❌ Output Error: {e}")

print("\n" + "=" * 60)
print("Test Complete!")
print("=" * 60)
print("\n🚀 Ready to run: python main.py")
