# F1 24 Race Engineer AI

**AI-powered race engineering assistant for F1 24**

🏎️ **Real-time telemetry analysis** • 🗣️ **Voice alerts** • 🧠 **Intelligent strategy advice**

---

## 🎯 Features

### 🔥 Real-Time Monitoring
- **Tyre Temperature**: Critical alerts at 110°C, warnings at 100°C
- **Brake Temperature**: All 4 corners monitoring
- **Engine Temperature**: Overheating protection
- **Fuel Management**: Remaining laps calculation, low fuel warnings
- **Tyre Wear**: Age tracking, degradation alerts
- **Performance**: Lap time analysis, sector comparison

### 🧠 AI Analysis Engine
- **Priority System**: Critical, High, Medium, Low alerts
- **Context Awareness**: Situation-specific recommendations  
- **Strategy Advice**: Pit window optimization
- **Predictive Warnings**: Proactive issue detection
- **Performance Analysis**: Lap time comparison and insights

### 🗣️ Voice Communication
- **Natural Speech**: Professional race engineer voice
- **Priority Filtering**: Only important messages spoken
- **Smart Timing**: Anti-spam with minimum intervals
- **Technical Translation**: User-friendly terminology

### 📊 Professional Interface
- **Real-time Statistics**: Packet rates, connection status
- **Session Reports**: Comprehensive performance summary
- **Alert History**: Track all warnings and recommendations
- **Configurable Settings**: Voice, priorities, intervals

---

## 🚀 Quick Start

### 1. Installation
```bash
git clone <repository>
cd race-engineer
pip install -r requirements.txt
```

### 2. F1 24 Setup
1. **Start F1 24**
2. **Settings > Telemetry Settings**
3. **UDP Telemetry = ON**
4. **UDP Port = 20777**
5. **UDP Send Rate = 60Hz**
6. **Start practice/race session**

### 3. Run Race Engineer
```bash
python race_engineer_main.py
```

---

## 🎮 Example Output

```
🏁 F1 24 RACE ENGINEER
AI-powered race engineering assistant

✅ Race Engineer session started
🔌 Listening on 127.0.0.1:20777
🎯 Monitoring telemetry for race engineering data...

🔥 [TYRE] CRITICAL: Rear Right tyre overheating at 112°C! Lift and coast!
🚨 [FUEL] LOW FUEL: 2.8 laps remaining
⚠️ [STRATEGY] Pit window open: Consider pit stop for fresh tyres
ℹ️ [PERFORMANCE] DRS available for next straight

📊 SESSION STATUS REPORT:
   📦 Packets processed: 45,888
   🚗 Telemetry packets: 1,250
   🚨 Total alerts: 15
   🗣️ Voice messages: 8
```

---

## 📋 Alert Types

### 🔥 Critical Alerts
- **Tyre Overheating**: >110°C surface temperature
- **Fuel Critical**: <1.5 laps remaining
- **Engine Critical**: Overheating detected

### 🚨 High Priority
- **Tyre Hot**: >100°C surface temperature  
- **Low Fuel**: <3 laps remaining
- **High Brake Temp**: >700°C brake temperature

### ⚠️ Strategic Warnings
- **Pit Window**: Optimal pit stop timing
- **Tyre Degradation**: Wear-based recommendations
- **Fuel Saving**: Efficiency suggestions

### ℹ️ Performance Info
- **Lap Comparison**: vs. personal best
- **DRS/ERS**: Availability notifications
- **Sector Analysis**: Performance breakdown

---

## 🔧 Configuration

### Voice Settings
```python
# Enable/disable voice
race_engineer.set_voice_enabled(True)

# Set priority filter (MEDIUM and above)
race_engineer.set_voice_priority_filter(AlertPriority.MEDIUM)
```

### Monitoring Settings
```python
settings = {
    'data_update_interval': 1.0,     # Analysis frequency (seconds)
    'status_report_interval': 30.0,  # Status reports (seconds)
    'voice_priority_filter': 'MEDIUM' # Minimum voice priority
}
```

---

## 🏗️ Architecture

### Core Components
- **`race_engineer_main.py`**: Main application coordinator
- **`telemetry_parser.py`**: F1 24 UDP packet parser
- **`race_engineer_ai.py`**: AI analysis and decision engine
- **`voice_system.py`**: Text-to-speech communication

### Data Flow
```
F1 24 Game → UDP Telemetry → Parser → AI Analysis → Voice + Console
```

### Packet Types Supported
- **Telemetry (ID: 6)**: Speed, throttle, temperatures, pressures
- **Lap Data (ID: 2)**: Times, positions, sectors, gaps
- **Car Status (ID: 7)**: Fuel, tyres, damage, ERS/DRS

---

## 🧪 Testing

### Connection Test
```bash
python connection_test_final.py
```

### Component Tests
```bash
python telemetry_parser.py    # Parser test
python race_engineer_ai.py    # AI demo
python voice_system.py        # Voice test
```

---

## 📊 Performance

### Tested Performance
- **Connection**: 189+ packets/second stable
- **Parsing**: 45,888 packets in 4 minutes
- **Response**: Sub-second alert generation
- **Reliability**: Zero packet loss during testing

### System Requirements
- **Python**: 3.7+
- **OS**: Windows (tested), Linux/Mac compatible
- **Memory**: <50MB typical usage
- **Network**: UDP port 20777 access

---

## 🎯 Use Cases

### 🏁 Race Sessions
- **Live Strategy**: Real-time pit stop recommendations
- **Performance**: Tire and fuel management guidance
- **Safety**: Critical temperature and damage alerts

### 🎓 Practice Sessions
- **Learning**: Understand car behavior and limits
- **Setup**: Optimize car configuration
- **Improvement**: Lap time and consistency analysis

### 🏆 Competitive Racing
- **Advantage**: Professional-level race engineering
- **Consistency**: Avoid costly mistakes
- **Strategy**: Optimal race management

---

## 🔬 Technical Details

### F1 24 Integration
- **Protocol**: UDP telemetry (official EA specification)
- **Format**: Binary packet parsing (24-byte headers)
- **Frequency**: 60Hz telemetry rate support
- **Compatibility**: F1 24 v1.19+ tested

### AI Engine
- **Real-time Analysis**: <100ms processing latency
- **Multi-threaded**: Separate parsing and analysis threads
- **Memory Efficient**: Circular buffers for data history
- **Extensible**: Plugin architecture for new features

---

## 🤝 Contributing

### Development Setup
```bash
git clone <repository>
cd race-engineer
pip install -r requirements.txt
```

### Adding Features
1. **New Alerts**: Extend `RaceEngineerAI.analyze_*()` methods
2. **Voice Messages**: Update `VoiceSystem.format_for_voice()`
3. **Packet Types**: Add parsing in `TelemetryParser`

### Testing
```bash
python -m pytest tests/
```

---

## 📝 Changelog

### v1.0.0 - Production Release
- ✅ Complete F1 24 telemetry integration
- ✅ AI-powered race analysis engine
- ✅ Professional voice communication system
- ✅ Real-time monitoring and alerts
- ✅ Comprehensive documentation
- ✅ Production-ready stability

---

## 📄 License

This project is developed for educational and personal use with F1 24.

---

## 🏁 Credits

Developed for F1 24 race simulation enthusiasts who want professional-level race engineering assistance.

**Drive smart, drive fast! 🏎️**
