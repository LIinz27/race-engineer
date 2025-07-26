// Standings Page JavaScript

// Connect to Socket.IO server
const socket = io();

// Elements
const trackName = document.getElementById('track-name');
const sessionType = document.getElementById('session-type');
const sessionRemaining = document.getElementById('session-remaining');
const weatherCondition = document.getElementById('weather-condition');
const trackTemp = document.getElementById('track-temp');
const airTemp = document.getElementById('air-temp');
const standingsBody = document.getElementById('standings-body');

// Store driver data
const driversData = {};

// Session type mapping
const sessionTypeMap = {
    0: 'Unknown',
    1: 'Practice 1',
    2: 'Practice 2',
    3: 'Practice 3',
    4: 'Short Practice',
    5: 'Qualifying 1',
    6: 'Qualifying 2',
    7: 'Qualifying 3',
    8: 'Short Qualifying',
    9: 'One Shot Qualifying',
    10: 'Race',
    11: 'Race 2',
    12: 'Time Trial'
};

// Weather condition mapping
const weatherMap = {
    0: 'Clear',
    1: 'Light Cloud',
    2: 'Overcast',
    3: 'Light Rain',
    4: 'Heavy Rain',
    5: 'Storm'
};

// Team colors mapping
const teamColorMap = {
    0: 'mercedes',
    1: 'ferrari',
    2: 'redbull',
    3: 'williams',
    4: 'aston-martin',
    5: 'alpine',
    6: 'alphatauri',
    7: 'haas',
    8: 'mclaren',
    9: 'alfa-romeo'
};

// Driver status mapping
const driverStatusMap = {
    0: 'In Garage',
    1: 'Flying Lap',
    2: 'In Lap',
    3: 'Out Lap',
    4: 'On Track'
};

// Track names
const trackNames = {
    0: 'Melbourne',
    1: 'Paul Ricard',
    2: 'Shanghai',
    3: 'Bahrain',
    4: 'Catalunya',
    5: 'Monaco',
    6: 'Montreal',
    7: 'Silverstone',
    8: 'Hockenheim',
    9: 'Hungaroring',
    10: 'Spa',
    11: 'Monza',
    12: 'Singapore',
    13: 'Suzuka',
    14: 'Abu Dhabi',
    15: 'Texas',
    16: 'Brazil',
    17: 'Austria',
    18: 'Sochi',
    19: 'Mexico',
    20: 'Baku',
    21: 'Sakhir Short',
    22: 'Silverstone Short',
    23: 'Texas Short',
    24: 'Suzuka Short',
    25: 'Hanoi',
    26: 'Zandvoort',
    27: 'Imola',
    28: 'Portimão',
    29: 'Jeddah',
    30: 'Miami'
};

// Socket.IO event listeners
socket.on('connect', () => {
    console.log('Connected to server');
});

socket.on('disconnect', () => {
    console.log('Disconnected from server');
});

// Listen for session updates
socket.on('session_data_update', (data) => {
    // Update track info
    trackName.textContent = trackNames[data.track_id] || 'Unknown Track';
    sessionType.textContent = sessionTypeMap[data.session_type] || 'Unknown Session';
    
    // Update weather info
    weatherCondition.textContent = weatherMap[data.weather] || 'Unknown';
    trackTemp.textContent = `${data.track_temperature}°C`;
    airTemp.textContent = `${data.air_temperature}°C`;
    
    // Update session time remaining
    if (data.session_time_left > 0) {
        const minutes = Math.floor(data.session_time_left / 60);
        const seconds = Math.floor(data.session_time_left % 60);
        sessionRemaining.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
    } else {
        sessionRemaining.textContent = 'Session Ended';
    }
});

// Listen for participants data
socket.on('participants_update', (data) => {
    // Store driver names and teams
    data.participants.forEach((driver, index) => {
        if (!driversData[index]) {
            driversData[index] = {};
        }
        
        driversData[index].name = driver.name;
        driversData[index].team = driver.team_id;
        driversData[index].teamColor = teamColorMap[driver.team_id] || 'default';
    });
    
    // Update standings table if we have lap data
    updateStandingsTable();
});

// Listen for lap data updates
socket.on('lap_data_batch_update', (data) => {
    // Store lap data for each driver
    data.forEach((lapData, index) => {
        if (!driversData[index]) {
            driversData[index] = {};
        }
        
        driversData[index].position = lapData.car_position;
        driversData[index].lastLapTime = lapData.last_lap_time_in_ms;
        driversData[index].bestLapTime = lapData.best_lap_time_in_ms;
        driversData[index].sector1 = lapData.sector1_time_in_ms;
        driversData[index].sector2 = lapData.sector2_time_in_ms;
        driversData[index].status = lapData.driver_status;
        driversData[index].lapNumber = lapData.current_lap_num;
        
        // Calculate gaps
        if (index > 0 && data[0]) {
            driversData[index].gap = (lapData.total_distance - data[0].total_distance) * -1;
        } else {
            driversData[index].gap = 0;
        }
        
        // Calculate intervals
        if (index > 0 && data[index-1]) {
            driversData[index].interval = (lapData.total_distance - data[index-1].total_distance) * -1;
        } else {
            driversData[index].interval = 0;
        }
    });
    
    // Update standings table
    updateStandingsTable();
});

// Function to update the standings table
function updateStandingsTable() {
    // Clear existing rows
    standingsBody.innerHTML = '';
    
    // Sort drivers by position
    const sortedDrivers = Object.entries(driversData)
        .filter(([_, driver]) => driver.position) // Filter out drivers without position
        .sort((a, b) => a[1].position - b[1].position);
    
    // Add rows for each driver
    sortedDrivers.forEach(([driverIndex, driver]) => {
        const row = document.createElement('tr');
        row.className = `team-${driver.teamColor}`;
        
        // Convert gap and interval from distance to time format
        const gapDisplay = driver.position === 1 ? 'Leader' : formatGap(driver.gap);
        const intervalDisplay = driver.position === 1 ? '' : formatGap(driver.interval);
        
        // Create driver status indicator
        const statusClass = getStatusClass(driver.status);
        
        row.innerHTML = `
            <td>${driver.position}</td>
            <td>
                <span class="status-indicator ${statusClass}"></span>
                ${driver.name || `Driver ${driverIndex}`}
            </td>
            <td>${getTeamName(driver.team)}</td>
            <td>${formatTime(driver.bestLapTime)}</td>
            <td>${formatTime(driver.lastLapTime)}</td>
            <td>${gapDisplay}</td>
            <td>${intervalDisplay}</td>
            <td>${formatTime(driver.sector1)}</td>
            <td>${formatTime(driver.sector2)}</td>
            <td>${calculateSector3(driver)}</td>
            <td>${driver.pitStops || 0}</td>
            <td>${driverStatusMap[driver.status] || 'Unknown'}</td>
        `;
        
        standingsBody.appendChild(row);
    });
}

// Function to get team name from ID
function getTeamName(teamId) {
    const teams = {
        0: 'Mercedes',
        1: 'Ferrari',
        2: 'Red Bull Racing',
        3: 'Williams',
        4: 'Aston Martin',
        5: 'Alpine',
        6: 'AlphaTauri',
        7: 'Haas',
        8: 'McLaren',
        9: 'Alfa Romeo'
    };
    
    return teams[teamId] || 'Unknown Team';
}

// Function to get status class
function getStatusClass(statusId) {
    switch (statusId) {
        case 0:
            return 'status-pitting';
        case 1:
        case 2:
        case 3:
        case 4:
            return 'status-racing';
        default:
            return '';
    }
}

// Function to calculate sector 3 time
function calculateSector3(driver) {
    if (driver.lastLapTime > 0 && driver.sector1 > 0 && driver.sector2 > 0) {
        const s3 = driver.lastLapTime - driver.sector1 - driver.sector2;
        return formatTime(s3);
    }
    return '--:--:---';
}

// Function to format gap (distance to time approximation)
function formatGap(distanceGap) {
    // Convert distance to time (very rough approximation)
    // Average speed ~80 m/s as a rough conversion factor
    const timeGap = Math.abs(distanceGap) / 80;
    
    if (timeGap < 0.1) {
        return '+0.0s';
    }
    
    return `+${timeGap.toFixed(1)}s`;
}

// Function to format milliseconds to MM:SS.sss format
function formatTime(timeInMs) {
    if (!timeInMs || timeInMs <= 0) return '--:--:---';
    
    const minutes = Math.floor(timeInMs / 60000);
    const seconds = Math.floor((timeInMs % 60000) / 1000);
    const milliseconds = timeInMs % 1000;
    
    return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}.${milliseconds.toString().padStart(3, '0')}`;
}
