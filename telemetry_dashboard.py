"""
F1 24 Telemetry Dashboard
Menampilkan data telemetry real-time seperti speed, gear, throttle, brake, RPM
"""

import socket
import struct
import threading
import time
from datetime import datetime
import os

class F1TelemetryDashboard:
    def __init__(self, port=20777):
        self.port = port
        self.socket = None
        self.running = False
        self.data_thread = None
        self.debug_mode = False  # Set to True for detailed packet analysis
        
        # Data telemetry terbaru
        self.current_data = {
            'speed': 0,
            'gear': 0,
            'throttle': 0.0,
            'brake': 0.0,
            'rpm': 0,
            'timestamp': None,
            'packets_received': 0,
            'valid_data': False
        }
        
        # Lock untuk thread safety
        self.data_lock = threading.Lock()
        
    def setup_socket(self):
        """Setup UDP socket untuk menerima data F1 24"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind(('', self.port))
            self.socket.settimeout(1.0)  # Timeout 1 detik
            print(f"✅ Socket berhasil dibind ke port {self.port}")
            return True
        except Exception as e:
            print(f"❌ Error setup socket: {e}")
            return False
    
    def parse_car_telemetry_packet(self, data):
        """Parse paket telemetry mobil F1 24 dengan analisis hex yang benar"""
        try:
            packet_size = len(data)
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            
            # Selalu update counter dan tampilkan paket yang diterima
            with self.data_lock:
                self.current_data['packets_received'] += 1
                self.current_data['timestamp'] = datetime.now()
            
            # Analisis pola hex: e8071801130103... 
            # Berdasarkan F1 24 spec yang benar:
            # Offset 0-1: packet format (2007 = 0x07E8 little endian)
            # Offset 2: game major version 
            # Offset 3: game minor version
            # Offset 4: packet version
            # Offset 5: packet ID
            
            if packet_size >= 10:
                try:
                    # Baca packet ID dari offset yang benar
                    packet_id = data[6]  # Packet ID di offset 6, bukan 5
                    
                    if self.debug_mode:
                        hex_preview = data[:24].hex()
                        print(f"Received {packet_size:4d} bytes from ('192.168.101.2', 58880) at {timestamp}")
                        print(f"📦 Packet ID: {packet_id:2d} | Size: {packet_size:4d} | Preview: {hex_preview}")
                        
                        # Analisis header F1 24 lengkap
                        print(f"🔍 Full Header Analysis (F1 24):")
                        print(f"   Format: 0x{data[0]:02X}{data[1]:02X} (expected: 0xE807 for F1 24)")
                        print(f"   Game Major Ver: {data[2]} (expected: 24)")  
                        print(f"   Game Minor Ver: {data[3]}")
                        print(f"   Packet Version: {data[4]} (expected: 1)")
                        print(f"   Packet ID: {data[5]} (looking for 6=Car Telemetry)")
                        
                        if len(data) >= 28:
                            session_uid = struct.unpack('<Q', data[6:14])[0]  # uint64
                            session_time = struct.unpack('<f', data[14:18])[0]  # float
                            frame_id = struct.unpack('<I', data[18:22])[0]  # uint32
                            overall_frame_id = struct.unpack('<I', data[22:26])[0]  # uint32
                            player_car_idx = data[26]  # uint8
                            secondary_player_car_idx = data[27]  # uint8
                            
                            print(f"   Session UID: {session_uid}")
                            print(f"   Session Time: {session_time:.3f}s")
                            print(f"   Frame ID: {frame_id}")
                            print(f"   Overall Frame ID: {overall_frame_id}")  
                            print(f"   Player Car Index: {player_car_idx}")
                            print(f"   Secondary Player Car Index: {secondary_player_car_idx}")
                        print()
                    
                    # Fokus pada car telemetry (packet ID 6) 
                    if packet_id == 6 and packet_size > 1000:  # Car telemetry biasanya >1000 bytes
                        print("🏎️ Car Telemetry Packet detected!")
                        
                        # F1 24 header biasanya 24 bytes
                        header_size = 24
                        
                        if packet_size >= header_size + 60:  # Cukup data untuk parsing telemetry
                            try:
                                base_offset = header_size
                                
                                # Parse car telemetry data untuk mobil pertama (player)
                                # Format F1 24: speed(4), throttle(4), steer(4), brake(4), clutch(1), gear(1), engineRPM(2), ...
                                speed = struct.unpack('<f', data[base_offset:base_offset+4])[0]
                                throttle = struct.unpack('<f', data[base_offset+4:base_offset+8])[0]
                                steer = struct.unpack('<f', data[base_offset+8:base_offset+12])[0]
                                brake = struct.unpack('<f', data[base_offset+12:base_offset+16])[0]
                                clutch = data[base_offset+16]
                                gear = struct.unpack('<b', data[base_offset+17:base_offset+18])[0]  # signed byte
                                engine_rpm = struct.unpack('<H', data[base_offset+18:base_offset+20])[0]
                                
                                # Validasi data
                                if (0 <= speed <= 400 and 
                                    0 <= throttle <= 1.1 and 
                                    0 <= brake <= 1.1 and
                                    0 <= engine_rpm <= 20000 and
                                    -2 <= gear <= 8):
                                    
                                    speed_kmh = int(speed)
                                    gear_display = str(gear) if gear > 0 else ('R' if gear == -1 else 'N')
                                    
                                    # Tampilkan data streaming
                                    print(f"🏁 Speed: {speed_kmh:3d} km/h | Gear: {gear_display:>2} | Throttle: {throttle*100:5.1f}% | Brake: {brake*100:5.1f}% | RPM: {engine_rpm:5d}")
                                    
                                    with self.data_lock:
                                        self.current_data.update({
                                            'speed': speed_kmh,
                                            'gear': gear_display,
                                            'throttle': throttle,
                                            'brake': brake,
                                            'rpm': engine_rpm,
                                            'steer': steer,
                                            'clutch': clutch,
                                            'valid_data': True
                                        })
                                    
                                    return True
                                    
                            except struct.error as e:
                                if self.debug_mode:
                                    print(f"❌ Telemetry parsing error: {e}")
                    
                    elif self.debug_mode:
                        # Info untuk packet types lain (hanya tampilkan yang relevan)
                        packet_types = {
                            0: "Motion", 1: "Session", 2: "Lap Data", 3: "Event", 
                            4: "Participants", 5: "Car Setups", 6: "Car Telemetry",
                            7: "Car Status", 8: "Final Classification", 9: "Lobby Info",
                            10: "Car Damage", 11: "Session History", 12: "Tyre Sets"
                        }
                        
                        if packet_id in packet_types:
                            packet_name = packet_types[packet_id]
                            print(f"📋 {packet_name} - {packet_size} bytes")
                        elif packet_id != 3:  # Skip spam dari event packets
                            print(f"📋 Unknown packet type {packet_id} - {packet_size} bytes")
                    
                    return False
                    
                except Exception as e:
                    if self.debug_mode:
                        print(f"❌ Parsing error: {e}")
                    return False
            
            else:
                if self.debug_mode:
                    print(f"❌ Packet too small: {packet_size} bytes")
                return False
            
        except Exception as e:
            if self.debug_mode:
                print(f"❌ General error: {e}")
            return False
    
    def receive_data(self):
        """Thread untuk menerima data UDP"""
        print("🎯 Mulai listening untuk data F1 24...")
        
        while self.running:
            try:
                data, addr = self.socket.recvfrom(2048)
                self.parse_car_telemetry_packet(data)
                
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"❌ Error receiving data: {e}")
                break
    
    def display_stream(self):
        """Tampilkan data stream yang terus berjalan ke bawah"""
        print("🏎️ F1 24 TELEMETRY STREAM - Data akan mengalir ke bawah")
        print("📡 Listening on UDP port 20777 | Press Ctrl+C to exit")
        print("=" * 80)
        if self.debug_mode:
            print("🔍 Debug mode: Akan menampilkan semua paket yang diterima")
        print("")
        
        # Tidak perlu logic khusus, semua output sudah ditangani di parse function
        while self.running:
            time.sleep(0.1)
    
    def start(self):
        """Start dashboard"""
        print("🚀 Starting F1 24 Telemetry Dashboard...")
        
        if not self.setup_socket():
            return False
        
        self.running = True
        
        # Start data receiving thread
        self.data_thread = threading.Thread(target=self.receive_data, daemon=True)
        self.data_thread.start()
        
        try:
            # Start display stream (main thread)
            self.display_stream()
        except KeyboardInterrupt:
            print("\n\n🛑 Dashboard dihentikan oleh user")
        finally:
            self.stop()
        
        return True
    
    def stop(self):
        """Stop dashboard"""
        print("\n🔄 Menghentikan dashboard...")
        self.running = False
        
        if self.socket:
            self.socket.close()
        
        if self.data_thread and self.data_thread.is_alive():
            self.data_thread.join(timeout=2)
        
        print("✅ Dashboard telah dihentikan")

def main():
    """Main function"""
    print("🏎️ F1 24 Telemetry Dashboard")
    print("=" * 50)
    print("📋 Pastikan F1 24 sedang berjalan dan UDP telemetry diaktifkan")
    print("⚙️  Settings -> Telemetry Settings -> UDP Telemetry = On")
    print("🔌 UDP Port: 20777")
    print("=" * 50)
    
    dashboard = F1TelemetryDashboard()
    dashboard.start()

if __name__ == "__main__":
    main()
