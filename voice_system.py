#!/usr/bin/env python3
"""
F1 24 Race Engineer Voice System
Text-to-Speech system untuk race engineer alerts
"""

import pyttsx3
import threading
import queue
import time
from typing import List, Optional
from dataclasses import dataclass
from enum import Enum

from race_engineer_ai import RaceAlert, AlertPriority

@dataclass
class VoiceMessage:
    """Voice message dengan priority queue"""
    text: str
    priority: AlertPriority
    timestamp: float
    interrupt: bool = False  # Apakah message ini bisa interrupt message lain

class RaceEngineerVoice:
    """Voice system untuk Race Engineer"""
    
    def __init__(self):
        # Initialize TTS engine
        try:
            self.engine = pyttsx3.init()
            self.setup_voice_properties()
            self.voice_available = True
            print("✅ Voice engine initialized successfully")
        except Exception as e:
            print(f"❌ Voice engine initialization failed: {e}")
            self.voice_available = False
            return
        
        # Voice queue dan threading
        self.voice_queue = queue.PriorityQueue()
        self.is_speaking = False
        self.voice_thread = None
        self.stop_voice = False
        
        # Voice settings
        self.settings = {
            'enabled': True,
            'min_interval': 3.0,  # Minimum seconds between voice messages
            'interrupt_on_critical': True,
            'priority_filter': AlertPriority.MEDIUM  # Only speak MEDIUM and above
        }
        
        # Message history untuk avoid repetition
        self.recent_messages = []
        self.last_voice_time = 0
        
        # Start voice thread
        self.start_voice_thread()
    
    def setup_voice_properties(self):
        """Setup voice properties"""
        # Set speech rate (slower for clarity during racing)
        self.engine.setProperty('rate', 150)  # Default around 200
        
        # Set volume
        self.engine.setProperty('volume', 0.9)
        
        # Try to use a male voice (race engineer typically male)
        voices = self.engine.getProperty('voices')
        if voices:
            # Look for male voice or use first available
            for voice in voices:
                if 'male' in voice.name.lower() or 'david' in voice.name.lower():
                    self.engine.setProperty('voice', voice.id)
                    break
            else:
                # Use first voice if no male voice found
                self.engine.setProperty('voice', voices[0].id)
        
        print(f"🗣️  Voice configured: Rate=150, Volume=0.9")
    
    def start_voice_thread(self):
        """Start background thread untuk voice processing"""
        if not self.voice_available:
            return
            
        self.voice_thread = threading.Thread(target=self.voice_worker, daemon=True)
        self.voice_thread.start()
        print("🎙️  Voice thread started")
    
    def voice_worker(self):
        """Background worker untuk process voice queue"""
        while not self.stop_voice:
            try:
                # Get message dari queue dengan timeout
                priority, timestamp, message = self.voice_queue.get(timeout=1.0)
                
                # Check jika masih relevant (tidak terlalu lama)
                if time.time() - timestamp > 30:  # Skip messages older than 30s
                    continue
                
                # Check minimum interval
                current_time = time.time()
                if current_time - self.last_voice_time < self.settings['min_interval']:
                    continue
                    
                # Speak the message
                self.speak_message(message)
                self.last_voice_time = current_time
                
                # Mark task as done
                self.voice_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"❌ Voice worker error: {e}")
                continue
    
    def speak_message(self, text: str):
        """Speak a message using TTS"""
        if not self.voice_available or not self.settings['enabled']:
            return
        
        try:
            self.is_speaking = True
            print(f"🗣️  Speaking: {text}")
            
            self.engine.say(text)
            self.engine.runAndWait()
            
        except Exception as e:
            print(f"❌ TTS error: {e}")
        finally:
            self.is_speaking = False
    
    def add_voice_message(self, alert: RaceAlert):
        """Add alert ke voice queue"""
        if not self.voice_available or not self.settings['enabled']:
            return
        
        # Filter berdasarkan priority
        if alert.priority.value < self.settings['priority_filter'].value:
            return
        
        # Check untuk avoid repetition
        if self.is_message_recent(alert.message):
            return
        
        # Format message untuk voice
        voice_text = self.format_for_voice(alert)
        
        # Add ke queue dengan priority (lower number = higher priority)
        priority_value = 5 - alert.priority.value  # Invert priority for queue
        
        try:
            self.voice_queue.put((priority_value, alert.timestamp, voice_text))
            self.recent_messages.append({
                'text': alert.message,
                'timestamp': alert.timestamp
            })
            
            # Keep only recent messages (last 2 minutes)
            cutoff_time = time.time() - 120
            self.recent_messages = [msg for msg in self.recent_messages 
                                  if msg['timestamp'] > cutoff_time]
            
        except Exception as e:
            print(f"❌ Error adding voice message: {e}")
    
    def format_for_voice(self, alert: RaceAlert) -> str:
        """Format alert message untuk TTS"""
        message = alert.message
        
        # Replace technical abbreviations
        replacements = {
            '°C': ' degrees',
            'km/h': ' kilometers per hour',
            'DRS': 'D R S',
            'ERS': 'E R S',
            'FL': 'front left',
            'FR': 'front right', 
            'RL': 'rear left',
            'RR': 'rear right'
        }
        
        for old, new in replacements.items():
            message = message.replace(old, new)
        
        # Add appropriate prefix based on priority and category
        if alert.priority == AlertPriority.CRITICAL:
            if alert.category == 'tyre':
                message = f"Critical tyre alert! {message}"
            elif alert.category == 'fuel':
                message = f"Fuel critical! {message}"
            else:
                message = f"Critical alert! {message}"
        elif alert.priority == AlertPriority.HIGH:
            if alert.category == 'tyre':
                message = f"Tyre warning: {message}"
            elif alert.category == 'fuel':
                message = f"Fuel warning: {message}"
            else:
                message = f"Warning: {message}"
        elif alert.category == 'strategy':
            message = f"Strategy update: {message}"
        
        return message
    
    def is_message_recent(self, message: str) -> bool:
        """Check jika message sudah diucapkan recently"""
        current_time = time.time()
        
        for recent_msg in self.recent_messages:
            # Check similarity (simple approach)
            if (current_time - recent_msg['timestamp'] < 60 and  # Within 1 minute
                message.lower() in recent_msg['text'].lower()):
                return True
        
        return False
    
    def speak_immediate(self, text: str):
        """Speak message immediately (bypass queue)"""
        if not self.voice_available:
            print(f"📢 [VOICE DISABLED] {text}")
            return
        
        # Stop current speech if critical
        if self.is_speaking:
            try:
                self.engine.stop()
            except:
                pass
        
        self.speak_message(text)
    
    def announce_session_start(self):
        """Announce race engineer session start"""
        messages = [
            "Race engineer online.",
            "Monitoring telemetry data.",
            "Good luck out there!"
        ]
        
        for msg in messages:
            self.speak_immediate(msg)
            time.sleep(1.5)
    
    def announce_session_end(self):
        """Announce session end"""
        self.speak_immediate("Race engineer session completed. Well done!")
    
    def set_voice_enabled(self, enabled: bool):
        """Enable/disable voice output"""
        self.settings['enabled'] = enabled
        status = "enabled" if enabled else "disabled"
        print(f"🗣️  Voice output {status}")
    
    def set_priority_filter(self, priority: AlertPriority):
        """Set minimum priority untuk voice alerts"""
        self.settings['priority_filter'] = priority
        print(f"🗣️  Voice priority filter set to {priority.name}")
    
    def get_voice_status(self) -> dict:
        """Get current voice system status"""
        return {
            'available': self.voice_available,
            'enabled': self.settings['enabled'],
            'speaking': self.is_speaking,
            'queue_size': self.voice_queue.qsize() if self.voice_available else 0,
            'last_voice_time': self.last_voice_time,
            'priority_filter': self.settings['priority_filter'].name
        }
    
    def shutdown(self):
        """Shutdown voice system"""
        self.stop_voice = True
        if self.voice_thread and self.voice_thread.is_alive():
            self.voice_thread.join(timeout=2.0)
        print("🗣️  Voice system shutdown")

def demo_voice_system():
    """Demo voice system dengan sample alerts"""
    print("🏎️  F1 24 RACE ENGINEER VOICE SYSTEM - DEMO")
    print("=" * 60)
    
    voice = RaceEngineerVoice()
    
    if not voice.voice_available:
        print("❌ Voice system not available - demo aborted")
        return
    
    print("🎙️  Testing voice system with sample alerts...")
    print("   (You should hear the race engineer speaking)")
    print()
    
    # Announce session start
    voice.announce_session_start()
    time.sleep(3)
    
    # Sample alerts untuk demo
    sample_alerts = [
        RaceAlert(
            message="Rear right tyre overheating at 115°C! Lift and coast!",
            priority=AlertPriority.CRITICAL,
            timestamp=time.time(),
            category='tyre'
        ),
        RaceAlert(
            message="LOW FUEL: 2.5 laps remaining",
            priority=AlertPriority.HIGH,
            timestamp=time.time() + 1,
            category='fuel'
        ),
        RaceAlert(
            message="DRS available for next straight",
            priority=AlertPriority.LOW,
            timestamp=time.time() + 2,
            category='performance'
        ),
        RaceAlert(
            message="Pit window open: Consider pit stop for fresh tyres",
            priority=AlertPriority.MEDIUM,
            timestamp=time.time() + 3,
            category='strategy'
        )
    ]
    
    print("🔥 Processing sample alerts:")
    for i, alert in enumerate(sample_alerts):
        print(f"   {i+1}. [{alert.priority.name}] {alert.message}")
        voice.add_voice_message(alert)
        time.sleep(2)  # Space out alerts
    
    # Wait untuk queue processing
    print("\n⏳ Waiting for voice queue to process...")
    time.sleep(10)
    
    # Show voice status
    status = voice.get_voice_status()
    print(f"\n📊 Voice system status:")
    print(f"   Available: {status['available']}")
    print(f"   Enabled: {status['enabled']}")
    print(f"   Queue size: {status['queue_size']}")
    print(f"   Priority filter: {status['priority_filter']}")
    
    # Announce end
    voice.announce_session_end()
    time.sleep(2)
    
    # Shutdown
    voice.shutdown()
    print("\n✅ Voice system demo completed!")

if __name__ == "__main__":
    demo_voice_system()
