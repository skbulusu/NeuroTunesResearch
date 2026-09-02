from flask import Flask, render_template_string
import subprocess
import threading
import time
import os

app = Flask(__name__)

# Store Streamlit process
streamlit_process = None

def start_streamlit():
    """Start Streamlit app in background"""
    global streamlit_process
    try:
        streamlit_process = subprocess.Popen([
        'streamlit', 'run', 'clinical_dashboard.py',
        '--server.port=8501',
        '--server.address=0.0.0.0',
        '--server.headless=true'
        ])
        print("Streamlit started successfully")
    except Exception as e:
        print(f"Failed to start Streamlit: {e}")

@app.route('/')
def index():
    # Get ML machine IP from environment variable
    ml_machine_ip = os.getenv('ML_MACHINE_IP', 'localhost')
    streamlit_url = f"http://{ml_machine_ip}:8501"
    
    return render_template_string('''
    <html>
    <head>
    <title>NeuroTunes Clinical Dashboard</title>
    <style>
    body { font-family: Arial, sans-serif; margin: 40px; }
    .container { max-width: 800px; margin: 0 auto; }
    .btn { background: #0066cc; color: white; padding: 10px 20px; 
    text-decoration: none; border-radius: 5px; display: inline-block; }
    </style>
    </head>
    <body>
    <div class="container">
    <h1>🏥 NeuroTunes Clinical Dashboard</h1>
    <p>Clinical oversight and regulatory compliance for federated learning</p>
    <a href="{{ streamlit_url }}" class="btn" target="_blank">
    Open Clinical Dashboard
    </a>
    <h3>Features:</h3>
    <ul>
    <li>📊 Federated Learning Overview</li>
    <li>🏥 Healthcare Site Performance</li>
    <li>🔒 Privacy & Compliance Monitoring</li>
    <li>📈 Clinical Efficacy Analysis</li>
    <li>⚙️ System Status & Monitoring</li>
    </ul>
    </div>
    </body>
    </html>
    ''', streamlit_url=streamlit_url)

@app.route('/health')
def health():
    return {'status': 'healthy', 'service': 'clinical-dashboard'}

if __name__ == '__main__':
    # Start Streamlit in background thread
    streamlit_thread = threading.Thread(target=start_streamlit)
    streamlit_thread.daemon = True
    streamlit_thread.start()
    
    # Give Streamlit time to start
    time.sleep(3)
    
    # Start Flask app
    app.run(host='0.0.0.0', port=int(os.getenv('CLINICAL_DASHBOARD_PORT', '5003')) , debug=False)
