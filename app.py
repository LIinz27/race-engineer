from flask import Flask, render_template
from flask_socketio import SocketIO
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize Flask app and SocketIO
app = Flask(__name__)
app.config['SECRET_KEY'] = 'f1telemetry'
socketio = SocketIO(app, cors_allowed_origins="*")

# Routes
@app.route('/')
@app.route('/car-telemetry')
def car_telemetry():
    return render_template('car_telemetry.html', title='Car Telemetry')

@app.route('/time-telemetry')
def time_telemetry():
    return render_template('time_telemetry.html', title='Time Telemetry')

@app.route('/standings')
def standings():
    return render_template('standings.html', title='Driver Standings')

# Socket.IO events
@socketio.on('connect')
def handle_connect():
    logger.info('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    logger.info('Client disconnected')

if __name__ == '__main__':
    try:
        logger.info("Starting F1 Telemetry Web Application")
        # Start the telemetry data collection in a separate thread
        from telemetry.collector import start_telemetry_collection
        start_telemetry_collection(socketio)
        # Run the web server
        socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)
    except Exception as e:
        logger.error(f"Error in main application: {e}")
