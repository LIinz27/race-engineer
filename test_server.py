from flask import Flask, render_template
import logging

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Routes
@app.route('/')
def index():
    return render_template('test.html')

if __name__ == '__main__':
    try:
        logger.info("Starting Test Web Server")
        app.run(host='0.0.0.0', port=5000, debug=True)
    except Exception as e:
        logger.error(f"Error in test application: {e}")
