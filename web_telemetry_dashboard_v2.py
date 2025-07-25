"""
F1 24 Web Telemetry Dashboard
Real-time telemetry data via web browser
Menggunakan pendekatan parsing dari pits-n-giggles untuk akurasi tinggi
"""

import socket
import struct
import threading
import time
from datetime import datetime
import json
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
        
        # Data telemetry terbaru - semua drivers dalam format tabel
        self.current_data = {
            'drivers': [],  # List of all drivers with their data
            'timestamp': None,
            'packets_received': 0,
            'valid_data': False,
            'last_update': None,
            'connection_status': 'disconnected',
            'session_type': 'Unknown'
        }
        
        # Driver names mapping dari session data
        self.driver_names = {}  # Will be populated from session packet
        
        # Lock untuk thread safety
        self.data_lock = threading.Lock()
        
        # Setup routes
        self.setup_routes()
    
    def setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/')
        def index():
            return render_template('telemetry_table.html')
        
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
            
            # Format data for web - tabel semua drivers
            web_data = {
                'drivers': data.get('drivers', []),
                'packets_received': data.get('packets_received', 0),
                'connection_status': data['connection_status'],
                'timestamp': datetime.now().strftime('%H:%M:%S'),
                'valid_data': data.get('valid_data', False),
                'session_type': data.get('session_type', 'Unknown'),
                'last_update': data.get('last_update').isoformat() if data.get('last_update') else None
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
    
    def format_lap_time(self, time_seconds):
        """Format lap time in MM:SS.sss format"""
        if time_seconds <= 0:
            return "--:--.---"
        
        minutes = int(time_seconds // 60)
        seconds = time_seconds % 60
        return f"{minutes}:{seconds:06.3f}"
    
    def format_sector_time(self, time_seconds):
        """Format sector time in SS.sss format"""
        if time_seconds <= 0:
            return "--.---"
        
        return f"{time_seconds:06.3f}"
    
    def format_gap_time(self, gap_seconds):
        """Format gap time"""
        if gap_seconds <= 0:
            return "Leader"
        elif gap_seconds < 60:
            return f"+{gap_seconds:.3f}s"
        else:
            minutes = int(gap_seconds // 60)
            seconds = gap_seconds % 60
            return f"+{minutes}:{seconds:06.3f}"

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

    def parse_participants_packet(self, raw_packet: bytes, header):
        """Parse Participants packet (ID=4) untuk mendapatkan nama driver yang akurat dari game"""
        try:
            if header['packet_id'] != 4:  # Participants packet ID
                return False
            
            # Skip header (29 bytes) and get participants data
            payload = raw_packet[29:]
            
            if self.debug_mode:
                print(f"🏎️ Parsing Participants packet for real driver names")
                print(f"🏎️ Payload size: {len(payload)} bytes")
            
            # F1 24 Participants Data format - from pits-n-giggles exact format
            participant_format = ("<"
                "B"   # uint8  m_aiControlled
                "B"   # uint8  m_driverId
                "B"   # uint8  networkId
                "B"   # uint8  m_teamId
                "B"   # uint8  m_myTeam
                "B"   # uint8  m_raceNumber
                "B"   # uint8  m_nationality
                "48s" # char   m_name[48]
                "B"   # uint8  m_yourTelemetry
                "B"   # uint8  m_showOnlineNames
                "H"   # uint16 m_techLevel
                "B"   # uint8  m_platform
            )
            participant_size = struct.calcsize(participant_format)  # Calculate actual size
            
            if self.debug_mode:
                print(f"🏎️ Calculated participant size: {participant_size} bytes")
                print(f"🏎️ Total payload: {len(payload)} bytes, Expected: {20 * participant_size}")
            
            # Check if we have enough data
            if len(payload) < 20 * participant_size:
                if self.debug_mode:
                    print(f"❌ Insufficient payload: {len(payload)} < {20 * participant_size}")
                return False
            
            # Clear existing names
            self.driver_names.clear()
            
            # Parse all 20 participants
            for driver_idx in range(20):
                offset = driver_idx * participant_size
                if offset + participant_size > len(payload):
                    break
                    
                participant_data = payload[offset:offset + participant_size]
                
                try:
                    # Unpack participant data
                    unpacked = struct.unpack(participant_format, participant_data)
                    raw_name = unpacked[7]  # m_name[48]
                    
                    # Decode name and clean it
                    driver_name = raw_name.decode('utf-8', errors='replace').rstrip('\x00').strip()
                    
                    if self.debug_mode:
                        print(f"🔧 Raw name before processing: '{driver_name}' for driver {driver_idx:02d}")
                    
                    # Clean up any non-printable characters and numbers
                    driver_name = ''.join(char for char in driver_name if char.isprintable()).strip()
                    
                    # Remove leading numbers and special characters
                    driver_name = ''.join(char for char in driver_name if char.isalpha() or char.isspace()).strip()
                    
                    if self.debug_mode:
                        print(f"🔧 After cleaning: '{driver_name}' for driver {driver_idx:02d}")
                    
                    # Fix known problematic names with direct mapping
                    name_fixes = {
                        'LECLERC': 'LEC',
                        'CHARLES LECLERC': 'LEC', 
                        'LE': 'LEC',  # Common truncation
                        'PEREZ': 'PER',
                        'SERGIO PEREZ': 'PER',
                        'PÉ': 'PER',  # Special character issue
                        'PÉREZ': 'PER',
                        'TSUNODA': 'TSU',
                        'YUKI TSUNODA': 'TSU',
                        'TS': 'TSU',  # Common truncation
                        'MAGNUSSEN': 'MAG',
                        'KEVIN MAGNUSSEN': 'MAG',
                        'VERSTAPPEN': 'VER',
                        'MAX VERSTAPPEN': 'VER',
                        'HAMILTON': 'HAM',
                        'LEWIS HAMILTON': 'HAM',
                        'RUSSELL': 'RUS',
                        'GEORGE RUSSELL': 'RUS',
                        'NORRIS': 'NOR',
                        'LANDO NORRIS': 'NOR',
                        'PIASTRI': 'PIA',
                        'OSCAR PIASTRI': 'PIA',
                        'ALONSO': 'ALO',
                        'FERNANDO ALONSO': 'ALO',
                        'STROLL': 'STR',
                        'LANCE STROLL': 'STR',
                        'SAINZ': 'SAI',
                        'CARLOS SAINZ': 'SAI',
                        'CARLOS SAINZ JR': 'SAI',
                        'SAINZ JR': 'SAI',
                        'MSAINZ': 'SAI',  # Fix MSAINZ -> SAI (Carlos Sainz)
                        'RICCIARDO': 'RIC',
                        'DANIEL RICCIARDO': 'RIC',
                        'GASLY': 'GAS',
                        'PIERRE GASLY': 'GAS',
                        'OCON': 'OCO',
                        'ESTEBAN OCON': 'OCO',
                        'BOTTAS': 'BOT',
                        'VALTTERI BOTTAS': 'BOT',
                        'ZHOU': 'ZHO',
                        'GUANYU ZHOU': 'ZHO',
                        'HULKENBERG': 'HUL',
                        'NICO HULKENBERG': 'HUL',
                        'ALBON': 'ALB',
                        'ALEXANDER ALBON': 'ALB',
                        'PALBON': 'ALB'  # Fix PALBON -> ALB (Alexander Albon)
                    }
                    
                    # If name is empty, create fallback
                    if not driver_name:
                        driver_name = f"CAR{driver_idx:02d}"
                    else:
                        # Check for direct fix first
                        driver_name_upper = driver_name.upper()
                        if driver_name_upper in name_fixes:
                            fixed_name = name_fixes[driver_name_upper]
                            if self.debug_mode:
                                print(f"🔧 MAPPING FIX: '{driver_name}' -> '{fixed_name}' for driver {driver_idx:02d}")
                            driver_name = fixed_name
                        else:
                            # Convert to 3-letter abbreviation if it's a full name
                            if len(driver_name) > 3:
                                # Try to extract 3-letter code from name
                                name_parts = driver_name.split()
                                if len(name_parts) >= 2:
                                    # First 3 letters of last name (common F1 convention)
                                    last_name = name_parts[-1].upper()
                                    # Check if last name has a direct mapping
                                    if last_name in name_fixes:
                                        fixed_name = name_fixes[last_name]
                                        if self.debug_mode:
                                            print(f"🔧 LASTNAME FIX: '{driver_name}' (lastname: '{last_name}') -> '{fixed_name}' for driver {driver_idx:02d}")
                                        driver_name = fixed_name
                                    else:
                                        driver_name = last_name[:3]
                                else:
                                    driver_name = driver_name[:3].upper()
                            else:
                                driver_name = driver_name.upper()
                    
                    # Store in mapping
                    self.driver_names[driver_idx] = driver_name
                    
                    if self.debug_mode:
                        print(f"🏎️ Driver {driver_idx:02d}: {driver_name}")
                        
                except Exception as e:
                    if self.debug_mode:
                        print(f"❌ Error parsing participant {driver_idx}: {e}")
                    # Fallback name
                    self.driver_names[driver_idx] = f"CAR{driver_idx:02d}"
            
            if self.debug_mode:
                print(f"✅ Participants packet processed - {len(self.driver_names)} driver names updated")
                print(f"🎮 Driver mapping: {self.driver_names}")
            
            return True
            
        except Exception as e:
            if self.debug_mode:
                print(f"❌ Participants packet parsing error: {e}")
            return False

    def parse_session_packet(self, raw_packet: bytes, header):
        """Parse Session packet untuk informasi session"""
        try:
            if header['packet_id'] != 1:  # Session packet ID
                return False
            
            if self.debug_mode:
                print(f"📋 Session packet received")
            
            return True
            
        except Exception as e:
            if self.debug_mode:
                print(f"❌ Session packet parsing error: {e}")
            return False

    def parse_lap_data_packet(self, raw_packet: bytes, header):
        """Parse Lap Data packet untuk semua drivers menggunakan format F1 24"""
        try:
            if header['packet_id'] != 2:  # Lap data packet ID
                return False
                
            if len(raw_packet) < 29 + (20 * 61):  # Header + 20 drivers * 61 bytes each
                return False
            
            # Skip header (29 bytes) and get all drivers data
            payload = raw_packet[29:]
            
            if self.debug_mode:
                print(f"🏁 Parsing F1 24 lap data for all drivers")
                # Debug: print driver positions and names for troubleshooting
                debug_drivers = []
            
            # F1 24 Lap Data format (accurate dari pits-n-giggles) - 61 bytes per car
            lap_data_format_24 = ("<"
                "I" # uint32   m_lastLapTimeInMS;                // Last lap time in milliseconds
                "I" # uint32   m_currentLapTimeInMS;      // Current time around the lap in milliseconds
                "H" # uint16   m_sector1TimeMSPart;         // Sector 1 time milliseconds part
                "B" # uint8    m_sector1TimeMinutesPart;    // Sector 1 whole minute part
                "H" # uint16   m_sector2TimeMSPart;         // Sector 2 time milliseconds part
                "B" # uint8    m_sector2TimeMinutesPart;    // Sector 2 whole minute part
                "H" # uint16   m_deltaToCarInFrontMSPart;   // Time delta to car in front milliseconds part
                "B" # uint8    m_deltaToCarInFrontMinutesPart; // Time delta to car in front whole minute part
                "H" # uint16   m_deltaToRaceLeaderMSPart;      // Time delta to race leader milliseconds part
                "B" # uint8    m_deltaToRaceLeaderMinutesPart; // Time delta to race leader whole minute part
                "f" # float    m_lapDistance;         // Distance vehicle is around current lap in metres
                "f" # float    m_totalDistance;         // Total distance travelled in session in metres
                "f" # float    m_safetyCarDelta;            // Delta in seconds for safety car
                "B" # uint8    m_carPosition;                // Car race position
                "B" # uint8    m_currentLapNum;         // Current lap number
                "B" # uint8    m_pitStatus;                 // 0 = none, 1 = pitting, 2 = in pit area
                "B" # uint8    m_numPitStops;                 // Number of pit stops taken in this race
                "B" # uint8    m_sector;                    // 0 = sector1, 1 = sector2, 2 = sector3
                "B" # uint8    m_currentLapInvalid;         // Current lap invalid - 0 = valid, 1 = invalid
                "B" # uint8    m_penalties;                 // Accumulated time penalties in seconds to be added
                "B" # uint8    m_totalWarnings;             // Accumulated number of warnings issued
                "B" # uint8    m_cornerCuttingWarnings;     // Accumulated number of corner cutting warnings issued
                "B" # uint8    m_numUnservedDriveThroughPens;  // Num drive through pens left to serve
                "B" # uint8    m_numUnservedStopGoPens;        // Num stop go pens left to serve
                "B" # uint8    m_gridPosition;              // Grid position the vehicle started the race in
                "B" # uint8    m_driverStatus;              // Status of driver - 0 = in garage, 1 = flying lap
                "B" # uint8    m_resultStatus;              // Result status - 0 = invalid, 1 = inactive, 2 = active
                "B" # uint8    m_pitLaneTimerActive;          // Pit lane timing, 0 = inactive, 1 = active
                "H" # uint16   m_pitLaneTimeInLaneInMS;        // If active, the current time spent in the pit lane in ms
                "H" # uint16   m_pitStopTimerInMS;             // Time of the actual pit stop in ms
                "B" # uint8    m_pitStopShouldServePen;        // Whether the car should serve a penalty at this stop
                "f" # float    m_speedTrapFastestSpeed;     // Fastest speed through speed trap for this car in kmph
                "B" # uint8    m_speedTrapFastestLap;       // Lap no the fastest speed was achieved, 255 = not set
            )
            lap_data_size = struct.calcsize(lap_data_format_24)
            
            if self.debug_mode:
                print(f"🏁 F1 24 lap data size: {lap_data_size} bytes per car")
            
            # Parse data for all 20 drivers
            drivers_data = []
            
            for driver_idx in range(20):
                offset = driver_idx * lap_data_size
                if offset + lap_data_size > len(payload):
                    break
                    
                car_data = payload[offset:offset + lap_data_size]
                lap_data = struct.unpack(lap_data_format_24, car_data)
                
                # Map data according to F1 24 specification
                last_lap_time_ms = lap_data[0]           # uint32
                current_lap_time_ms = lap_data[1]        # uint32
                sector1_time_ms = lap_data[2]            # uint16
                sector1_minutes = lap_data[3]            # uint8
                sector2_time_ms = lap_data[4]            # uint16
                sector2_minutes = lap_data[5]            # uint8
                delta_to_front_ms = lap_data[6]          # uint16
                delta_to_front_min = lap_data[7]         # uint8  
                delta_to_leader_ms = lap_data[8]         # uint16
                delta_to_leader_min = lap_data[9]        # uint8
                lap_distance = lap_data[10]              # float
                total_distance = lap_data[11]            # float
                safety_car_delta = lap_data[12]          # float
                car_position = lap_data[13]              # uint8
                current_lap_num = lap_data[14]           # uint8
                pit_status = lap_data[15]                # uint8
                num_pit_stops = lap_data[16]             # uint8
                sector = lap_data[17]                    # uint8
                current_lap_invalid = lap_data[18]       # uint8
                penalties = lap_data[19]                 # uint8
                driver_status = lap_data[25]             # uint8
                result_status = lap_data[26]             # uint8
                
                # Convert to seconds and add minutes properly
                last_lap_time = (last_lap_time_ms / 1000.0) if last_lap_time_ms > 0 else 0.0
                current_lap_time = (current_lap_time_ms / 1000.0) if current_lap_time_ms > 0 else 0.0
                sector1_time = (sector1_time_ms / 1000.0) + (sector1_minutes * 60) if sector1_time_ms > 0 else 0.0
                sector2_time = (sector2_time_ms / 1000.0) + (sector2_minutes * 60) if sector2_time_ms > 0 else 0.0
                gap_to_leader = (delta_to_leader_ms / 1000.0) + (delta_to_leader_min * 60)
                gap_to_front = (delta_to_front_ms / 1000.0) + (delta_to_front_min * 60)
                
                # Calculate sector 3 time
                sector3_time = 0.0
                if last_lap_time > 0 and sector1_time > 0 and sector2_time > 0:
                    sector3_time = last_lap_time - sector1_time - sector2_time
                    if sector3_time < 0:
                        sector3_time = 0.0
                
                # Only include drivers with valid data
                if (result_status in [1, 2, 3] and  # 1=inactive, 2=active, 3=finished
                    0 <= car_position <= 22 and 
                    0 <= current_lap_num <= 100):
                    
                    # Gunakan driver names dari session data atau fallback ke CAR##
                    driver_name = self.driver_names.get(driver_idx, f"CAR{driver_idx:02d}")
                    
                    # Debug: show position vs driver_idx mapping
                    if self.debug_mode:
                        print(f"🏁 Driver debug: Idx={driver_idx:02d}, Position={car_position}, Name={driver_name}")
                        
                        # Extra debug: show who is actually in position 1
                        if car_position == 1:
                            print(f"🥇 POSITION 1 IS: Idx={driver_idx:02d}, Name={driver_name}")
                        elif car_position == 2:
                            print(f"🥈 POSITION 2 IS: Idx={driver_idx:02d}, Name={driver_name}")
                        elif car_position == 3:
                            print(f"🥉 POSITION 3 IS: Idx={driver_idx:02d}, Name={driver_name}")
                    
                    # Determine pit status text
                    pit_status_text = "Track"
                    if pit_status == 1:
                        pit_status_text = "Pitting"
                    elif pit_status == 2:
                        pit_status_text = "Pit Lane"
                    
                    driver_data = {
                        'position': car_position,
                        'driver_name': driver_name,
                        'lap_number': current_lap_num,
                        'last_lap_time': self.format_lap_time(last_lap_time),
                        'current_lap_time': self.format_lap_time(current_lap_time),
                        'sector1_time': self.format_sector_time(sector1_time),
                        'sector2_time': self.format_sector_time(sector2_time),
                        'sector3_time': self.format_sector_time(sector3_time),
                        'gap_to_leader': self.format_gap_time(gap_to_leader),
                        'gap_to_front': self.format_gap_time(gap_to_front),
                        'pit_status': pit_status_text,
                        'pit_stops': num_pit_stops,
                        'current_lap_invalid': bool(current_lap_invalid),
                        'penalties': penalties,
                        'driver_status': driver_status,
                        'result_status': result_status
                    }
                    
                    drivers_data.append(driver_data)
                    
                    # Debug: track for troubleshooting
                    if self.debug_mode:
                        debug_drivers.append(f"Idx:{driver_idx} Name:{driver_name} Pos:{car_position}")
            
            # Sort drivers by position ASC saja - simple sorting
            drivers_data.sort(key=lambda x: x['position'] if x['position'] > 0 else 999)
            
            # Debug: print sorted order
            if self.debug_mode and len(drivers_data) > 0:
                print(f"🏁 Debug drivers before sort: {debug_drivers}")
                sorted_debug = [f"{d['driver_name']}(P{d['position']})" for d in drivers_data[:5]]
                print(f"🏁 Debug top 5 after sort: {sorted_debug}")
            
            # Update data
            with self.data_lock:
                self.current_data.update({
                    'drivers': drivers_data,
                    'valid_data': len(drivers_data) > 0,
                    'last_update': datetime.now()
                })
            
            # Emit to web clients
            self.emit_telemetry_update()
            
            if self.debug_mode:
                print(f"✅ F1 24 parsed {len(drivers_data)} drivers and emitted to web clients")
            
            return True
                
        except struct.error as e:
            if self.debug_mode:
                print(f"❌ F1 24 lap data struct error: {e}")
        except Exception as e:
            if self.debug_mode:
                print(f"❌ F1 24 lap data parsing error: {e}")
        
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
            
            # Focus on important packets
            if packet_id == 2 and packet_size > 1000:
                if self.debug_mode:
                    print(f"📊 Processing Lap Data packet - {packet_size} bytes")
                return self.parse_lap_data_packet(data, header)
            elif packet_id == 1:
                if self.debug_mode:
                    print(f"📋 Processing Session packet - {packet_size} bytes")
                return self.parse_session_packet(data, header)
            elif packet_id == 4:
                if self.debug_mode:
                    print(f"🏎️ Processing Participants packet - {packet_size} bytes")
                return self.parse_participants_packet(data, header)
            
            return False
                    
        except Exception as e:
            if self.debug_mode:
                print(f"❌ Packet parsing error: {e}")
            return False
    
    def emit_telemetry_update(self):
        """Emit telemetry update to web clients untuk format tabel"""
        try:
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
            
            web_data = {
                'drivers': data.get('drivers', []),
                'packets_received': data.get('packets_received', 0),
                'connection_status': data['connection_status'],
                'timestamp': datetime.now().strftime('%H:%M:%S'),
                'valid_data': data.get('valid_data', False),
                'session_type': data.get('session_type', 'Unknown'),
                'last_update': data.get('last_update').isoformat() if data.get('last_update') else None
            }
            
            self.socketio.emit('telemetry_update', web_data)
            
        except Exception as e:
            print(f"Error emitting telemetry: {e}")

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
