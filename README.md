# F1 Telemetry Web Application

A web-based application that displays F1 game telemetry data across three pages:

1. **Car Telemetry** - Shows real-time car data (speed, RPM, gear, throttle/brake, etc.)
2. **Time Telemetry** - Displays lap times, sector times, and lap history
3. **Driver Standings** - Shows a comprehensive table with driver positions and lap times

## Features

- Real-time data updates via WebSockets
- Responsive design that works on different screen sizes
- Interactive gauges and visualizations
- Session information and weather conditions
- Comprehensive timing data with delta comparisons

## Setup Instructions

### Prerequisites

- Python 3.9 or higher
- F1 game (F1 2023/2024/2025) with UDP telemetry enabled

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/f1-telemetry-web.git
   cd f1-telemetry-web
   ```

2. Create a virtual environment (optional but recommended):
   ```
   python -m venv venv
   ```

3. Activate the virtual environment:
   - On Windows:
     ```
     venv\Scripts\activate
     ```
   - On macOS/Linux:
     ```
     source venv/bin/activate
     ```

4. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

## Running the Application

1. Start the web application:
   ```
   python app.py
   ```

2. Open a web browser and navigate to:
   ```
   http://localhost:5000
   ```

3. Launch your F1 game and enable UDP telemetry in the game settings:
   - Set the UDP IP to your computer's IP address
   - Set the UDP port to 20777 (default)
   - Enable UDP telemetry

## Configuring F1 Game Telemetry

In F1 2023/2024/2025 games:

1. Go to Game Options > Settings > Telemetry Settings
2. Set UDP Telemetry to "On"
3. Set UDP Broadcast Mode to "Off"
4. Set UDP IP Address to your computer's IP address (or "127.0.0.1" for local testing)
5. Set UDP Port to 20777
6. Set UDP Send Rate to "Ultra High" for best results
7. Set UDP Format to "2023" (or the latest format available)

## Project Structure

```
race-engineer/
├── app.py                # Main application file
├── requirements.txt      # Python dependencies
├── static/              
│   ├── css/              # CSS stylesheets
│   │   ├── main.css
│   │   ├── car_telemetry.css
│   │   ├── time_telemetry.css
│   │   └── standings.css
│   └── js/               # JavaScript files
│       ├── car_telemetry.js
│       ├── time_telemetry.js
│       └── standings.js
├── templates/            # HTML templates
│   ├── car_telemetry.html
│   ├── time_telemetry.html
│   └── standings.html
└── telemetry/           # Telemetry data processing
    ├── __init__.py
    └── collector.py     # UDP packet receiver and parser
```

## Acknowledgments

This project uses the F1 game UDP telemetry format. It was inspired by the "pits-n-giggles" project.

## License

This project is licensed under the MIT License.
