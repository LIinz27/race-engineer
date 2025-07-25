#!/usr/bin/env python3
"""
F1 24 Race Engineer AI
AI system untuk memberikan advice dan informasi race
"""

import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

class AlertPriority(Enum):
    """Priority level untuk alerts"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class RaceAlert:
    """Alert message dengan priority"""
    message: str
    priority: AlertPriority
    timestamp: float
    category: str  # 'tyre', 'fuel', 'strategy', 'damage', 'performance'

class RaceEngineerAI:
    """AI Race Engineer untuk F1 24"""
    
    def __init__(self):
        self.alerts_history: List[RaceAlert] = []
        self.last_advice_time = 0
        self.advice_interval = 5.0  # Minimum seconds between advice
        
        # Thresholds untuk warnings
        self.thresholds = {
            'tyre_temp_warning': 100,
            'tyre_temp_critical': 110,
            'fuel_warning_laps': 3,
            'fuel_critical_laps': 1.5,
            'tyre_wear_warning': 25,
            'brake_temp_warning': 700,
            'engine_temp_warning': 110
        }
        
        # Tyre compound mapping
        self.tyre_compounds = {
            16: "C5 (Soft)",
            17: "C4 (Medium)", 
            18: "C3 (Hard)",
            7: "Intermediate",
            8: "Wet"
        }
        
    def analyze_telemetry_data(self, race_data: Dict[str, Any]) -> List[RaceAlert]:
        """Analisis telemetry data dan generate alerts"""
        alerts = []
        current_time = time.time()
        
        # Skip jika belum waktunya memberikan advice
        if current_time - self.last_advice_time < self.advice_interval:
            return alerts
        
        if not race_data.get('telemetry'):
            return alerts
        
        t = race_data['telemetry']
        
        # === ANALISIS SUHU BAN ===
        tyre_temps = t['tyre_temps']
        tyre_positions = ['front_left', 'front_right', 'rear_left', 'rear_right']
        tyre_names = ['Front Left', 'Front Right', 'Rear Left', 'Rear Right']
        
        for pos, name in zip(tyre_positions, tyre_names):
            temp = tyre_temps[pos]
            
            if temp > self.thresholds['tyre_temp_critical']:
                alerts.append(RaceAlert(
                    message=f"CRITICAL: {name} tyre overheating at {temp}°C! Lift and coast!",
                    priority=AlertPriority.CRITICAL,
                    timestamp=current_time,
                    category='tyre'
                ))
            elif temp > self.thresholds['tyre_temp_warning']:
                alerts.append(RaceAlert(
                    message=f"WARNING: {name} tyre getting hot at {temp}°C",
                    priority=AlertPriority.HIGH,
                    timestamp=current_time,
                    category='tyre'
                ))
        
        # === ANALISIS BRAKE TEMP ===
        brake_temps = t['brake_temps']
        for pos, name in zip(tyre_positions, tyre_names):
            brake_temp = brake_temps[pos]
            
            if brake_temp > self.thresholds['brake_temp_warning']:
                alerts.append(RaceAlert(
                    message=f"High brake temperature on {name}: {brake_temp}°C",
                    priority=AlertPriority.MEDIUM,
                    timestamp=current_time,
                    category='brakes'
                ))
        
        # === ANALISIS ENGINE TEMP ===
        if t['engine_temp'] > self.thresholds['engine_temp_warning']:
            alerts.append(RaceAlert(
                message=f"Engine temperature high: {t['engine_temp']}°C",
                priority=AlertPriority.HIGH,
                timestamp=current_time,
                category='engine'
            ))
        
        return alerts
    
    def analyze_car_status(self, race_data: Dict[str, Any]) -> List[RaceAlert]:
        """Analisis car status dan generate fuel/strategy alerts"""
        alerts = []
        current_time = time.time()
        
        if not race_data.get('car_status'):
            return alerts
        
        s = race_data['car_status']
        
        # === ANALISIS FUEL ===
        fuel_laps = s['fuel_remaining_laps']
        
        if fuel_laps < self.thresholds['fuel_critical_laps']:
            alerts.append(RaceAlert(
                message=f"CRITICAL: Only {fuel_laps:.1f} laps of fuel remaining!",
                priority=AlertPriority.CRITICAL,
                timestamp=current_time,
                category='fuel'
            ))
        elif fuel_laps < self.thresholds['fuel_warning_laps']:
            alerts.append(RaceAlert(
                message=f"LOW FUEL: {fuel_laps:.1f} laps remaining",
                priority=AlertPriority.HIGH,
                timestamp=current_time,
                category='fuel'
            ))
        
        # === ANALISIS TYRE AGE ===
        tyre_age = s['tyre_age']
        tyre_compound = self.tyre_compounds.get(s['tyre_compound'], f"Unknown ({s['tyre_compound']})")
        
        if tyre_age > 30:
            alerts.append(RaceAlert(
                message=f"High tyre wear: {tyre_compound} tyres are {tyre_age} laps old",
                priority=AlertPriority.MEDIUM,
                timestamp=current_time,
                category='strategy'
            ))
        elif tyre_age > 20:
            alerts.append(RaceAlert(
                message=f"Tyre degradation: {tyre_compound} tyres at {tyre_age} laps",
                priority=AlertPriority.LOW,
                timestamp=current_time,
                category='strategy'
            ))
        
        # === DRS AVAILABILITY ===
        if s['drs_allowed'] and race_data.get('telemetry', {}).get('drs_active') == False:
            alerts.append(RaceAlert(
                message="DRS available for next straight",
                priority=AlertPriority.LOW,
                timestamp=current_time,
                category='performance'
            ))
        
        return alerts
    
    def analyze_lap_performance(self, race_data: Dict[str, Any]) -> List[RaceAlert]:
        """Analisis performa lap dan posisi"""
        alerts = []
        current_time = time.time()
        
        if not race_data.get('lap_info'):
            return alerts
        
        lap_info = race_data['lap_info']
        
        # === LAP TIME ANALYSIS ===
        if lap_info['last_lap_time'] > 0 and lap_info['best_lap_time'] > 0:
            time_diff = lap_info['last_lap_time'] - lap_info['best_lap_time']
            
            if time_diff > 2.0:  # More than 2 seconds slower
                alerts.append(RaceAlert(
                    message=f"Last lap {time_diff:.1f}s slower than personal best",
                    priority=AlertPriority.MEDIUM,
                    timestamp=current_time,
                    category='performance'
                ))
        
        # === PIT STATUS ===
        pit_status_names = {
            0: "None",
            1: "Pitting",
            2: "In Pit Area",
            3: "In Pit Lane"
        }
        
        if lap_info['pit_status'] > 0:
            status_name = pit_status_names.get(lap_info['pit_status'], "Unknown")
            alerts.append(RaceAlert(
                message=f"Pit status: {status_name}",
                priority=AlertPriority.MEDIUM,
                timestamp=current_time,
                category='strategy'
            ))
        
        return alerts
    
    def generate_strategic_advice(self, race_data: Dict[str, Any]) -> List[RaceAlert]:
        """Generate strategic advice berdasarkan situasi race"""
        alerts = []
        current_time = time.time()
        
        # Hanya berikan advice strategis setiap 15 detik
        if current_time - self.last_advice_time < 15.0:
            return alerts
        
        # === PIT WINDOW ANALYSIS ===
        if race_data.get('car_status') and race_data.get('lap_info'):
            tyre_age = race_data['car_status']['tyre_age']
            fuel_laps = race_data['car_status']['fuel_remaining_laps']
            current_lap = race_data['lap_info']['current_lap']
            
            # Pit window recommendation
            if tyre_age > 25 and fuel_laps > 10:
                alerts.append(RaceAlert(
                    message=f"Pit window open: Tyres degrading, fuel sufficient for {fuel_laps:.1f} laps",
                    priority=AlertPriority.MEDIUM,
                    timestamp=current_time,
                    category='strategy'
                ))
            
            # Fuel strategy
            if fuel_laps < 8 and tyre_age < 15:
                alerts.append(RaceAlert(
                    message="Consider fuel saving: Lift and coast on straights",
                    priority=AlertPriority.HIGH,
                    timestamp=current_time,
                    category='strategy'
                ))
        
        return alerts
    
    def process_race_data(self, race_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process race data dan generate comprehensive analysis"""
        current_time = time.time()
        
        # Generate all alerts
        new_alerts = []
        new_alerts.extend(self.analyze_telemetry_data(race_data))
        new_alerts.extend(self.analyze_car_status(race_data))
        new_alerts.extend(self.analyze_lap_performance(race_data))
        new_alerts.extend(self.generate_strategic_advice(race_data))
        
        # Add new alerts to history
        self.alerts_history.extend(new_alerts)
        
        # Keep only recent alerts (last 5 minutes)
        cutoff_time = current_time - 300
        self.alerts_history = [alert for alert in self.alerts_history 
                              if alert.timestamp > cutoff_time]
        
        # Update last advice time if we generated alerts
        if new_alerts:
            self.last_advice_time = current_time
        
        # Create summary
        summary = {
            'timestamp': current_time,
            'new_alerts': new_alerts,
            'recent_alerts': self.alerts_history[-10:],  # Last 10 alerts
            'alert_counts': self.get_alert_counts(),
            'priority_alerts': self.get_priority_alerts(),
            'recommendations': self.get_current_recommendations(race_data)
        }
        
        return summary
    
    def get_alert_counts(self) -> Dict[str, int]:
        """Get count of alerts by category"""
        counts = {}
        for alert in self.alerts_history:
            if alert.category not in counts:
                counts[alert.category] = 0
            counts[alert.category] += 1
        return counts
    
    def get_priority_alerts(self) -> List[RaceAlert]:
        """Get only high and critical priority alerts"""
        return [alert for alert in self.alerts_history 
                if alert.priority in [AlertPriority.HIGH, AlertPriority.CRITICAL]]
    
    def get_current_recommendations(self, race_data: Dict[str, Any]) -> List[str]:
        """Get current driving recommendations"""
        recommendations = []
        
        # Based on recent critical alerts
        critical_alerts = [alert for alert in self.alerts_history 
                          if alert.priority == AlertPriority.CRITICAL 
                          and time.time() - alert.timestamp < 30]
        
        if any('overheating' in alert.message.lower() for alert in critical_alerts):
            recommendations.append("Reduce pace to cool tyres")
            recommendations.append("Avoid aggressive cornering")
        
        if any('fuel' in alert.message.lower() for alert in critical_alerts):
            recommendations.append("Implement fuel saving mode")
            recommendations.append("Lift and coast before braking zones")
        
        # General recommendations based on current data
        if race_data.get('car_status', {}).get('drs_allowed'):
            recommendations.append("DRS available - use on straights")
        
        return recommendations
    
    def format_alert_for_voice(self, alert: RaceAlert) -> str:
        """Format alert message untuk text-to-speech"""
        # Simplify technical terms for voice
        message = alert.message
        message = message.replace("°C", " degrees celsius")
        message = message.replace("km/h", " kilometers per hour")
        message = message.replace("DRS", "D R S")
        message = message.replace("ERS", "E R S")
        
        # Add priority indicators
        if alert.priority == AlertPriority.CRITICAL:
            message = f"Critical alert: {message}"
        elif alert.priority == AlertPriority.HIGH:
            message = f"Important: {message}"
        
        return message

def main():
    """Demo race engineer AI"""
    print("🏎️  F1 24 RACE ENGINEER AI - DEMO")
    print("=" * 50)
    
    engineer = RaceEngineerAI()
    
    # Simulate race data untuk demo
    demo_race_data = {
        'telemetry': {
            'speed': 285,
            'throttle_percent': 98,
            'brake_percent': 0,
            'gear': 7,
            'rpm': 11500,
            'drs_active': True,
            'tyre_temps': {
                'front_left': 102,
                'front_right': 104,
                'rear_left': 108,
                'rear_right': 112  # Critical temp
            },
            'brake_temps': {
                'front_left': 650,
                'front_right': 680,
                'rear_left': 720,  # High temp
                'rear_right': 700
            },
            'engine_temp': 95
        },
        'car_status': {
            'fuel_remaining': 28.5,
            'fuel_capacity': 110,
            'fuel_remaining_laps': 2.8,  # Low fuel
            'tyre_compound': 16,  # C5 Soft
            'tyre_age': 28,  # High wear
            'drs_allowed': True,
            'ers_energy': 2.1
        },
        'lap_info': {
            'current_lap': 45,
            'last_lap_time': 78.234,
            'best_lap_time': 76.891,
            'sector': 2,
            'pit_status': 0,
            'position': 8
        }
    }
    
    print("🎮 Processing demo race data...")
    print("-" * 30)
    
    # Process race data
    analysis = engineer.process_race_data(demo_race_data)
    
    print(f"📊 Analysis timestamp: {datetime.fromtimestamp(analysis['timestamp']).strftime('%H:%M:%S')}")
    print(f"🚨 New alerts generated: {len(analysis['new_alerts'])}")
    
    if analysis['new_alerts']:
        print(f"\n🔥 ALERTS:")
        for alert in analysis['new_alerts']:
            priority_icon = {
                AlertPriority.LOW: "ℹ️",
                AlertPriority.MEDIUM: "⚠️",
                AlertPriority.HIGH: "🚨",
                AlertPriority.CRITICAL: "🔥"
            }
            
            icon = priority_icon.get(alert.priority, "❓")
            print(f"   {icon} [{alert.category.upper()}] {alert.message}")
    
    if analysis['recommendations']:
        print(f"\n💡 RECOMMENDATIONS:")
        for rec in analysis['recommendations']:
            print(f"   • {rec}")
    
    print(f"\n📈 Alert summary by category:")
    for category, count in analysis['alert_counts'].items():
        print(f"   {category}: {count} alerts")
    
    print(f"\n🎯 Race Engineer AI is ready for real telemetry data!")

if __name__ == "__main__":
    main()
