// Time Telemetry JavaScript

// Connect to Socket.IO server
const socket = io();

// Elements
const currentLapTime = document.getElementById('current-lap-time');
const lastLapTime = document.getElementById('last-lap-time');
const bestLapTime = document.getElementById('best-lap-time');
const lapNumber = document.getElementById('lap-number');
const bestLapNumber = document.getElementById('best-lap-number');
const lastLapDelta = document.getElementById('last-lap-delta');
const currentS1 = document.getElementById('current-s1');
const bestS1 = document.getElementById('best-s1');
const deltaS1 = document.getElementById('delta-s1');
const currentS2 = document.getElementById('current-s2');
const bestS2 = document.getElementById('best-s2');
const deltaS2 = document.getElementById('delta-s2');
const currentS3 = document.getElementById('current-s3');
const bestS3 = document.getElementById('best-s3');
const deltaS3 = document.getElementById('delta-s3');
const lapHistoryBody = document.getElementById('lap-history-body');

// Lap history data
const lapHistoryData = [];
let bestLapTimeMs = 0;
let lapChart = null;

// Initialize lap chart
function initLapChart() {
    const ctx = document.getElementById('lap-chart').getContext('2d');
    
    lapChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Lap Times',
                data: [],
                backgroundColor: 'rgba(33, 150, 243, 0.2)',
                borderColor: 'rgba(33, 150, 243, 1)',
                borderWidth: 2,
                tension: 0.1,
                fill: false
            },
            {
                label: 'Best Lap',
                data: [],
                backgroundColor: 'rgba(76, 175, 80, 0.2)',
                borderColor: 'rgba(76, 175, 80, 1)',
                borderWidth: 2,
                borderDash: [5, 5],
                tension: 0.1,
                fill: false
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: false,
                    reverse: true,
                    ticks: {
                        callback: function(value) {
                            return formatTime(value);
                        }
                    },
                    title: {
                        display: true,
                        text: 'Lap Time'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Lap Number'
                    }
                }
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return formatTime(context.raw);
                        }
                    }
                }
            }
        }
    });
}

// Call initialize chart on page load
initLapChart();

// Socket.IO event listeners
socket.on('connect', () => {
    console.log('Connected to server');
});

socket.on('disconnect', () => {
    console.log('Disconnected from server');
});

socket.on('lap_data_update', (data) => {
    // Update current lap info
    currentLapTime.textContent = formatTime(data.current_lap_time_in_ms);
    lapNumber.textContent = data.current_lap_num;
    
    // Update sector times
    currentS1.textContent = formatTime(data.sector1_time_in_ms);
    currentS2.textContent = formatTime(data.sector2_time_in_ms);
    currentS3.textContent = "Calculating..."; // S3 is usually calculated at lap end
    
    // If we have a completed lap
    if (data.last_lap_time_in_ms > 0) {
        // Update last lap time
        lastLapTime.textContent = formatTime(data.last_lap_time_in_ms);
        
        // Calculate delta to best lap
        if (bestLapTimeMs > 0) {
            const delta = data.last_lap_time_in_ms - bestLapTimeMs;
            lastLapDelta.textContent = formatDelta(delta);
            lastLapDelta.className = delta > 0 ? 'negative' : 'positive';
        }
        
        // Check if this is a new best lap
        if (bestLapTimeMs === 0 || data.last_lap_time_in_ms < bestLapTimeMs) {
            bestLapTimeMs = data.last_lap_time_in_ms;
            bestLapTime.textContent = formatTime(bestLapTimeMs);
            bestLapNumber.textContent = data.current_lap_num - 1;
        }
        
        // Add lap to history
        addLapToHistory(data.current_lap_num - 1, data.last_lap_time_in_ms, data.sector1_time_in_ms, data.sector2_time_in_ms);
    }
    
    // Update best sector times
    if (data.sector1_time_in_ms > 0) {
        if (bestS1.textContent === '--:--:---' || data.sector1_time_in_ms < parseTiming(bestS1.textContent)) {
            bestS1.textContent = formatTime(data.sector1_time_in_ms);
        }
        
        // Calculate delta
        const s1Delta = data.sector1_time_in_ms - parseTiming(bestS1.textContent);
        deltaS1.textContent = formatDelta(s1Delta);
        deltaS1.className = s1Delta > 0 ? 'negative' : 'positive';
    }
    
    if (data.sector2_time_in_ms > 0) {
        if (bestS2.textContent === '--:--:---' || data.sector2_time_in_ms < parseTiming(bestS2.textContent)) {
            bestS2.textContent = formatTime(data.sector2_time_in_ms);
        }
        
        // Calculate delta
        const s2Delta = data.sector2_time_in_ms - parseTiming(bestS2.textContent);
        deltaS2.textContent = formatDelta(s2Delta);
        deltaS2.className = s2Delta > 0 ? 'negative' : 'positive';
    }
    
    // Calculate S3 time if available
    if (data.last_lap_time_in_ms > 0 && data.sector1_time_in_ms > 0 && data.sector2_time_in_ms > 0) {
        const s3Time = data.last_lap_time_in_ms - data.sector1_time_in_ms - data.sector2_time_in_ms;
        if (s3Time > 0) {
            currentS3.textContent = formatTime(s3Time);
            
            // Update best S3 if needed
            if (bestS3.textContent === '--:--:---' || s3Time < parseTiming(bestS3.textContent)) {
                bestS3.textContent = formatTime(s3Time);
            }
            
            // Calculate delta
            const s3Delta = s3Time - parseTiming(bestS3.textContent);
            deltaS3.textContent = formatDelta(s3Delta);
            deltaS3.className = s3Delta > 0 ? 'negative' : 'positive';
        }
    }
});

// Function to add a lap to the history
function addLapToHistory(lapNum, lapTime, s1Time, s2Time) {
    // Calculate S3 time
    const s3Time = lapTime - s1Time - s2Time;
    
    // Add to lap history data array
    lapHistoryData.push({
        lap: lapNum,
        time: lapTime,
        s1: s1Time,
        s2: s2Time,
        s3: s3Time
    });
    
    // Add to lap history table
    const row = document.createElement('tr');
    
    // Calculate delta from best lap
    const delta = lapTime - bestLapTimeMs;
    const deltaClass = delta > 0 ? 'negative' : 'positive';
    
    row.innerHTML = `
        <td>${lapNum}</td>
        <td>${formatTime(lapTime)}</td>
        <td>${formatTime(s1Time)}</td>
        <td>${formatTime(s2Time)}</td>
        <td>${formatTime(s3Time)}</td>
        <td class="${deltaClass}">${formatDelta(delta)}</td>
    `;
    
    // Prepend row to the table (newest laps at the top)
    lapHistoryBody.prepend(row);
    
    // Update chart
    updateLapChart();
}

// Function to update the lap chart
function updateLapChart() {
    // Clear existing data
    lapChart.data.labels = [];
    lapChart.data.datasets[0].data = [];
    lapChart.data.datasets[1].data = [];
    
    // Add lap history data
    lapHistoryData.forEach(lap => {
        lapChart.data.labels.push(lap.lap);
        lapChart.data.datasets[0].data.push(lap.time);
        
        // Add best lap line (flat line at best lap time)
        lapChart.data.datasets[1].data.push(bestLapTimeMs);
    });
    
    // Update chart
    lapChart.update();
}

// Function to format milliseconds to MM:SS.sss format
function formatTime(timeInMs) {
    if (!timeInMs || timeInMs <= 0) return '--:--:---';
    
    const minutes = Math.floor(timeInMs / 60000);
    const seconds = Math.floor((timeInMs % 60000) / 1000);
    const milliseconds = timeInMs % 1000;
    
    return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}.${milliseconds.toString().padStart(3, '0')}`;
}

// Function to format delta time (+/-SS.sss)
function formatDelta(deltaInMs) {
    if (!deltaInMs) return '+0.000';
    
    const sign = deltaInMs >= 0 ? '+' : '-';
    const absDelta = Math.abs(deltaInMs);
    const seconds = Math.floor(absDelta / 1000);
    const milliseconds = absDelta % 1000;
    
    return `${sign}${seconds}.${milliseconds.toString().padStart(3, '0')}`;
}

// Function to parse timing string back to milliseconds
function parseTiming(timeString) {
    if (timeString === '--:--:---') return 0;
    
    const parts = timeString.split(/[:.]/);
    if (parts.length !== 3) return 0;
    
    const minutes = parseInt(parts[0]);
    const seconds = parseInt(parts[1]);
    const milliseconds = parseInt(parts[2]);
    
    return minutes * 60000 + seconds * 1000 + milliseconds;
}
