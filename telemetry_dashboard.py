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
        self.debug_mode = True  # Set to True for detailed packet analysis
        
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
    
    def extract_basic_packet_info(self, raw_packet: bytes):
        """Extract basic packet info tanpa complex parsing (dari race_engineer_f1_24_final.py)"""
        try:
            if len(raw_packet) < 8:
                return None
            
            # Extract packet format (should be 2024 for F1 24)
            packet_format = struct.unpack('<H', raw_packet[0:2])[0]
            
            # Check if this looks like F1 24 packet
            if packet_format != 2024:
                return None
            
            # Extract packet ID safely
            packet_id = 0
            if len(raw_packet) > 5:
                packet_id = raw_packet[5] if raw_packet[5] <= 13 else 0
                
            # Extract session time if possible
            session_time = 0.0
            if len(raw_packet) > 20:
                try:
                    session_time = struct.unpack('<f', raw_packet[16:20])[0]
                except:
                    session_time = 0.0
                    
            return {
                'packet_format': packet_format,
                'packet_id': packet_id,
                'session_time': session_time,
                'raw_size': len(raw_packet),
                'is_valid_f1': True
            }
                
        except Exception as e:
            if self.debug_mode:
                print(f"Failed to extract packet info: {e}")
            return None
    def parse_car_telemetry_packet(self, data):
        """Parse paket F1 24 dengan pendekatan yang lebih robust"""
        try:
            packet_size = len(data)
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            
            # Selalu update counter
            with self.data_lock:
                self.current_data['packets_received'] += 1
                self.current_data['timestamp'] = datetime.now()
            
            # Extract basic packet info dengan method yang lebih robust
            packet_info = self.extract_basic_packet_info(data)
            
            if not packet_info:
                if self.debug_mode and packet_size > 10:
                    print(f"❌ Invalid F1 packet: {packet_size} bytes")
                return False
            
            packet_id = packet_info['packet_id']
            
            if self.debug_mode:
                hex_preview = data[:24].hex()
                print(f"Received {packet_size:4d} bytes at {timestamp}")
                print(f"📦 Packet ID: {packet_id:2d} | Size: {packet_size:4d} | Preview: {hex_preview}")
                
                # Show packet type
                packet_types = {
                    0: "Motion", 1: "Session", 2: "Lap Data", 3: "Event", 
                    4: "Participants", 5: "Car Setups", 6: "Car Telemetry",
                    7: "Car Status", 8: "Final Classification", 9: "Lobby Info",
                    10: "Car Damage", 11: "Session History", 12: "Tyre Sets"
                }
                
                packet_name = packet_types.get(packet_id, f"Unknown-{packet_id}")
                print(f"📋 {packet_name} (ID:{packet_id}) - {packet_size} bytes")
            
            # Fokus pada Car Telemetry (packet ID 6) 
            if packet_id == 6 and packet_size > 1000:
                return self._parse_car_telemetry_data(data, packet_info)
            
            return False
                    
        except Exception as e:
            if self.debug_mode:
                print(f"❌ General parsing error: {e}")
            return False
    
    def _parse_car_telemetry_data(self, data, packet_info):
        """Parse actual car telemetry data dari packet ID 6"""
        try:
            # F1 24 header biasanya 24 bytes
            header_size = 24
            
            if len(data) < header_size + 60:  # Tidak cukup data
                return False
                
            base_offset = header_size
            
            # Parse car telemetry data untuk mobil pertama (player)
            # Format F1 24: speed(4), throttle(4), steer(4), brake(4), clutch(1), gear(1), engineRPM(2)
            speed = struct.unpack('<f', data[base_offset:base_offset+4])[0]
            throttle = struct.unpack('<f', data[base_offset+4:base_offset+8])[0]
            steer = struct.unpack('<f', data[base_offset+8:base_offset+12])[0]
            brake = struct.unpack('<f', data[base_offset+12:base_offset+16])[0]
            clutch = data[base_offset+16]
            gear = struct.unpack('<b', data[base_offset+17:base_offset+18])[0]  # signed byte
            engine_rpm = struct.unpack('<H', data[base_offset+18:base_offset+20])[0]
            
            # Validasi data dengan range yang masuk akal
            if (0 <= speed <= 400 and 
                0 <= throttle <= 1.1 and 
                0 <= brake <= 1.1 and
                0 <= engine_rpm <= 20000 and
                -2 <= gear <= 8):
                
                speed_kmh = int(speed)
                gear_display = str(gear) if gear > 0 else ('R' if gear == -1 else 'N')
                
                # Update data
                with self.data_lock:
                    self.current_data.update({
                        'speed': speed_kmh,
                        'gear': gear_display,
                        'throttle': throttle,
                        'brake': brake,
                        'rpm': engine_rpm,
                        'steer': steer,
                        'clutch': clutch,
                        'valid_data': True,
                        'last_update': datetime.now()
                    })
                
                if self.debug_mode:
                    print(f"🏎️ Car Telemetry: Speed={speed_kmh} km/h, Gear={gear_display}, Throttle={throttle*100:.1f}%, RPM={engine_rpm}")
                
                return True
                
        except struct.error as e:
            if self.debug_mode:
                print(f"❌ Telemetry parsing error: {e}")
        except Exception as e:
            if self.debug_mode:
                print(f"❌ Car telemetry error: {e}")
        
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
        """Tampilkan data stream yang update setiap detik"""
        print("🏎️ F1 24 TELEMETRY STREAM - Update setiap detik")
        print("📡 Listening on UDP port 20777 | Press Ctrl+C to exit")
        print("=" * 80)
        if self.debug_mode:
            print("🔍 Debug mode: Akan menampilkan semua paket yang diterima")
        print("")
        
        last_display_time = time.time()
        
        while self.running:
            current_time = time.time()
            
            # Update display setiap 1 detik
            if current_time - last_display_time >= 1.0:
                with self.data_lock:
                    data_copy = self.current_data.copy()
                
                # Format timestamp
                timestamp = datetime.now().strftime("%H:%M:%S")
                
                # Status koneksi
                if data_copy.get('valid_data', False):
                    # Hitung berapa lama sejak update terakhir
                    last_update = data_copy.get('last_update')
                    if last_update:
                        time_diff = (datetime.now() - last_update).total_seconds()
                        status = "🟢 LIVE" if time_diff < 2 else f"🟡 {time_diff:.1f}s ago"
                    else:
                        status = "🟢 LIVE"
                else:
                    status = "🔴 NO DATA"
                
                # Tampilkan data dengan format yang konsisten
                speed = data_copy.get('speed', 0)
                gear = data_copy.get('gear', 'N')
                throttle = data_copy.get('throttle', 0.0) * 100
                brake = data_copy.get('brake', 0.0) * 100
                rpm = data_copy.get('rpm', 0)
                packets = data_copy.get('packets_received', 0)
                
                print(f"[{timestamp}] {status} | Speed: {speed:3d} km/h | Gear: {gear:>2} | Throttle: {throttle:5.1f}% | Brake: {brake:5.1f}% | RPM: {rpm:5d} | Packets: {packets}")
                
                last_display_time = current_time
            
            time.sleep(0.1)  # Check setiap 100ms tapi display setiap 1 detik
    
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
