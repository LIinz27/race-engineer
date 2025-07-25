#!/usr/bin/env python3
"""
F1 24 Race Engineer Final - Working Version
Based on exact packet analysis from F1 24
"""

import socket
import struct
import threading
import time
import queue
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
from collections import Counter

# Import existing components  
from race_engineer_ai import RaceEngineerAI
from voice_system import RaceEngineerVoice

@dataclass
class F1PacketInfo:
    """Simplified F1 packet info"""
    packet_format: int      # 2024 for F1 24
    packet_id: int         # 0-13 packet type
    session_uid: int       # Session ID
    session_time: float    # Session time
    raw_size: int          # Total packet size

class F1TelemetryReceiver:
    """
    Simplified F1 24 Telemetry Receiver
    Skip complex header parsing, focus on getting data
    """
    
    def __init__(self, port: int = 20777, bind_ip: str = "127.0.0.1"):
        """Initialize receiver"""
        self.port = port
        self.bind_ip = bind_ip
        
        # Setup logging
        logging.basicConfig(level=logging.INFO,
                          format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)
        
        # Socket dan threading
        self.socket = None
        self.listening_thread = None
        self.packet_queue = queue.Queue()
        self.running = False
        
        # Callbacks
        self.packet_callbacks = {}
        self.raw_packet_callback = None
        
        # Statistics
        self.stats = {
            'total_packets': 0,
            'valid_packets': 0,
            'packet_sizes': Counter(),
            'start_time': None
        }
        
        self.logger.info(f"F1 Telemetry Receiver initialized on {bind_ip}:{port}")
    
    def setup_socket(self) -> bool:
        """Setup UDP socket dengan konfigurasi optimal"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            # Socket options seperti Pits n' Giggles
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self.socket.settimeout(0.1)  # Non-blocking
            
            # Bind socket
            self.socket.bind((self.bind_ip, self.port))
            
            self.logger.info(f"✅ Socket berhasil bind ke {self.bind_ip}:{self.port}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error setup socket: {e}")
            if self.socket:
                self.socket.close()
                self.socket = None
            return False
    
    def register_callback(self, callback_name: str, callback: Callable):
        """Register callback"""
        self.packet_callbacks[callback_name] = callback
        self.logger.debug(f"Registered callback: {callback_name}")
    
    def register_raw_callback(self, callback: Callable):
        """Register raw packet callback"""
        self.raw_packet_callback = callback
        self.logger.debug("Registered raw packet callback")
    
    def extract_basic_info(self, raw_packet: bytes) -> Optional[F1PacketInfo]:
        """Extract basic info from packet without complex parsing"""
        try:
            if len(raw_packet) < 8:
                return None
            
            # From analysis: bytes 0-1 = 2024 (format), byte 6 = packet_id
            packet_format = struct.unpack('<H', raw_packet[0:2])[0]
            
            # Check if this looks like F1 24 packet
            if packet_format != 2024:
                return None
            
            # Extract what we can safely
            try:
                # From analysis pattern, packet ID is around byte 6
                if len(raw_packet) > 6:
                    packet_id = raw_packet[6] if raw_packet[6] <= 13 else 0
                else:
                    packet_id = 0
                    
                # Try to extract session info if packet is big enough
                session_uid = 0
                session_time = 0.0
                
                if len(raw_packet) > 20:
                    try:
                        # Try different positions for session data
                        session_time = struct.unpack('<f', raw_packet[16:20])[0]
                    except:
                        session_time = 0.0
                        
                return F1PacketInfo(
                    packet_format=packet_format,
                    packet_id=packet_id,
                    session_uid=session_uid,
                    session_time=session_time,
                    raw_size=len(raw_packet)
                )
                
            except Exception as e:
                # If extraction fails, return basic info
                return F1PacketInfo(
                    packet_format=packet_format,
                    packet_id=0,
                    session_uid=0,
                    session_time=0.0,
                    raw_size=len(raw_packet)
                )
                
        except Exception as e:
            self.logger.debug(f"Failed to extract basic info: {e}")
            return None
    
    def _listening_loop(self):
        """Main listening loop"""
        self.logger.info("🎯 Started telemetry listening loop")
        
        while self.running:
            try:
                # Receive packet
                raw_packet, addr = self.socket.recvfrom(4096)
                
                # Add to queue for processing
                self.packet_queue.put(raw_packet)
                
            except socket.timeout:
                continue  # Normal timeout
            except Exception as e:
                if self.running:
                    self.logger.error(f"Error in listening loop: {e}")
                break
        
        self.logger.info("Telemetry listening loop stopped")
    
    def _processing_loop(self):
        """Packet processing loop"""
        while self.running:
            try:
                # Get packet with timeout
                raw_packet = self.packet_queue.get(timeout=0.1)
                
                # Process packet
                self._process_packet(raw_packet)
                
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"Error processing packet: {e}")
    
    def _process_packet(self, raw_packet: bytes):
        """Process individual packet"""
        try:
            self.stats['total_packets'] += 1
            
            # Call raw packet callback first
            if self.raw_packet_callback:
                self.raw_packet_callback(raw_packet)
            
            # Extract basic info
            packet_info = self.extract_basic_info(raw_packet)
            if packet_info:
                self.stats['valid_packets'] += 1
                self.stats['packet_sizes'][packet_info.raw_size] += 1
                
                # Call registered callbacks
                for callback_name, callback in self.packet_callbacks.items():
                    try:
                        callback(packet_info, raw_packet)
                    except Exception as e:
                        self.logger.error(f"Error in callback {callback_name}: {e}")
            
        except Exception as e:
            self.logger.error(f"Error processing packet: {e}")
    
    def start_listening(self):
        """Start telemetry listening"""
        if not self.setup_socket():
            raise RuntimeError("Failed to setup socket")
        
        self.running = True
        self.stats['start_time'] = datetime.now()
        
        # Start listening thread
        self.listening_thread = threading.Thread(target=self._listening_loop, daemon=True)
        self.listening_thread.start()
        
        self.logger.info("🚀 Telemetry receiver started")
        
        # Run processing loop in main thread
        try:
            self._processing_loop()
        except KeyboardInterrupt:
            self.logger.info("🛑 Telemetry receiver interrupted by user")
        finally:
            self.stop_listening()
    
    def stop_listening(self):
        """Stop telemetry listening"""
        self.running = False
        
        # Wait for listening thread
        if self.listening_thread and self.listening_thread.is_alive():
            self.listening_thread.join(timeout=1.0)
        
        # Close socket
        if self.socket:
            self.socket.close()
            self.socket = None
        
        self._print_statistics()
        self.logger.info("Telemetry receiver stopped")
    
    def _print_statistics(self):
        """Print final statistics"""
        if not self.stats['start_time']:
            return
            
        duration = (datetime.now() - self.stats['start_time']).total_seconds()
        total = self.stats['total_packets']
        valid = self.stats['valid_packets']
        
        print(f"\n📊 F1 24 TELEMETRY STATISTICS")
        print(f"⏱️  Duration: {duration:.1f} seconds")
        print(f"📦 Total packets: {total}")
        print(f"✅ Valid F1 packets: {valid} ({valid/total*100:.1f}%)" if total > 0 else "✅ Valid packets: 0")
        print(f"📈 Rate: {total/duration:.1f} packets/second" if duration > 0 else "📈 Rate: 0 packets/second")
        
        # Packet size breakdown
        if self.stats['packet_sizes']:
            print(f"\n📋 Packet Sizes Received:")
            for size, count in self.stats['packet_sizes'].most_common(10):
                percentage = (count / valid * 100) if valid > 0 else 0
                print(f"   {size:4d} bytes: {count:6d} packets ({percentage:5.1f}%)")


class RaceEngineerF124:
    """
    F1 24 Race Engineer - Final Working Version
    """
    
    def __init__(self, port: int = 20777):
        """Initialize Race Engineer"""
        print("🏎️  F1 24 RACE ENGINEER - FINAL VERSION")
        print("=" * 60)
        
        # Initialize components
        self.telemetry_receiver = F1TelemetryReceiver(port)
        self.ai_engineer = RaceEngineerAI()
        self.voice_system = RaceEngineerVoice()
        
        # Session tracking
        self.session_active = False
        self.session_start_time = None
        self.packet_count = 0
        self.last_voice_alert = 0
        
        # Statistics
        self.race_stats = {
            'session_packets': 0,
            'voice_alerts': 0,
            'large_packets': 0,  # Packets > 1000 bytes (likely race data)
            'small_packets': 0   # Packets < 100 bytes (likely events)
        }
        
        self._register_callbacks()
        
        print("✅ All systems initialized")
        print(f"🎙️  Voice system: {'Available' if self.voice_system.voice_available else 'Not Available'}")
        print()
    
    def _register_callbacks(self):
        """Register telemetry callbacks"""
        
        def handle_raw_packet(raw_packet: bytes):
            """Handle all raw packets for session detection"""
            if not self.session_active:
                self.session_active = True
                self.session_start_time = datetime.now()
                self._announce_session_start()
            
            self.packet_count += 1
            self.race_stats['session_packets'] += 1
            
            # Categorize packets by size
            size = len(raw_packet)
            if size > 1000:
                self.race_stats['large_packets'] += 1
            elif size < 100:
                self.race_stats['small_packets'] += 1
            
            # Periodic voice updates
            current_time = time.time()
            if current_time - self.last_voice_alert > 30:  # Every 30 seconds
                self._send_periodic_update()
                self.last_voice_alert = current_time
        
        def handle_processed_packet(packet_info: F1PacketInfo, raw_packet: bytes):
            """Handle processed F1 packets"""
            # Log interesting packets
            if packet_info.raw_size > 1000:
                packet_types = {
                    1: "Session", 2: "Lap Data", 4: "Participants", 
                    6: "Car Telemetry", 7: "Car Status"
                }
                packet_name = packet_types.get(packet_info.packet_id, f"Type-{packet_info.packet_id}")
                
                if packet_info.packet_id in [1, 2, 6, 7]:  # Important packet types
                    print(f"📡 {packet_name} packet: {packet_info.raw_size} bytes")
        
        # Register callbacks
        self.telemetry_receiver.register_raw_callback(handle_raw_packet)
        self.telemetry_receiver.register_callback("processed", handle_processed_packet)
    
    def _announce_session_start(self):
        """Announce session start"""
        print("🏁 F1 24 SESSION DETECTED!")
        print(f"⏰ Session started at: {self.session_start_time.strftime('%H:%M:%S')}")
        
        if self.voice_system.voice_available:
            self.voice_system.speak_immediate("F1 session detected. Race Engineer monitoring active.")
    
    def _send_periodic_update(self):
        """Send periodic voice update"""
        if not self.session_active:
            return
            
        duration = (datetime.now() - self.session_start_time).total_seconds()
        
        # Create status message
        messages = [
            f"Race Engineer active for {int(duration)} seconds.",
            f"Received {self.race_stats['session_packets']} telemetry packets.",
        ]
        
        if self.race_stats['large_packets'] > 0:
            messages.append(f"Processing {self.race_stats['large_packets']} data packets.")
        
        message = " ".join(messages)
        
        if self.voice_system.voice_available:
            self.voice_system.speak_immediate(message)
        
        self.race_stats['voice_alerts'] += 1
        print(f"🔊 Voice Update: {message}")
    
    def run(self):
        """Run the Race Engineer"""
        print("🚀 STARTING F1 24 RACE ENGINEER")
        print(f"🔌 Listening on port {self.telemetry_receiver.port}")
        print("🎯 Start F1 24 and begin a session!")
        print("-" * 60)
        
        if self.voice_system.voice_available:
            self.voice_system.speak_immediate("F1 Race Engineer ready. Waiting for telemetry data.")
        
        try:
            # Start telemetry listening (blocks until stopped)
            self.telemetry_receiver.start_listening()
            
        except Exception as e:
            print(f"❌ Error in Race Engineer: {e}")
        finally:
            self._print_final_stats()
    
    def _print_final_stats(self):
        """Print final race statistics"""
        if self.session_start_time:
            duration = (datetime.now() - self.session_start_time).total_seconds()
            print(f"\n🏁 RACE ENGINEER SESSION SUMMARY")
            print(f"⏱️  Total duration: {duration:.1f}s")
            print(f"📦 Session packets: {self.race_stats['session_packets']}")
            print(f"📊 Large packets (race data): {self.race_stats['large_packets']}")
            print(f"📋 Small packets (events): {self.race_stats['small_packets']}")
            print(f"🔊 Voice alerts: {self.race_stats['voice_alerts']}")


# Main application
def main():
    """Main application entry point"""
    try:
        race_engineer = RaceEngineerF124()
        race_engineer.run()
    except KeyboardInterrupt:
        print("\n🛑 Race Engineer stopped by user")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
