// Car Telemetry JavaScript

// Connect to Socket.IO server
const socket = io();

// Elements
const speedValue = document.getElementById('speed-value');
const rpmValue = document.getElementById('rpm-value');
const gearValue = document.getElementById('gear-value');
const throttleBar = document.getElementById('throttle-bar');
const throttleValue = document.getElementById('throttle-value');
const brakeBar = document.getElementById('brake-bar');
const brakeValue = document.getElementById('brake-value');
const flTemp = document.getElementById('fl-temp');
const frTemp = document.getElementById('fr-temp');
const rlTemp = document.getElementById('rl-temp');
const rrTemp = document.getElementById('rr-temp');
const drsIndicator = document.getElementById('drs-indicator');

// Create speed gauge
const speedGauge = new Gauge(document.getElementById('speed-gauge')).setOptions({
    angle: 0,
    lineWidth: 0.3,
    radiusScale: 0.8,
    pointer: {
        length: 0.6,
        strokeWidth: 0.035,
        color: '#ffffff'
    },
    limitMax: false,
    limitMin: false,
    colorStart: '#6fadcf',
    colorStop: '#4caf50',
    strokeColor: '#e0e0e0',
    generateGradient: true,
    highDpiSupport: true,
    staticZones: [
        { strokeStyle: "#4caf50", min: 0, max: 150 }, // Green
        { strokeStyle: "#ff9800", min: 150, max: 300 }, // Yellow
        { strokeStyle: "#f44336", min: 300, max: 400 } // Red
    ],
    staticLabels: {
        font: "10px sans-serif",
        labels: [0, 100, 200, 300, 400],
        color: "#ffffff",
        fractionDigits: 0
    },
});
speedGauge.maxValue = 400; // Maximum speed
speedGauge.setMinValue(0);
speedGauge.animationSpeed = 10;
speedGauge.set(0);

// Create RPM gauge
const rpmGauge = new Gauge(document.getElementById('rpm-gauge')).setOptions({
    angle: 0,
    lineWidth: 0.3,
    radiusScale: 0.8,
    pointer: {
        length: 0.6,
        strokeWidth: 0.035,
        color: '#ffffff'
    },
    limitMax: false,
    limitMin: false,
    colorStart: '#6fadcf',
    colorStop: '#f44336',
    strokeColor: '#e0e0e0',
    generateGradient: true,
    highDpiSupport: true,
    staticZones: [
        { strokeStyle: "#4caf50", min: 0, max: 10000 }, // Green
        { strokeStyle: "#ff9800", min: 10000, max: 12000 }, // Yellow
        { strokeStyle: "#f44336", min: 12000, max: 15000 } // Red
    ],
    staticLabels: {
        font: "10px sans-serif",
        labels: [0, 5000, 10000, 15000],
        color: "#ffffff",
        fractionDigits: 0
    },
});
rpmGauge.maxValue = 15000; // Maximum RPM
rpmGauge.setMinValue(0);
rpmGauge.animationSpeed = 10;
rpmGauge.set(0);

// Socket.IO event listeners
socket.on('connect', () => {
    console.log('Connected to server');
});

socket.on('disconnect', () => {
    console.log('Disconnected from server');
});

socket.on('car_telemetry_update', (data) => {
    // Update speed
    speedValue.textContent = data.speed;
    speedGauge.set(data.speed);
    
    // Update RPM
    rpmValue.textContent = data.engine_rpm;
    rpmGauge.set(data.engine_rpm);
    
    // Update gear
    const gear = data.gear;
    if (gear === -1) {
        gearValue.textContent = 'R';
    } else if (gear === 0) {
        gearValue.textContent = 'N';
    } else {
        gearValue.textContent = gear;
    }
    
    // Update throttle
    const throttlePercentage = data.throttle;
    throttleBar.style.height = `${throttlePercentage}%`;
    throttleValue.textContent = `${Math.round(throttlePercentage)}%`;
    
    // Update brake
    const brakePercentage = data.brake;
    brakeBar.style.height = `${brakePercentage}%`;
    brakeValue.textContent = `${Math.round(brakePercentage)}%`;
    
    // Update tyre temperatures
    flTemp.textContent = `${data.tyres_surface_temperature.front_left}°C`;
    frTemp.textContent = `${data.tyres_surface_temperature.front_right}°C`;
    rlTemp.textContent = `${data.tyres_surface_temperature.rear_left}°C`;
    rrTemp.textContent = `${data.tyres_surface_temperature.rear_right}°C`;
    
    // Update DRS status
    if (data.drs === 1) {
        drsIndicator.classList.remove('inactive');
        drsIndicator.classList.add('active');
    } else {
        drsIndicator.classList.remove('active');
        drsIndicator.classList.add('inactive');
    }
});

// Function to format milliseconds to MM:SS.sss format
function formatTime(timeInMs) {
    if (!timeInMs || timeInMs <= 0) return '--:--:---';
    
    const minutes = Math.floor(timeInMs / 60000);
    const seconds = Math.floor((timeInMs % 60000) / 1000);
    const milliseconds = timeInMs % 1000;
    
    return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}.${milliseconds.toString().padStart(3, '0')}`;
}
