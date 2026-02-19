"""Input module for video sources"""
from .ndi_capture import NDICapture
from .stream_capture import StreamCapture

__all__ = ['NDICapture', 'StreamCapture']
