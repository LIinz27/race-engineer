"""
F1 24 Web Telemetry Dashboard
Real-time telemetry data via web browser
Menggunakan pendekatan parsing dari pits-n-giggles
"""

import socket
import struct
import threading
import time
from datetime import datetime
import json
import asyncio
from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO
import os

class F1WebTelemetryDashboard:
    def __init__(self, port=20777, web_port=5000):
        self.port = port
        self.web_port = web_port
        self.socket = None
        self.running = False
        self.data_thread = None
        self.debug_mode = True  # Enable debug to see what's happening
        
        # Setup Flask app
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'f1-telemetry-secret-key'
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")
        
        # Data telemetry terbaru - fokus pada position dan timing
        self.current_data = {
            'position': 0,
            'lap_number': 0,
            'current_lap_time': 0.0,
            'last_lap_time': 0.0,
            'best_lap_time': 0.0,
            'sector1_time': 0.0,
            'sector2_time': 0.0,
            'sector3_time': 0.0,
            'gap_to_leader': 0.0,
            'gap_to_car_ahead': 0.0,
            'driver_name': 'Unknown',
            'timestamp': None,
            'packets_received': 0,
            'valid_data': False,
            'last_update': None,
            'connection_status': 'disconnected'
        }
        
        # Lock untuk thread safety
        self.data_lock = threading.Lock()
        
        # Setup routes
        self.setup_routes()
    
    def format_lap_time(self, seconds):
        """Format lap time in MM:SS.mmm format"""
        if seconds <= 0:
            return "00:00.000"
        
        minutes = int(seconds // 60)
        remaining_seconds = seconds % 60
        return f"{minutes:02d}:{remaining_seconds:06.3f}"
    
    def format_sector_time(self, seconds):
        """Format sector time in SS.mmm format"""
        if seconds <= 0:
            return "00.000"
        return f"{seconds:06.3f}"
    
    def format_gap_time(self, seconds):
        """Format gap time"""
        if seconds <= 0:
            return "+0.000"
        
        if seconds < 60:
            return f"+{seconds:.3f}"
        else:
            minutes = int(seconds // 60)
            remaining_seconds = seconds % 60
            return f"+{minutes}:{remaining_seconds:06.3f}"
        
    def setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/')
        def index():
            return render_template('telemetry.html')
        
        @self.app.route('/api/telemetry')
        def get_telemetry():
            with self.data_lock:
                data = self.current_data.copy()
            
            # Calculate connection status
            if data.get('last_update'):
                time_diff = (datetime.now() - data['last_update']).total_seconds()
                if time_diff < 2:
                    data['connection_status'] = 'connected'
                elif time_diff < 5:
                    data['connection_status'] = 'warning'
                else:
                    data['connection_status'] = 'disconnected'
            else:
                data['connection_status'] = 'disconnected'
            
            # Format data for web - race position dan timing
            web_data = {
                'position': data.get('position', 0),
                'lap_number': data.get('lap_number', 0),
                'current_lap_time': self.format_lap_time(data.get('current_lap_time', 0.0)),
                'last_lap_time': self.format_lap_time(data.get('last_lap_time', 0.0)),
                'best_lap_time': self.format_lap_time(data.get('best_lap_time', 0.0)),
                'sector1_time': self.format_sector_time(data.get('sector1_time', 0.0)),
                'sector2_time': self.format_sector_time(data.get('sector2_time', 0.0)),
                'sector3_time': self.format_sector_time(data.get('sector3_time', 0.0)),
                'gap_to_leader': self.format_gap_time(data.get('gap_to_leader', 0.0)),
                'gap_to_car_ahead': self.format_gap_time(data.get('gap_to_car_ahead', 0.0)),
                'driver_name': data.get('driver_name', 'Unknown'),
                'packets_received': data.get('packets_received', 0),
                'connection_status': data['connection_status'],
                'timestamp': datetime.now().strftime('%H:%M:%S'),
                'valid_data': data.get('valid_data', False)
            }
            
            return jsonify(web_data)
        
        @self.socketio.on('connect')
        def handle_connect():
            print(f"🌐 Web client connected")
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            print(f"🌐 Web client disconnected")
    
    def setup_socket(self):
        """Setup UDP socket dengan konfigurasi optimal seperti pits-n-giggles"""
        try:
            self.socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self.socket.bind(('0.0.0.0', self.port))  # Bind to all interfaces
            self.socket.settimeout(1.0)
            print(f"✅ UDP Socket bound to port {self.port}")
            return True
        except Exception as e:
            print(f"❌ Error setup socket: {e}")
            return False
    
    def parse_packet_header(self, raw_packet: bytes):
        """Parse F1 24 packet header (inspired by pits-n-giggles)"""
        if len(raw_packet) < 29:  # F1 24 header is 29 bytes
            return None
            
        try:
            # F1 24 Header Format (29 bytes total)
            header_format = '<HBBBBBQfIIBB'
            header_data = struct.unpack(header_format, raw_packet[:29])
            
            return {
                'packet_format': header_data[0],      # uint16 - packet format (should be 2024)
                'game_year': header_data[1],          # uint8  - game year (24 for F1 24)
                'game_major_version': header_data[2], # uint8  - game major version
                'game_minor_version': header_data[3], # uint8  - game minor version  
                'packet_version': header_data[4],     # uint8  - packet version
                'packet_id': header_data[5],          # uint8  - packet type (0-15)
                'session_uid': header_data[6],        # uint64 - session UID
                'session_time': header_data[7],       # float  - session time
                'frame_identifier': header_data[8],   # uint32 - frame identifier
                'overall_frame_identifier': header_data[9], # uint32 - overall frame
                'player_car_index': header_data[10],  # uint8  - player car index
                'secondary_player_car_index': header_data[11] # uint8 - secondary player
            }
        except struct.error as e:
            if self.debug_mode:
                print(f"❌ Header parsing error: {e}")
            return None
    
    def parse_lap_data_packet(self, raw_packet: bytes, header):
        """Parse Lap Data packet menggunakan format pits-n-giggles yang akurat"""
        try:
            if header['packet_id'] != 2:  # Lap data packet ID
                return False
                
            if len(raw_packet) < 29 + 44:  # Header + minimal lap data
                return False
            
            # Skip header (29 bytes) and get first car's lap data
            payload = raw_packet[29:]
            player_car_index = header.get('player_car_index', 0)
            
            if self.debug_mode:
                print(f"🏁 Parsing lap data for player car index: {player_car_index}")
            
            # F1 24 Lap Data format (44 bytes per car)
            lap_data_format = '<IIHBHBHBHBffBBBBBBBBBBBBBBBBfB'
            lap_data_size = struct.calcsize(lap_data_format)
            
            # Extract data for player car
            offset = player_car_index * lap_data_size
            if offset + lap_data_size > len(payload):
                if self.debug_mode:
                    print(f"❌ Not enough data for player car {player_car_index}")
                return False
                
            car_data = payload[offset:offset + lap_data_size]
            lap_data = struct.unpack(lap_data_format, car_data)
            
            # Map data according to F1 24 specification
            last_lap_time_ms = lap_data[0]      # uint32
            current_lap_time_ms = lap_data[1]   # uint32
            sector1_time_ms = lap_data[2]       # uint16
            sector1_minutes = lap_data[3]       # uint8
            sector2_time_ms = lap_data[4]       # uint16
            sector2_minutes = lap_data[5]       # uint8
            delta_to_front_ms = lap_data[6]     # uint16
            delta_to_front_min = lap_data[7]    # uint8  
            delta_to_leader_ms = lap_data[8]    # uint16
            delta_to_leader_min = lap_data[9]   # uint8
            lap_distance = lap_data[10]         # float
            total_distance = lap_data[11]       # float
            safety_car_delta = lap_data[12]     # float
            car_position = lap_data[13]         # uint8
            current_lap_num = lap_data[14]      # uint8
            pit_status = lap_data[15]           # uint8
            num_pit_stops = lap_data[16]        # uint8
            sector = lap_data[17]               # uint8
            
            # Convert to seconds and add minutes
            last_lap_time = (last_lap_time_ms / 1000.0) if last_lap_time_ms > 0 else 0.0
            current_lap_time = (current_lap_time_ms / 1000.0) if current_lap_time_ms > 0 else 0.0
            sector1_time = (sector1_time_ms / 1000.0) + (sector1_minutes * 60) if sector1_time_ms > 0 else 0.0
            sector2_time = (sector2_time_ms / 1000.0) + (sector2_minutes * 60) if sector2_time_ms > 0 else 0.0
            gap_to_leader = (delta_to_leader_ms / 1000.0) + (delta_to_leader_min * 60)
            gap_to_front = (delta_to_front_ms / 1000.0) + (delta_to_front_min * 60)
            
            if self.debug_mode:
                print(f"🏁 Parsed: Pos={car_position}, Lap={current_lap_num}, LastLap={last_lap_time:.3f}s")
                print(f"🏁 Sectors: S1={sector1_time:.3f}s, S2={sector2_time:.3f}s")
                print(f"🏁 Gaps: Leader={gap_to_leader:.3f}s, Front={gap_to_front:.3f}s")
            
            # Validate data ranges
            if (1 <= car_position <= 22 and 
                0 <= current_lap_num <= 100 and
                0 <= last_lap_time <= 300):
                
                # Calculate sector 3 time
                sector3_time = 0.0
                if last_lap_time > 0 and sector1_time > 0 and sector2_time > 0:
                    sector3_time = last_lap_time - sector1_time - sector2_time
                    if sector3_time < 0:
                        sector3_time = 0.0
                
                # Update data
                with self.data_lock:
                    self.current_data.update({
                        'position': car_position,
                        'lap_number': current_lap_num,
                        'current_lap_time': current_lap_time,
                        'last_lap_time': last_lap_time,
                        'sector1_time': sector1_time,
                        'sector2_time': sector2_time,
                        'sector3_time': sector3_time,
                        'gap_to_leader': gap_to_leader,
                        'gap_to_car_ahead': gap_to_front,
                        'lap_distance': lap_distance,
                        'total_distance': total_distance,
                        'valid_data': True,
                        'last_update': datetime.now()
                    })
                
                # Emit to web clients
                self.emit_telemetry_update()
                
                if self.debug_mode:
                    print(f"✅ Lap data updated and emitted to web clients")
                
                return True
            else:
                if self.debug_mode:
                    print(f"❌ Data validation failed: pos={car_position}, lap={current_lap_num}, time={last_lap_time}")
                
        except struct.error as e:
            if self.debug_mode:
                print(f"❌ Lap data struct error: {e}")
        except Exception as e:
            if self.debug_mode:
                print(f"❌ Lap data parsing error: {e}")
        
        return False
    
    def parse_car_telemetry_packet(self, data):
        """Parse F1 24 packet data menggunakan pendekatan pits-n-giggles"""
        try:
            packet_size = len(data)
            
            # Update packet counter
            with self.data_lock:
                self.current_data['packets_received'] += 1
                self.current_data['timestamp'] = datetime.now()
            
            # Parse header dengan format yang benar
            header = self.parse_packet_header(data)
            
            if not header:
                if self.debug_mode:
                    print(f"❌ Failed to parse packet header")
                return False
            
            # Validate F1 24 packet
            if header['packet_format'] != 2024:
                if self.debug_mode:
                    print(f"❌ Invalid packet format: {header['packet_format']}")
                return False
            
            packet_id = header['packet_id']
            
            if self.debug_mode:
                timestamp = datetime.now().strftime("%H:%M:%S")
                print(f"[{timestamp}] Packet ID: {packet_id}, Size: {packet_size}, Format: {header['packet_format']}")
            
            # Focus on Lap Data (packet ID 2)
            if packet_id == 2 and packet_size > 1000:
                if self.debug_mode:
                    print(f"📊 Processing Lap Data packet - {packet_size} bytes")
                return self.parse_lap_data_packet(data, header)
            elif packet_id == 1:
                if self.debug_mode:
                    print(f"📋 Processing Session packet - {packet_size} bytes")
                # For now, just count session packets
                return True
            
            return False
                    
        except Exception as e:
            if self.debug_mode:
                print(f"❌ Packet parsing error: {e}")
            return False
    
    def emit_telemetry_update(self):
        """Emit telemetry update to web clients"""
        try:
            with self.data_lock:
                data = self.current_data.copy()
            
            web_data = {
                'position': data.get('position', 0),
                'lap_number': data.get('lap_number', 0),
                'current_lap_time': self.format_lap_time(data.get('current_lap_time', 0.0)),
                'last_lap_time': self.format_lap_time(data.get('last_lap_time', 0.0)),
                'best_lap_time': self.format_lap_time(data.get('best_lap_time', 0.0)),
                'sector1_time': self.format_sector_time(data.get('sector1_time', 0.0)),
                'sector2_time': self.format_sector_time(data.get('sector2_time', 0.0)),
                'sector3_time': self.format_sector_time(data.get('sector3_time', 0.0)),
                'gap_to_leader': self.format_gap_time(data.get('gap_to_leader', 0.0)),
                'gap_to_car_ahead': self.format_gap_time(data.get('gap_to_car_ahead', 0.0)),
                'driver_name': data.get('driver_name', 'Unknown'),
                'packets_received': data.get('packets_received', 0),
                'timestamp': datetime.now().strftime('%H:%M:%S'),
                'valid_data': data.get('valid_data', False)
            }
            
            self.socketio.emit('telemetry_update', web_data)
            
        except Exception as e:
            print(f"Error emitting telemetry: {e}")
    
    def start(self):
        """Start web dashboard"""
        print("🚀 Starting F1 24 Web Telemetry Dashboard...")
        
        if not self.setup_socket():
            return False
        
        self.running = True
        
        # Start data receiving thread
        self.data_thread = threading.Thread(target=self.receive_data, daemon=True)
        self.data_thread.start()
        
        print(f"� Web dashboard starting on http://localhost:{self.web_port}")
        print("📡 Listening for F1 24 telemetry data on UDP port 20777")
        print("🎮 Make sure F1 24 has UDP telemetry enabled")
        print("⚙️  Settings -> Telemetry Settings -> UDP Telemetry = On")
        print("🔧 Menggunakan parsing method dari pits-n-giggles untuk akurasi tinggi")
        print("-" * 60)
        
        try:
            # Start Flask-SocketIO server
            self.socketio.run(self.app, 
                            host='0.0.0.0', 
                            port=self.web_port, 
                            debug=False,
                            allow_unsafe_werkzeug=True)
        except KeyboardInterrupt:
            print("\n\n🛑 Dashboard stopped by user")
        finally:
            self.stop()
        
        return True
    
    def receive_data(self):
        """Thread untuk menerima data UDP dengan pendekatan async-like"""
        print("🎯 Starting UDP data reception...")
        
        packet_count = 0
        last_status_time = time.time()
        
        while self.running:
            try:
                # Receive with timeout
                data, addr = self.socket.recvfrom(4096)  # Increased buffer size
                packet_count += 1
                
                if self.debug_mode:
                    print(f"🎯 [DEBUG] Packet #{packet_count} from {addr}, size: {len(data)} bytes")
                
                # Process packet immediately
                self.parse_car_telemetry_packet(data)
                
            except socket.timeout:
                # Print periodic status
                current_time = time.time()
                if packet_count == 0 and (current_time - last_status_time) > 10:
                    print(f"⏰ [DEBUG] Still listening on port {self.port}... No packets received yet.")
                    print(f"🎮 [DEBUG] Make sure F1 24 telemetry is enabled and you're in a session!")
                    last_status_time = current_time
                continue
            except Exception as e:
                if self.running:
                    print(f"❌ Error receiving data: {e}")
                break
    
    def stop(self):
        """Stop dashboard"""
        print("\n🔄 Stopping dashboard...")
        self.running = False
        
        if self.socket:
            self.socket.close()
        
        if self.data_thread and self.data_thread.is_alive():
            self.data_thread.join(timeout=2)
        
        print("✅ Dashboard stopped")
            self.stop()
        
        return True
        """Thread untuk menerima data UDP dengan pendekatan async-like"""
        print("🎯 Starting UDP data reception...")
        
        packet_count = 0
        last_status_time = time.time()
        
        while self.running:
            try:
                # Receive with timeout
                data, addr = self.socket.recvfrom(4096)  # Increased buffer size
                packet_count += 1
                
                if self.debug_mode:
                    print(f"🎯 [DEBUG] Packet #{packet_count} from {addr}, size: {len(data)} bytes")
                
                # Process packet immediately
                self.parse_car_telemetry_packet(data)
                
            except socket.timeout:
                # Print periodic status
                current_time = time.time()
                if packet_count == 0 and (current_time - last_status_time) > 10:
                    print(f"⏰ [DEBUG] Still listening on port {self.port}... No packets received yet.")
                    print(f"🎮 [DEBUG] Make sure F1 24 telemetry is enabled and you're in a session!")
                    last_status_time = current_time
                continue
            except Exception as e:
                if self.running:
                    print(f"❌ Error receiving data: {e}")
                break
    
    def start(self):
        """Start web dashboard"""
        print("🚀 Starting F1 24 Web Telemetry Dashboard...")
        
        if not self.setup_socket():
            return False
        
        self.running = True
        
        # Start data receiving thread
        self.data_thread = threading.Thread(target=self.receive_data, daemon=True)
        self.data_thread.start()
        
        print(f"🌐 Web dashboard starting on http://localhost:{self.web_port}")
        print("📡 Listening for F1 24 telemetry data on UDP port 20777")
        print("🎮 Make sure F1 24 has UDP telemetry enabled")
        print("⚙️  Settings -> Telemetry Settings -> UDP Telemetry = On")
        print("-" * 60)
        
        try:
            # Start Flask-SocketIO server
            self.socketio.run(self.app, 
                            host='0.0.0.0', 
                            port=self.web_port, 
                            debug=False,
                            allow_unsafe_werkzeug=True)
        except KeyboardInterrupt:
            print("\n\n🛑 Dashboard stopped by user")
        finally:
            self.stop()
        
        return True
    
    def stop(self):
        """Stop dashboard"""
        print("\n🔄 Stopping dashboard...")
        self.running = False
        
        if self.socket:
            self.socket.close()
        
        if self.data_thread and self.data_thread.is_alive():
            self.data_thread.join(timeout=2)
        
        print("✅ Dashboard stopped")

def main():
    """Main function"""
    print("🏎️ F1 24 Web Telemetry Dashboard")
    print("=" * 50)
    
    dashboard = F1WebTelemetryDashboard()
    dashboard.start()

if __name__ == "__main__":
    main()
