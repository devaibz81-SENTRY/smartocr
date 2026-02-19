"""
XML Output - File-based XML output for vMix and other systems
"""
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Dict

class XMLOutput:
    """
    Write OCR results to XML file for vMix data sources
    """
    
    def __init__(self, output_path: str = None):
        self.output_path = output_path or self._get_default_path()
        self.last_data = {}
    
    def _get_default_path(self) -> str:
        """Get default output path"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"scores_{timestamp}.xml"
    
    def write(self, values: Dict[str, str]):
        """Write current values to XML file"""
        self.last_data = values
        
        # Create XML structure
        root = ET.Element('SmartOCR')
        root.set('timestamp', datetime.now().isoformat())
        
        # Add data element
        data = ET.SubElement(root, 'Data')
        
        for field_name, value in values.items():
            # Create camelCase element name for vMix compatibility
            elem_name = self._to_camel_case(field_name)
            elem = ET.SubElement(data, elem_name)
            elem.text = str(value) if value else ''
        
        # Format XML
        xml_str = ET.tostring(root, encoding='unicode')
        xml_str = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_str
        
        # Write to file
        with open(self.output_path, 'w', encoding='utf-8') as f:
            f.write(xml_str)
    
    def _to_camel_case(self, text: str) -> str:
        """Convert field_name to CamelCase for vMix"""
        words = text.replace('_', ' ').replace('-', ' ').split()
        return ''.join(word.capitalize() for word in words)
    
    def get_path(self) -> str:
        """Get output file path"""
        return self.output_path
    
    def get_vmux_format(self) -> str:
        """Get vMix-compatible XML format"""
        root = ET.Element('vmix_data')
        
        for field_name, value in self.last_data.items():
            # vMix typically uses simple element names
            elem = ET.SubElement(root, field_name)
            elem.text = str(value) if value else ''
        
        return ET.tostring(root, encoding='unicode')
