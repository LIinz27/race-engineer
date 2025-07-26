import socket
import logging
import time

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
UDP_IP = "0.0.0.0"  # Listen on all interfaces
UDP_PORT = 20777    # Default F1 game telemetry port

def main():
    """Simple UDP listener to test if F1 telemetry data is being received."""
    # Create a UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))
    
    # Set socket timeout to 1 second to allow for clean program exit
    sock.settimeout(1)
    
    logger.info(f"UDP listener started on {UDP_IP}:{UDP_PORT}")
    logger.info("Waiting for F1 telemetry data...")
    logger.info("Make sure your F1 game is running with UDP telemetry enabled")
    logger.info("Press Ctrl+C to stop the listener")
    
    packet_count = 0
    start_time = time.time()
    
    try:
        while True:
            try:
                # Wait to receive data
                data, addr = sock.recvfrom(2048)
                
                # If we received data, print info
                packet_count += 1
                if packet_count == 1:
                    logger.info(f"🎮 First telemetry packet received from {addr}!")
                    logger.info(f"Packet size: {len(data)} bytes")
                
                # Show stats every 100 packets
                if packet_count % 100 == 0:
                    elapsed = time.time() - start_time
                    packets_per_second = packet_count / elapsed
                    logger.info(f"Received {packet_count} packets ({packets_per_second:.1f} packets/second)")
                    
            except socket.timeout:
                # No data received in the timeout period
                continue
                
    except KeyboardInterrupt:
        # Handle Ctrl+C
        elapsed = time.time() - start_time
        if packet_count > 0:
            packets_per_second = packet_count / elapsed
            logger.info(f"\nListener stopped. Summary:")
            logger.info(f"Received {packet_count} packets in {elapsed:.1f} seconds")
            logger.info(f"Average rate: {packets_per_second:.1f} packets/second")
        else:
            logger.info("\nListener stopped. No F1 telemetry packets were received.")
            logger.info("Check that:")
            logger.info("1. Your F1 game is running")
            logger.info("2. UDP telemetry is enabled in the game settings")
            logger.info("3. The UDP port is set to 20777")
            logger.info("4. No firewall is blocking the UDP traffic")
    
    finally:
        sock.close()

if __name__ == "__main__":
    main()
