# 🏆 YOLOv5 Scoreboard Training

## Dataset Info
- **Images**: 31 labeled scoreboard images
- **Classes**: 9 scoreboard elements
  - Away-Fouls
  - Away-Team Name
  - Away-Team Score
  - Game-Clock
  - Home-Fouls
  - Home-Team Name
  - Home-Team Score
  - Period
  - Shot-Clock

## Quick Start

### Option 1: Run Training Script (Recommended)
```cmd
cd "C:\Users\suppo\Documents\YOLO BUILD"
python train_yolov5.py
```

This will:
1. Download YOLOv5 (if not present)
2. Install dependencies
3. Train for 100 epochs
4. Export to ONNX format
5. Save model to: `yolov5/runs/train/scoreboard_detection/weights/best.pt`

### Option 2: Manual Training
```cmd
cd "C:\Users\suppo\Documents\YOLO BUILD"

# Clone YOLOv5
git clone https://github.com/ultralytics/yolov5.git

# Install requirements
cd yolov5
pip install -r requirements.txt

# Train
python train.py --img 640 --batch 16 --epochs 100 --data ../data/data.yaml --weights yolov5s.pt --cache
```

## Training Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| `--img` | 640 | Input image size |
| `--batch` | 16 | Batch size |
| `--epochs` | 100 | Training iterations |
| `--weights` | yolov5s.pt | Pretrained model (small) |
| `--data` | data.yaml | Dataset config |

## After Training

### Use Model in SmartOCR
1. Copy trained model:
   ```
   yolov5/runs/train/scoreboard_detection/weights/best.pt
   ```

2. Paste to:
   ```
   C:\Users\suppo\Documents\YOLO BUILD\YOLOv8-Object-Detection-on-Video-with-OpenCV-main
   ```

3. In SmartOCR, click "🔍 Auto-Detect Fields"

### Export to Other Formats
```cmd
# ONNX (for faster inference)
python export.py --weights runs/train/scoreboard_detection/weights/best.pt --include onnx

# TorchScript
python export.py --weights runs/train/scoreboard_detection/weights/best.pt --include torchscript

# TensorRT (for NVIDIA GPUs)
python export.py --weights runs/train/scoreboard_detection/weights/best.pt --include engine
```

## Tips for Better Results

1. **More Data**: 31 images is minimal. Collect 50-100+ for better accuracy
2. **Augmentation**: YOLOv5 automatically augments (flips, scales, etc.)
3. **Validation**: With small datasets, use k-fold cross-validation
4. **Class Balance**: Ensure all 9 classes are represented
5. **Image Quality**: Use high-resolution scoreboard images

## Troubleshooting

### CUDA Out of Memory
Reduce batch size:
```cmd
python train.py --batch 8 ...
```

### Slow Training
Use smaller model:
```cmd
--weights yolov5n.pt  # nano (fastest)
```

### Need More Accuracy
Use larger model:
```cmd
--weights yolov5m.pt  # medium
--weights yolov5l.pt  # large
--weights yolov5x.pt  # extra large
```

## Results Location
After training, find results at:
```
yolov5/runs/train/scoreboard_detection/
├── weights/
│   ├── best.pt      # Best model
│   └── last.pt      # Last checkpoint
├── results.png      # Training graphs
├── confusion_matrix.png
├── F1_curve.png
├── PR_curve.png
└── labels.jpg       # Dataset visualization
```

## Next Steps

1. ✅ Train model
2. ✅ Test detection on new images
3. ✅ Integrate with SmartOCR
4. ⬜ Collect more training data
5. ⬜ Fine-tune hyperparameters

## Resources

- [YOLOv5 Docs](https://docs.ultralytics.com/yolov5/)
- [Training Tips](https://docs.ultralytics.com/yolov5/tutorials/train_custom_data/)
- [Your Colab Guide](https://colab.research.google.com/github/EdjeElectronics/Train-and-Deploy-YOLO-Models/blob/main/Train_YOLO_Models.ipynb)
