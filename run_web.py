#!/usr/bin/env python3
"""
Minimal web server for HackGPT
"""

import sys
sys.path.insert(0, '.')

from flask import Flask

app = Flask(__name__)

@app.route('/')
def index():
    return """
    <html>
    <head>
        <title>HackGPT Web Dashboard</title>
        <style>
            body { 
                background: #000; 
                color: #0f0; 
                font-family: monospace; 
                margin: 0;
                padding: 20px;
            }
            .container { 
                max-width: 800px; 
                margin: 0 auto; 
            }
            .panel { 
                border: 1px solid #0f0; 
                padding: 20px; 
                margin: 20px 0; 
            }
            button { 
                background: #333; 
                color: #0f0; 
                border: 1px solid #0f0; 
                padding: 10px 20px; 
                cursor: pointer; 
            }
            input { 
                background: #333; 
                color: #0f0; 
                border: 1px solid #0f0; 
                padding: 10px; 
                margin: 5px 0; 
                width: 100%;
            }
            h1 { 
                color: #0f0; 
                text-align: center; 
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>HackGPT - AI-Powered Penetration Testing</h1>
            
            <div class="panel">
                <h2>Start Pentest</h2>
                <input type="text" id="target" placeholder="Target IP/Domain">
                <input type="text" id="scope" placeholder="Scope">
                <input type="password" id="auth" placeholder="Authorization Key">
                <button onclick="startPentest()">Start Full Pentest</button>
            </div>
            
            <div class="panel">
                <h2>Status</h2>
                <div id="status">Ready</div>
            </div>
            
            <div class="panel">
                <h2>Quick Actions</h2>
                <button onclick="runScan()">Run Network Scan</button>
                <button onclick="generateReport()">Generate Report</button>
                <button onclick="viewResults()">View Results</button>
            </div>
        </div>
        
        <script>
            function startPentest() {
                const target = document.getElementById('target').value;
                const scope = document.getElementById('scope').value;
                const auth = document.getElementById('auth').value;
                
                document.getElementById('status').innerText = 'Starting pentest...';
                
                // Simulate API call
                setTimeout(() => {
                    document.getElementById('status').innerText = 'Pentest in progress...';
                }, 1000);
            }
            
            function runScan() {
                document.getElementById('status').innerText = 'Running network scan...';
            }
            
            function generateReport() {
                document.getElementById('status').innerText = 'Generating report...';
            }
            
            function viewResults() {
                document.getElementById('status').innerText = 'Loading results...';
            }
        </script>
    </body>
    </html>
    """

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=False)