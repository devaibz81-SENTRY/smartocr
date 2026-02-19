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
        self.socketio = SocketIO(self.app, cors_allowed_origins="*", async_mode='threading')
        self.setup_routes()
        self.setup_websocket()
    
    def setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/')
        def index():
            """Live HTML dashboard with premium UI"""
            return render_template_string(self.get_dashboard_html())
        
        @self.app.route('/overlay')
        def overlay():
            """Transparent overlay for OBS/vMix web browser sources"""
            return render_template_string(self.get_overlay_html())
        
        @self.app.route('/json')
        def get_json():
            """Return JSON data"""
            return jsonify(self.get_json_data())
        
        @self.app.route('/xml')
        def get_xml():
            """Return XML data for vMix"""
            return Response(self.get_vmux_xml(), mimetype='application/xml')
        
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
    
    def setup_websocket(self):
        """Setup WebSocket for real-time updates"""
        @self.socketio.on('connect')
        def handle_connect():
            emit('data_update', self.get_json_data())
    
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
                'confidence': field.confidence,
                'status': 'ok' if field.is_visible else 'lost'
            }
        
        return data

    def get_vmux_xml(self) -> str:
        """Generate vMix-compatible XML format"""
        root = ET.Element('vmix')
        inputs = ET.SubElement(root, 'inputs')
        
        for field in self.field_manager.get_all_fields():
            input_elem = ET.SubElement(inputs, 'input')
            input_elem.set('name', field.display_name)
            input_elem.set('key', field.name)
            input_elem.text = field.get_output_value() or ''
        
        xml_str = ET.tostring(root, encoding='unicode')
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_str

    def get_dashboard_html(self) -> str:
        """Premium Dashboard with modern UI"""
        return '''
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>SmartOCR Premium Dashboard</title>
            <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap" rel="stylesheet">
            <style>
                :root {
                    --primary: #4CAF50;
                    --primary-glow: rgba(76, 175, 80, 0.4);
                    --danger: #ff4757;
                    --bg: #0f172a;
                    --card-bg: rgba(30, 41, 59, 0.7);
                    --text: #f8fafc;
                    --text-muted: #94a3b8;
                }

                * { margin: 0; padding: 0; box-sizing: border-box; }
                body {
                    font-family: 'Outfit', sans-serif;
                    background: var(--bg);
                    background-image: 
                        radial-gradient(at 0% 0%, rgba(76, 175, 80, 0.15) 0px, transparent 50%),
                        radial-gradient(at 100% 100%, rgba(33, 150, 243, 0.1) 0px, transparent 50%);
                    color: var(--text);
                    min-height: 100vh;
                    display: flex;
                    flex-direction: column;
                    overflow-x: hidden;
                }

                header {
                    padding: 40px 20px;
                    text-align: center;
                    animation: fadeInDown 0.8s ease-out;
                }

                h1 {
                    font-size: 3rem;
                    font-weight: 800;
                    letter-spacing: -1px;
                    background: linear-gradient(to right, #4CAF50, #81C784);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    margin-bottom: 8px;
                }

                .badge {
                    display: inline-flex;
                    align-items: center;
                    padding: 4px 12px;
                    background: rgba(76, 175, 80, 0.1);
                    border: 1px solid var(--primary);
                    border-radius: 20px;
                    color: var(--primary);
                    font-size: 0.85rem;
                    font-weight: 600;
                    margin-bottom: 20px;
                }

                .badge::before {
                    content: '';
                    width: 8px;
                    height: 8px;
                    background: var(--primary);
                    border-radius: 50%;
                    margin-right: 8px;
                    box-shadow: 0 0 10px var(--primary);
                    animation: pulse 2s infinite;
                }

                .container {
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 0 20px 60px;
                    width: 100%;
                }

                .grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                    gap: 24px;
                }

                .card {
                    background: var(--card-bg);
                    backdrop-filter: blur(12px);
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    border-radius: 24px;
                    padding: 32px;
                    transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
                    position: relative;
                    overflow: hidden;
                }

                .card:hover {
                    transform: translateY(-8px);
                    border-color: var(--primary);
                    box-shadow: 0 20px 40px rgba(0,0,0,0.4), 0 0 20px var(--primary-glow);
                }

                .card.lost {
                    border-color: var(--danger);
                    opacity: 0.8;
                }

                .card.lost::before {
                    content: 'SIGNAL LOST';
                    position: absolute;
                    top: 12px;
                    right: 12px;
                    font-size: 0.7rem;
                    font-weight: 800;
                    color: var(--danger);
                }

                .label {
                    font-size: 0.9rem;
                    font-weight: 600;
                    color: var(--text-muted);
                    text-transform: uppercase;
                    letter-spacing: 2px;
                    margin-bottom: 12px;
                }

                .value {
                    font-size: 4rem;
                    font-weight: 800;
                    color: var(--text);
                    text-shadow: 0 0 30px rgba(255,255,255,0.1);
                }

                .card.lost .value {
                    color: var(--danger);
                }

                .footer {
                    margin-top: auto;
                    padding: 40px 20px;
                    background: rgba(0,0,0,0.2);
                    text-align: center;
                }

                .links {
                    display: flex;
                    justify-content: center;
                    gap: 16px;
                    margin-bottom: 20px;
                    flex-wrap: wrap;
                }

                .links a {
                    color: var(--text);
                    text-decoration: none;
                    padding: 10px 24px;
                    background: rgba(255,255,255,0.05);
                    border: 1px solid rgba(255,255,255,0.1);
                    border-radius: 12px;
                    font-weight: 600;
                    transition: all 0.3s;
                }

                .links a:hover {
                    background: var(--primary);
                    border-color: var(--primary);
                    transform: scale(1.05);
                }

                .timestamp {
                    font-size: 0.9rem;
                    color: var(--text-muted);
                }

                @keyframes pulse {
                    0% { opacity: 1; transform: scale(1); }
                    50% { opacity: 0.5; transform: scale(1.2); }
                    100% { opacity: 1; transform: scale(1); }
                }

                @keyframes fadeInDown {
                    from { opacity: 0; transform: translateY(-20px); }
                    to { opacity: 1; transform: translateY(0); }
                }

                @media (max-width: 768px) {
                    h1 { font-size: 2rem; }
                    .value { font-size: 3rem; }
                }
            </style>
            <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
        </head>
        <body>
            <header>
                <div class="badge">LIVE DATA FEED</div>
                <h1>SmartOCR Dashboard</h1>
            </header>

            <div class="container">
                <div class="grid" id="data-grid">
                    <!-- Data will be injected here -->
                </div>
            </div>

            <div class="footer">
                <div class="links">
                    <a href="/json" target="_blank">JSON API</a>
                    <a href="/xml" target="_blank">XML (vMix)</a>
                    <a href="/csv" target="_blank">CSV Output</a>
                    <a href="/overlay" target="_blank">Web Overlay</a>
                </div>
                <div class="timestamp" id="last-update">Connecting to OCR Engine...</div>
            </div>

            <script>
                const socket = io();
                const grid = document.getElementById('data-grid');
                const updateEl = document.getElementById('last-update');

                socket.on('data_update', (data) => {
                    renderData(data);
                    updateEl.textContent = 'Last sync: ' + new Date().toLocaleTimeString();
                });

                // Fallback polling
                setInterval(() => {
                    if (!socket.connected) {
                        fetch('/json')
                            .then(r => r.json())
                            .then(renderData)
                            .catch(console.error);
                    }
                }, 1000);

                function renderData(data) {
                    let html = '';
                    for (const [key, field] of Object.entries(data.fields)) {
                        const isLost = field.status === 'lost';
                        html += `
                            <div class="card ${isLost ? 'lost' : ''}">
                                <div class="label">${field.display_name}</div>
                                <div class="value">${field.value || '---'}</div>
                            </div>
                        `;
                    }
                    grid.innerHTML = html;
                }
            </script>
        </body>
        </html>
        '''

    def get_overlay_html(self) -> str:
        """Minimal transparent overlay for streaming software"""
        return '''
        <!DOCTYPE html>
        <html>
        <head>
            <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@800&display=swap" rel="stylesheet">
            <style>
                body { 
                    margin: 0; padding: 20px; overflow: hidden; 
                    background: transparent; color: white;
                    font-family: 'Outfit', sans-serif;
                }
                .overlay-container {
                    display: flex; gap: 30px; align-items: center;
                }
                .field {
                    background: rgba(0,0,0,0.8);
                    padding: 10px 20px;
                    border-radius: 8px;
                    border: 2px solid #4CAF50;
                    min-width: 100px;
                    text-align: center;
                }
                .field.lost { border-color: #ff4757; opacity: 0.5; }
                .label { font-size: 12px; color: #aaa; text-transform: uppercase; }
                .value { font-size: 32px; font-weight: 800; }
            </style>
            <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
        </head>
        <body>
            <div id="overlay" class="overlay-container"></div>
            <script>
                const socket = io();
                socket.on('data_update', (data) => {
                    let html = '';
                    for (const [key, field] of Object.entries(data.fields)) {
                        html += `
                            <div class="field ${field.status === 'lost' ? 'lost' : ''}">
                                <div class="label">${field.display_name}</div>
                                <div class="value">${field.value || '--'}</div>
                            </div>
                        `;
                    }
                    document.getElementById('overlay').innerHTML = html;
                });
            </script>
        </body>
        </html>
        '''

    def update_data(self, data):
        """Update data and broadcast"""
        self.current_data = data
        try:
            self.socketio.emit('data_update', self.get_json_data())
        except:
            pass

    def run(self):
        """Run the server"""
        try:
            print(f"🚀 Starting SmartOCR Premium Server on http://{self.host}:{self.port}")
            self.socketio.run(self.app, host=self.host, port=self.port, debug=False, use_reloader=False)
        except Exception as e:
            print(f"Server Error: {e}")

    def stop(self):
        self.terminate()
