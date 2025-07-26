import socket
import struct
import threading
import time
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)

# Based on F1 game UDP specification
# Reference: pits-n-giggles telemetry processing

# Constants
UDP_IP = "0.0.0.0"
UDP_PORT = 20777  # Default F1 game telemetry port

# Packet IDs based on F1 game specification
MOTION_PACKET_ID = 0
SESSION_PACKET_ID = 1
LAP_DATA_PACKET_ID = 2
EVENT_PACKET_ID = 3
PARTICIPANTS_PACKET_ID = 4
CAR_SETUPS_PACKET_ID = 5
CAR_TELEMETRY_PACKET_ID = 6
CAR_STATUS_PACKET_ID = 7
FINAL_CLASSIFICATION_PACKET_ID = 8
LOBBY_INFO_PACKET_ID = 9
CAR_DAMAGE_PACKET_ID = 10
SESSION_HISTORY_PACKET_ID = 11

# Global state to store telemetry data
telemetry_state = {
    'car_telemetry': {},
    'lap_data': {},
    'session_data': {},
    'participants': {},
    'car_status': {},
    'last_update': datetime.now().isoformat()
}

def parse_header(header_data):
    """Parse the F1 packet header"""
    header_format = '<HBBBBQfIBB'
    header_size = struct.calcsize(header_format)
    
    unpacked = struct.unpack(header_format, header_data[:header_size])
    
    header = {
        'packet_format': unpacked[0],
        'game_major_version': unpacked[1],
        'game_minor_version': unpacked[2],
        'packet_version': unpacked[3],
        'packet_id': unpacked[4],
        'session_uid': unpacked[5],
        'session_time': unpacked[6],
        'frame_identifier': unpacked[7],
        'player_car_index': unpacked[8],
        'secondary_player_car_index': unpacked[9]
    }
    
    return header, header_size

def parse_car_telemetry_packet(data, header):
    """Parse car telemetry data packet"""
    try:
        # Extract player car index from header
        player_car_index = header['player_car_index']
        
        # Define the structure for a single car's telemetry
        car_format = '<HfffBbHBBHHBBHHfBB'
        car_size = struct.calcsize(car_format)
        
        # Calculate offset to the player's car data
        offset = 24  # Header size is typically 24 bytes
        car_offset = offset + (player_car_index * car_size)
        
        # Unpack the player's car telemetry data
        car_data = struct.unpack(car_format, data[car_offset:car_offset+car_size])
        
        # Map the unpacked data to a dictionary
        telemetry = {
            'speed': car_data[0],  # Speed in km/h
            'throttle': car_data[1] * 100,  # Convert to percentage
            'steer': car_data[2],  # Steering (-1.0 to 1.0)
            'brake': car_data[3] * 100,  # Convert to percentage
            'clutch': car_data[4],
            'gear': car_data[5],  # -1 = reverse, 0 = neutral, 1-8 = gears
            'engine_rpm': car_data[6],
            'drs': car_data[7],  # 0 = off, 1 = on
            'rev_lights_percent': car_data[8],
            'rev_lights_bit_value': car_data[9],
            'brakes_temperature': {
                'rear_left': car_data[10],
                'rear_right': car_data[11],
                'front_left': car_data[12],
                'front_right': car_data[13]
            },
            'tyres_surface_temperature': {
                'rear_left': car_data[14],
                'rear_right': car_data[15],
                'front_left': car_data[16],
                'front_right': car_data[17]
            },
            'engine_temperature': car_data[18],
            'tyre_pressure_status': car_data[19],
            'current_telemetry_surface_type': car_data[20]
        }
        
        # Update the global state
        telemetry_state['car_telemetry'] = telemetry
        telemetry_state['last_update'] = datetime.now().isoformat()
        
        return telemetry
    except Exception as e:
        logger.error(f"Error parsing car telemetry packet: {e}")
        return None

def parse_lap_data_packet(data, header):
    """Parse lap data packet"""
    try:
        # Extract player car index from header
        player_car_index = header['player_car_index']
        
        # Define the structure for lap data (simplified for this example)
        lap_format = '<iIBBBBffBBBBBBfHHHHffBBfffBBBBBB'
        lap_size = struct.calcsize(lap_format)
        
        # Calculate offset to the player's lap data
        offset = 24  # Header size is typically 24 bytes
        lap_offset = offset + (player_car_index * lap_size)
        
        # Unpack the player's lap data
        lap_data_unpacked = struct.unpack(lap_format, data[lap_offset:lap_offset+lap_size])
        
        # Map the unpacked data to a dictionary (simplified)
        lap_data = {
            'last_lap_time_in_ms': lap_data_unpacked[0],
            'current_lap_time_in_ms': lap_data_unpacked[1],
            'sector1_time_in_ms': lap_data_unpacked[2],
            'sector2_time_in_ms': lap_data_unpacked[3],
            'lap_distance': lap_data_unpacked[4],
            'total_distance': lap_data_unpacked[5],
            'safety_car_delta': lap_data_unpacked[6],
            'car_position': lap_data_unpacked[7],
            'current_lap_num': lap_data_unpacked[8],
            'pit_status': lap_data_unpacked[9],
            'sector': lap_data_unpacked[10],
            'current_lap_invalid': lap_data_unpacked[11],
            'penalties': lap_data_unpacked[12],
            'grid_position': lap_data_unpacked[13],
            'driver_status': lap_data_unpacked[14],
            'result_status': lap_data_unpacked[15]
        }
        
        # Update the global state
        telemetry_state['lap_data'] = lap_data
        telemetry_state['last_update'] = datetime.now().isoformat()
        
        return lap_data
    except Exception as e:
        logger.error(f"Error parsing lap data packet: {e}")
        return None

def process_packet(data, socketio):
    """Process a received UDP packet"""
    try:
        # Parse the packet header
        header, header_size = parse_header(data)
        
        # Process different packet types based on packet_id
        if header['packet_id'] == CAR_TELEMETRY_PACKET_ID:
            telemetry = parse_car_telemetry_packet(data, header)
            if telemetry:
                # Emit telemetry data via Socket.IO
                socketio.emit('car_telemetry_update', telemetry)
        
        elif header['packet_id'] == LAP_DATA_PACKET_ID:
            lap_data = parse_lap_data_packet(data, header)
            if lap_data:
                # Emit lap data via Socket.IO
                socketio.emit('lap_data_update', lap_data)
        
        # Additional packet types can be added here
        
    except Exception as e:
        logger.error(f"Error processing packet: {e}")

def udp_server_thread(socketio):
    """Thread function to run UDP server"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))
    
    logger.info(f"UDP server started on {UDP_IP}:{UDP_PORT}")
    
    while True:
        try:
            data, addr = sock.recvfrom(2048)  # Buffer size is 2048 bytes
            process_packet(data, socketio)
        except Exception as e:
            logger.error(f"Error in UDP server: {e}")

def start_telemetry_collection(socketio):
    """Start the telemetry collection in a separate thread"""
    thread = threading.Thread(target=udp_server_thread, args=(socketio,))
    thread.daemon = True
    thread.start()
    logger.info("Telemetry collection started")
    return thread
