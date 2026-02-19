"""Input module for video sources"""
from .ndi_capture import NDICapture
from .stream_capture import StreamCapture
from .usb_camera import USBCameraCapture

__all__ = ['NDICapture', 'StreamCapture', 'USBCameraCapture']
