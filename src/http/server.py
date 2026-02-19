"""
HTTP Server - Enhanced localhost output with WebSocket support
"""
from flask import Flask, jsonify, Response, render_template_string
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from PySide6.QtCore import QThread
import xml.etree.ElementTree as ET
import json
from datetime import datetime

class HTTPServerThread(QThread):
    """
    Flask HTTP server with WebSocket support for real-time updates
    Provides JSON, XML, HTML, and live WebSocket endpoints
    """
    
    def __init__(self, field_manager, host='0.0.0.0', port=8080):
        super().__init__()
        self.field_manager = field_manager
        self.host = host
        self.port = port
        self.current_data = {}
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'smartocr-secret-key'
        CORS(self.app)
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")
        self.setup_routes()
        self.setup_websocket()
    
    def setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/')
        def index():
            """Live HTML dashboard with auto-updates"""
            return render_template_string(self.get_dashboard_html())
        
        @self.app.route('/json')
        def get_json():
            """Return JSON data"""
            data = {
                'timestamp': datetime.now().isoformat(),
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
            return Response(self.get_vmux_xml(), mimetype='application/xml')
        
        @self.app.route('/xml/simple')
        def get_simple_xml():
            """Return simple XML"""
            return Response(self.get_simple_xml_format(), mimetype='application/xml')
        
        @self.app.route('/csv')
        def get_csv():
            """Return CSV format"""
            lines = ['field_name,display_name,value,type,timestamp']
            timestamp = datetime.now().isoformat()
            
            for field in self.field_manager.get_all_fields():
                value = field.get_output_value() or ''
                lines.append(f"{field.name},{field.display_name},{value},{field.field_type.value},{timestamp}")
            
            csv_data = '\n'.join(lines)
            return Response(csv_data, mimetype='text/csv')
        
        @self.app.route('/text/<field_name>')
        def get_field_text(field_name):
            """Return single field value as plain text"""
            field = self.field_manager.get_field(field_name)
            if field:
                return field.get_output_value() or ''
            return 'Field not found', 404
        
        @self.app.route('/api/all')
        def get_all_formats():
            """Return all formats at once"""
            return jsonify({
                'json': self.get_json_data(),
                'xml_url': f'http://localhost:{self.port}/xml',
                'csv_url': f'http://localhost:{self.port}/csv',
                'timestamp': datetime.now().isoformat()
            })
    
    def setup_websocket(self):
        """Setup WebSocket for real-time updates"""
        
        @self.socketio.on('connect')
        def handle_connect():
            print('Client connected to WebSocket')
            emit('connected', {'data': 'Connected to SmartOCR'})
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            print('Client disconnected from WebSocket')
        
        @self.socketio.on('request_data')
        def handle_request_data():
            """Send current data to client"""
            data = self.get_json_data()
            emit('data_update', data)
    
    def get_json_data(self):
        """Get current data as dict"""
        data = {
            'timestamp': datetime.now().isoformat(),
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
        
        return data
    
    def get_vmux_xml(self) -> str:
        """Generate vMix-compatible XML format"""
        root = ET.Element('vmix')
        
        # Add inputs element
        inputs = ET.SubElement(root, 'inputs')
        
        # Add each field as input
        for field in self.field_manager.get_all_fields():
            input_elem = ET.SubElement(inputs, 'input')
            input_elem.set('name', field.display_name)
            input_elem.set('key', field.name)
            input_elem.text = field.get_output_value() or ''
        
        # Add overlay data
        overlay = ET.SubElement(root, 'overlay')
        for field in self.field_manager.get_all_fields():
            # Convert to camelCase
            elem_name = ''.join(word.capitalize() for word in field.name.split('_'))
            elem = ET.SubElement(overlay, elem_name)
            elem.text = field.get_output_value() or ''
        
        xml_str = ET.tostring(root, encoding='unicode')
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_str
    
    def get_simple_xml_format(self) -> str:
        """Generate simple XML format"""
        root = ET.Element('SmartOCR')
        root.set('timestamp', datetime.now().isoformat())
        
        for field in self.field_manager.get_all_fields():
            elem = ET.SubElement(root, field.name)
            elem.text = field.get_output_value() or ''
        
        xml_str = ET.tostring(root, encoding='unicode')
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_str
    
    def get_dashboard_html(self) -> str:
        """Get dashboard HTML with WebSocket support"""
        return '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>SmartOCR Live Scoreboard</title>
            <style>
                * { margin: 0; padding: 0; box-sizing: border-box; }
                body { 
                    font-family: 'Segoe UI', Arial, sans-serif; 
                    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                    color: white; 
                    padding: 20px;
                    min-height: 100vh;
                }
                h1 { 
                    color: #4CAF50; 
                    margin-bottom: 10px;
                    text-align: center;
                }
                .subtitle {
                    text-align: center;
                    color: #888;
                    margin-bottom: 30px;
                }
                .grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                    gap: 20px;
                    max-width: 1200px;
                    margin: 0 auto;
                }
                .field { 
                    background: rgba(255,255,255,0.1);
                    padding: 20px; 
                    border-radius: 12px;
                    border: 1px solid rgba(255,255,255,0.2);
                    transition: all 0.3s ease;
                }
                .field:hover {
                    transform: translateY(-2px);
                    box-shadow: 0 4px 20px rgba(76, 175, 80, 0.3);
                }
                .field.lost {
                    border-color: #f44336;
                    opacity: 0.7;
                }
                .value { 
                    font-size: 36px; 
                    font-weight: bold; 
                    color: #4CAF50;
                    margin: 10px 0;
                }
                .value.lost {
                    color: #f44336;
                }
                .name { 
                    font-size: 14px; 
                    color: #aaa;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                }
                .status {
                    display: inline-block;
                    width: 8px;
                    height: 8px;
                    border-radius: 50%;
                    margin-right: 8px;
                }
                .status.ok { background: #4CAF50; }
                .status.lost { background: #f44336; }
                .api-links {
                    text-align: center;
                    margin-top: 40px;
                    padding: 20px;
                    background: rgba(255,255,255,0.05);
                    border-radius: 8px;
                }
                .api-links a {
                    color: #4CAF50;
                    text-decoration: none;
                    margin: 0 15px;
                    padding: 8px 16px;
                    border: 1px solid #4CAF50;
                    border-radius: 4px;
                    transition: all 0.3s;
                }
                .api-links a:hover {
                    background: #4CAF50;
                    color: white;
                }
                .update-time {
                    text-align: center;
                    color: #666;
                    font-size: 12px;
                    margin-top: 20px;
                }
            </style>
            <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
        </head>
        <body>
            <h1>🏆 SmartOCR Live Scoreboard</h1>
            <p class="subtitle">Real-time OCR from Live Video Stream</p>
            
            <div class="grid" id="fields-container">
                Loading...
            </div>
            
            <div class="api-links">
                <a href="/json" target="_blank">JSON API</a>
                <a href="/xml" target="_blank">XML (vMix)</a>
                <a href="/csv" target="_blank">CSV</a>
                <a href="/xml/simple" target="_blank">Simple XML</a>
            </div>
            
            <p class="update-time" id="update-time">Waiting for data...</p>
            
            <script>
                const socket = io();
                
                socket.on('connect', function() {
                    console.log('Connected to SmartOCR');
                    socket.emit('request_data');
                });
                
                socket.on('data_update', function(data) {
                    updateDisplay(data);
                });
                
                // Fallback: Poll every second if WebSocket fails
                setInterval(function() {
                    fetch('/json')
                        .then(response => response.json())
                        .then(data => updateDisplay(data))
                        .catch(err => console.log('Poll error:', err));
                }, 1000);
                
                function updateDisplay(data) {
                    const container = document.getElementById('fields-container');
                    const timeEl = document.getElementById('update-time');
                    
                    let html = '';
                    for (const [key, field] of Object.entries(data.fields)) {
                        const isLost = !field.visible;
                        const statusClass = isLost ? 'lost' : 'ok';
                        const valueClass = isLost ? 'value lost' : 'value';
                        const fieldClass = isLost ? 'field lost' : 'field';
                        
                        html += `
                            <div class="${fieldClass}">
                                <div class="name">
                                    <span class="status ${statusClass}"></span>
                                    ${field.display_name}
                                </div>
                                <div class="${valueClass}">${field.value || '...'}</div>
                            </div>
                        `;
                    }
                    
                    container.innerHTML = html;
                    timeEl.textContent = 'Last update: ' + new Date().toLocaleTimeString();
                }
            </script>
        </body>
        </html>
        '''
    
    def update_data(self, data):
        """Update current data and broadcast via WebSocket"""
        self.current_data = data
        try:
            self.socketio.emit('data_update', self.get_json_data())
        except:
            pass  # WebSocket might not be connected
    
    def run(self):
        """Run Flask-SocketIO server"""
        try:
            print(f"🌐 HTTP Server starting on http://{self.host}:{self.port}")
            print(f"   Dashboard: http://localhost:{self.port}")
            print(f"   JSON API:  http://localhost:{self.port}/json")
            print(f"   XML API:   http://localhost:{self.port}/xml")
            self.socketio.run(self.app, host=self.host, port=self.port, debug=False, use_reloader=False)
        except Exception as e:
            print(f"HTTP Server error: {e}")
    
    def stop(self):
        """Stop server"""
        self.terminate()
