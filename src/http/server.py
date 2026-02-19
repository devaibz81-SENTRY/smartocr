"""
HTTP Server - Localhost output for web overlays
"""
from flask import Flask, jsonify, Response
from flask_cors import CORS
from PySide6.QtCore import QThread
import xml.etree.ElementTree as ET
import json

class HTTPServerThread(QThread):
    """
    Flask HTTP server running in separate thread
    Provides JSON, XML, and HTML endpoints
    """
    
    def __init__(self, field_manager, host='0.0.0.0', port=8080):
        super().__init__()
        self.field_manager = field_manager
        self.host = host
        self.port = port
        self.current_data = {}
        self.app = Flask(__name__)
        CORS(self.app)  # Enable CORS for web overlays
        self.setup_routes()
    
    def setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/')
        def index():
            """Simple HTML dashboard"""
            html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>SmartOCR Live Data</title>
                <style>
                    body { font-family: Arial, sans-serif; background: #1a1a1a; color: white; padding: 20px; }
                    .field { background: #333; padding: 15px; margin: 10px 0; border-radius: 8px; }
                    .value { font-size: 24px; font-weight: bold; color: #4CAF50; }
                    .name { font-size: 14px; color: #aaa; }
                    h1 { color: #4CAF50; }
                    .refresh { color: #888; font-size: 12px; }
                </style>
                <meta http-equiv="refresh" content="1">
            </head>
            <body>
                <h1>🏆 SmartOCR Live Scoreboard</h1>
                <p class="refresh">Auto-refreshing every second...</p>
            """
            
            for field in self.field_manager.get_all_fields():
                value = field.get_output_value() or "..."
                status = "✓" if field.is_visible else "✗"
                color = "#4CAF50" if field.is_visible else "#f44336"
                
                html += f"""
                <div class="field">
                    <div class="name">{status} {field.display_name}</div>
                    <div class="value" style="color: {color}">{value}</div>
                </div>
                """
            
            html += """
                <hr>
                <p style="font-size: 12px; color: #666;">
                    <a href="/json" style="color: #4CAF50;">JSON API</a> | 
                    <a href="/xml" style="color: #4CAF50;">XML API</a>
                </p>
            </body>
            </html>
            """
            return html
        
        @self.app.route('/json')
        def get_json():
            """Return JSON data"""
            data = {
                'timestamp': self.current_data.get('timestamp', ''),
                'fields': {}
            }
            
            for field in self.field_manager.get_all_fields():
                data['fields'][field.name] = {
                    'value': field.get_output_value(),
                    'display_name': field.display_name,
                    'type': field.field_type.value,
                    'visible': field.is_visible,
                    'confidence': field.confidence
                }
            
            return jsonify(data)
        
        @self.app.route('/xml')
        def get_xml():
            """Return XML data for vMix"""
            root = ET.Element('scoreboard')
            
            for field in self.field_manager.get_all_fields():
                field_elem = ET.SubElement(root, 'field')
                field_elem.set('name', field.name)
                field_elem.set('display', field.display_name)
                field_elem.set('type', field.field_type.value)
                field_elem.text = field.get_output_value()
            
            xml_str = ET.tostring(root, encoding='unicode')
            return Response(xml_str, mimetype='application/xml')
        
        @self.app.route('/csv')
        def get_csv():
            """Return CSV format"""
            lines = ['field_name,display_name,value,type']
            
            for field in self.field_manager.get_all_fields():
                value = field.get_output_value() or ''
                lines.append(f"{field.name},{field.display_name},{value},{field.field_type.value}")
            
            csv_data = '\n'.join(lines)
            return Response(csv_data, mimetype='text/csv')
    
    def update_data(self, data):
        """Update current data"""
        self.current_data = data
    
    def run(self):
        """Run Flask server"""
        try:
            print(f"Starting HTTP server on http://{self.host}:{self.port}")
            self.app.run(host=self.host, port=self.port, debug=False, use_reloader=False)
        except Exception as e:
            print(f"HTTP Server error: {e}")
    
    def stop(self):
        """Stop server"""
        # Flask doesn't have clean shutdown, just terminate thread
        self.terminate()
