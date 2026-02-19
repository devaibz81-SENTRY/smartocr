"""
YOLOv5 Training Script for Scoreboard Detection
Based on: https://colab.research.google.com/github/EdjeElectronics/Train-and-Deploy-YOLO-Models/blob/main/Train_YOLO_Models.ipynb
"""
import os
import sys
import subprocess
from pathlib import Path

def setup_yolov5():
    """Clone and setup YOLOv5"""
    yolov5_path = Path("C:/Users/suppo/Documents/YOLO BUILD/yolov5")
    
    if not yolov5_path.exists():
        print("📥 Cloning YOLOv5 repository...")
        subprocess.run([
            "git", "clone", "https://github.com/ultralytics/yolov5.git",
            str(yolov5_path)
        ], check=True)
        
        # Install requirements
        print("📦 Installing YOLOv5 requirements...")
        subprocess.run([
            sys.executable, "-m", "pip", "install", "-r",
            str(yolov5_path / "requirements.txt")
        ], check=True)
    else:
        print("✅ YOLOv5 already exists")
    
    return yolov5_path

def train_model(yolov5_path, data_yaml, epochs=100, batch_size=16, img_size=640):
    """Train YOLOv5 model"""
    print(f"🚀 Starting training...")
    print(f"   Epochs: {epochs}")
    print(f"   Batch size: {batch_size}")
    print(f"   Image size: {img_size}")
    
    # Change to yolov5 directory
    os.chdir(yolov5_path)
    
    # Run training
    cmd = [
        sys.executable, "train.py",
        "--img", str(img_size),
        "--batch", str(batch_size),
        "--epochs", str(epochs),
        "--data", data_yaml,
        "--weights", "yolov5s.pt",  # Start with small model
        "--cache",
        "--name", "scoreboard_detection",
        "--exist-ok"
    ]
    
    print(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)
    
    # Get results path
    results_path = yolov5_path / "runs" / "train" / "scoreboard_detection" / "weights" / "best.pt"
    return results_path

def export_model(model_path, format='onnx'):
    """Export trained model to other formats"""
    yolov5_path = Path("C:/Users/suppo/Documents/YOLO BUILD/yolov5")
    os.chdir(yolov5_path)
    
    cmd = [
        sys.executable, "export.py",
        "--weights", str(model_path),
        "--include", format
    ]
    
    print(f"📤 Exporting model to {format}...")
    subprocess.run(cmd, check=True)

def main():
    """Main training pipeline"""
    print("=" * 60)
    print("🏆 YOLOv5 Scoreboard Training Pipeline")
    print("=" * 60)
    
    # Setup paths
    data_yaml = "C:/Users/suppo/Documents/YOLO BUILD/data/data.yaml"
    
    # Step 1: Setup YOLOv5
    print("\n1️⃣ Setting up YOLOv5...")
    yolov5_path = setup_yolov5()
    
    # Step 2: Train model
    print("\n2️⃣ Training model...")
    try:
        model_path = train_model(yolov5_path, data_yaml, epochs=100)
        print(f"\n✅ Training complete!")
        print(f"   Model saved to: {model_path}")
        
        # Step 3: Export model
        print("\n3️⃣ Exporting model...")
        export_model(model_path, 'onnx')
        
        print("\n" + "=" * 60)
        print("🎉 Training pipeline complete!")
        print("=" * 60)
        print(f"\nModel location: {model_path}")
        print("\nTo use in SmartOCR:")
        print(f"1. Copy {model_path}")
        print("2. Paste to: C:\\Users\\suppo\\Documents\\YOLO BUILD\\YOLOv8-Object-Detection-on-Video-with-OpenCV-main")
        print("3. Update SmartOCR to use this model")
        
    except Exception as e:
        print(f"\n❌ Training failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
