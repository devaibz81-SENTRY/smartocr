"""
CSV Writer - Outputs field values for vMix data sources
"""
import csv
import os
from datetime import datetime
from typing import Dict, List
from pathlib import Path

class CSVWriter:
    """
    Writes OCR results to CSV file for vMix integration
    Format: timestamp,field1,field2,field3,...
    """
    
    def __init__(self, output_path: str = None):
        self.output_path = output_path or self._get_default_path()
        self.file_handle = None
        self.csv_writer = None
        self.fieldnames = []
        self.is_open = False
    
    def _get_default_path(self) -> str:
        """Get default output path"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"scores_{timestamp}.csv"
    
    def open(self, fieldnames: List[str]):
        """Open CSV file for writing"""
        self.fieldnames = ['timestamp'] + fieldnames
        
        # Create directory if needed
        os.makedirs(os.path.dirname(self.output_path) or '.', exist_ok=True)
        
        self.file_handle = open(self.output_path, 'w', newline='')
        self.csv_writer = csv.DictWriter(
            self.file_handle, 
            fieldnames=self.fieldnames
        )
        self.csv_writer.writeheader()
        self.is_open = True
    
    def write(self, values: Dict[str, str]):
        """Write a row of values"""
        if not self.is_open or self.csv_writer is None:
            return
        
        row = {'timestamp': datetime.now().strftime('%H:%M:%S')}
        row.update(values)
        
        self.csv_writer.writerow(row)
        self.file_handle.flush()  # Ensure data is written immediately
    
    def close(self):
        """Close CSV file"""
        if self.file_handle:
            self.file_handle.close()
            self.is_open = False
    
    def get_path(self) -> str:
        """Get output file path"""
        return self.output_path
