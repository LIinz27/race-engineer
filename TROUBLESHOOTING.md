# F1 24 Telemetry Dashboard - Troubleshooting Guide

## 🔍 Problem: Data Not Updating ("datanya tidak berubah")

Dashboard berjalan normal tapi data tidak berubah. Ini karena F1 24 tidak mengirim UDP packets ke dashboard.

### ✅ Checklist Langkah-langkah:

#### 1. **Pastikan F1 24 Telemetry Aktif**
```
F1 24 Game → Settings → Telemetry Settings:
- UDP Telemetry: ON
- UDP Port: 20777
- UDP IP Address: 127.0.0.1 (localhost)
- UDP Send Rate: 20Hz atau lebih tinggi
- UDP Format: 2024
```

#### 2. **Pastikan Anda Dalam Session Game**
F1 24 hanya mengirim telemetry data ketika:
- ✅ Dalam practice session
- ✅ Dalam qualifying session  
- ✅ Dalam race session
- ✅ Dalam time trial
- ❌ TIDAK di main menu
- ❌ TIDAK di garage/setup menu

#### 3. **Cek Windows Firewall**
Windows mungkin memblokir UDP port 20777:
```powershell
# Buka PowerShell sebagai Administrator, lalu jalankan:
New-NetFirewallRule -DisplayName "F1 24 Telemetry" -Direction Inbound -Protocol UDP -LocalPort 20777 -Action Allow
```

#### 4. **Test dengan Game Lain (Opsional)**
Jika punya game F1 23 atau game EA Sports lain, coba test dengan game itu untuk memastikan dashboard berfungsi.

#### 5. **Manual Network Test**
Test apakah port 20777 terbuka:
```powershell
# Test UDP port
netstat -an | findstr :20777
```

### 🐛 Debug Mode

Dashboard sudah memiliki debug mode. Jika berjalan dengan benar, Anda akan melihat:
```
⏰ [DEBUG] Still listening on port 20777... No packets received yet.
🎮 [DEBUG] Make sure F1 24 telemetry is enabled and you're in a session!
```

Ketika menerima data, akan muncul:
```
🎯 [DEBUG] Packet #1 received from ('127.0.0.1', 12345), size: 1464 bytes
📦 [DEBUG] First 24 bytes: f12024000000000002000000...
```

### 🎯 Solusi yang Paling Umum

**90% kasus**: Pastikan Anda berada dalam session aktif (practice/qualifying/race) di F1 24, bukan di menu utama!

### 📞 Jika Masih Bermasalah

1. Screenshot pengaturan telemetry F1 24
2. Screenshot output terminal dashboard
3. Konfirmasi bahwa Anda sedang dalam session game (tidak di menu)

## 🏁 Success Indicators

Dashboard berhasil ketika Anda melihat:
- Web browser menampilkan posisi driver berubah-ubah
- Terminal menampilkan packet yang diterima
- Lap times dan sector times terupdate real-time
