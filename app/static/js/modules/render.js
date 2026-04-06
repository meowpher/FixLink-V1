/**
 * Map Rendering Module - Handles all SVG and grid-based floor plan generation.
 */

import { selectRoom } from './ui.js';

// Attach to window so SVG onclick works
window.selectRoom = selectRoom;

const SVG_OUTLINE = `
    <path d="M50 10 L480 350 L480 950 L50 950 Z" 
          class="building-outline" />
`;

/**
 * Main rendering entry point.
 * @param {HTMLElement} container 
 * @param {Array} rooms 
 * @param {string} floorLevel 
 * @param {boolean} isAdmin
 */
export function renderFloorMap(container, rooms, floorLevel, isAdmin = false) {
    const detailedFloors = ['1', '2', '3', '4', '5', '7'];

    if (floorLevel === '0') {
        renderGroundFloor(container, rooms, isAdmin);
    } else if (detailedFloors.includes(floorLevel) && rooms.length >= 10) {
        renderDetailedLayout(container, rooms, floorLevel, isAdmin);
    } else {
        renderGenericFloor(container, rooms, isAdmin);
    }
}

/**
 * Ground floor (Vyas V1) specific layout.
 */
export function renderGroundFloor(container, rooms, isAdmin = false) {
    const findRoom = (num) => rooms.find(r => r.number === num);

    const renderRoomRect = (roomNum, x, y, w, h, labelText, typeOverride) => {
        const room = findRoom(roomNum);
        const roomId = room ? room.id : '';
        const type = typeOverride || (room ? room.room_type : 'unknown');
        const isIssue = room && room.status === 'issue';
        const isInProgress = room && room.status === 'in-progress';
        const isAssigned = room && room.status === 'assigned';
        const roomName = (room ? (room.name || roomNum) : roomNum).replace(/'/g, "\\'");

        let className = 'room-poly';
        if (type === 'class') className += ' fill-blue';
        else if (type === 'lab' || type === 'breakout') className += ' fill-red';
        else if (type === 'faculty') className += ' fill-orange';
        else if (type === 'washroom') className += ' fill-red';
        else if (type === 'lift') className += ' fill-pink';
        else if (type === 'management') className += ' fill-silver';

        if (isAdmin) {
            if (isIssue) className += ' has-issue';
            else if (isInProgress) className += ' in-progress';
            else if (isAssigned) className += ' assigned';
        }

        const attrs = room ?
            `data-room="${roomNum}" data-room-id="${roomId}" onclick="selectRoom('${roomNum}', ${roomId}, '${roomName}', '${type}')"` :
            'class="room-disabled"';

        let circleHtml = isAdmin ? renderAdminIndicators(x, y, w, isIssue, isInProgress, isAssigned) : '';

        return `
            <g class="room-group" ${attrs}>
                <rect x="${x}" y="${y}" width="${w}" height="${h}" class="${className}" rx="4" />
                <text x="${x + w / 2}" y="${y + h / 2}" class="room-text" text-anchor="middle" dominant-baseline="middle" fill="white">${labelText || roomNum}</text>
                ${circleHtml}
            </g>
        `;
    };

    const svgContent = `
        <svg viewBox="0 0 530 980" width="100%" height="100%" class="interactive-map">
            <defs>
                <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
                    <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
                    <feMerge><feMergeNode in="coloredBlur"/><feMergeNode in="SourceGraphic"/></feMerge>
                </filter>
            </defs>
            ${SVG_OUTLINE}
            ${renderGroundFloorGrid(renderRoomRect)}
        </svg>
    `;

    container.innerHTML = `<div class="vyas-floor-map svg-container">${svgContent}</div>`;
    handleAutoSelect(container);
}

/**
 * Detailed layout for standard floors (1, 2, 3, 4, 5, 7).
 */
export function renderDetailedLayout(container, rooms, floorLevel, isAdmin = false) {
    const findRoom = (num) => rooms.find(r => r.number === num);
    const getRoomNum = (suffix) => `VY${floorLevel}${suffix}`;

    const renderRoomRect = (suffix, x, y, w, h, labelText, typeOverride) => {
        const roomNum = getRoomNum(suffix);
        const room = findRoom(roomNum);
        const roomId = room ? room.id : '';
        const type = typeOverride || (room ? room.room_type : 'unknown');
        const isIssue = room && room.status === 'issue';
        const isInProgress = room && room.status === 'in-progress';
        const isAssigned = room && room.status === 'assigned';
        const roomName = (room ? (room.name || roomNum) : roomNum).replace(/'/g, "\\'");

        let className = 'room-poly';
        if (type === 'class') className += ' fill-blue';
        else if (type === 'lab') className += ' fill-teal';
        else if (type === 'washroom') className += ' fill-red';
        else if (type === 'faculty') className += ' fill-orange';
        else if (type === 'lift') className += ' fill-pink';

        if (isAdmin) {
            if (isIssue) className += ' has-issue';
            else if (isInProgress) className += ' in-progress';
            else if (isAssigned) className += ' assigned';
        }

        const attrs = room ?
            `data-room="${roomNum}" data-room-id="${roomId}" onclick="selectRoom('${roomNum}', ${roomId}, '${roomName}', '${type}')"` :
            'class="room-disabled"';

        let circleHtml = isAdmin ? renderAdminIndicators(x, y, w, isIssue, isInProgress, isAssigned) : '';

        return `
            <g class="room-group" ${attrs}>
                <rect x="${x}" y="${y}" width="${w}" height="${h}" class="${className}" rx="4" />
                <text x="${x + w / 2}" y="${y + h / 2}" class="room-text" text-anchor="middle" dominant-baseline="middle" fill="white" font-size="11">${labelText || roomNum}</text>
                ${circleHtml}
            </g>
        `;
    };

    const svgContent = `
        <svg viewBox="0 0 530 980" width="100%" height="100%" class="interactive-map">
            <defs>
                <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
                    <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
                    <feMerge><feMergeNode in="coloredBlur"/><feMergeNode in="SourceGraphic"/></feMerge>
                </filter>
            </defs>
            ${SVG_OUTLINE}
            ${renderStandardFloorGrid(renderRoomRect)}
        </svg>
    `;

    container.innerHTML = `<div class="vyas-floor-map svg-container">${svgContent}</div>`;
    handleAutoSelect(container);
}

/**
 * Generic grid layout for non-standardized floors (e.g. 6th).
 */
export function renderGenericFloor(container, rooms, isAdmin = false) {
    const roomsHtml = rooms.map(room => {
        let roomClass = 'room-block';
        if (room.room_type === 'class') roomClass += ' classroom';
        else if (room.room_type === 'lab') roomClass += ' lab';
        else if (room.room_type === 'washroom') roomClass += ' washroom';

        if (isAdmin) {
            if (room.status === 'issue') roomClass += ' has-issue';
            else if (room.status === 'in-progress') roomClass += ' in-progress';
            else if (room.status === 'assigned') roomClass += ' assigned';
        }

        const roomName = (room.name || room.number).replace(/'/g, "\\'");
        
        let indicatorHtml = '';
        if (isAdmin) {
            const isIssue = room.status === 'issue';
            const isInProgress = room.status === 'in-progress';
            const isAssigned = room.status === 'assigned';
            const color = isIssue ? '#dc3545' : (isInProgress ? '#ffc107' : (isAssigned ? '#0d6efd' : '#28a745'));
            indicatorHtml = `<span class="admin-indicator" style="background-color: ${color}; width: 8px; height: 8px; border-radius: 50%; display: inline-block; margin-left: 5px; border: 1px solid white;"></span>`;
        }

        return `
            <div class="${roomClass}" 
                 data-room="${room.number}" 
                 data-room-id="${room.id}"
                 onclick="selectRoom('${room.number}', ${room.id}, '${roomName}', '${room.room_type}')">
                <span class="room-label">${room.number}${indicatorHtml}</span>
            </div>
        `;
    }).join('');

    container.innerHTML = `
        <div class="vyas-floor-map"><div class="floor-layout generic"><div class="generic-grid">${roomsHtml}</div></div></div>
    `;
    handleAutoSelect(container);
}

// Helpers

function renderAdminIndicators(x, y, w, isIssue, isInProgress, isAssigned) {
    const radius = 6;
    const padding = 4;
    const cx = x + w - radius - padding;
    const cy = y + radius + padding;
    let circleFill = isIssue ? '#dc3545' : (isInProgress ? '#ffc107' : (isAssigned ? '#0d6efd' : '#28a745'));
    return `<circle cx="${cx}" cy="${cy}" r="${radius}" fill="${circleFill}" stroke="white" stroke-width="1.5" />`;
}

function handleAutoSelect(container) {
    if (typeof preSelectedRoom !== 'undefined' && preSelectedRoom) {
        const roomEl = container.querySelector(`[data-room-id="${preSelectedRoom}"]`);
        if (roomEl) {
            if (roomEl.tagName === 'g') {
                const onclick = roomEl.getAttribute('onclick');
                if (onclick) eval(onclick);
            } else {
                roomEl.click();
            }
        }
    }
}

/**
 * Internal Grid Definitions to declutter main render functions.
 */
function renderGroundFloorGrid(renderRoomRect) {
    return `
        <!-- LEFT COLUMN -->
        ${renderRoomRect('VY0Lift1', 60, 50, 30, 25, 'L', 'lift')}
        ${renderRoomRect('VY0Lift2', 60, 80, 30, 25, 'L', 'lift')}
        ${renderRoomRect('VY0Lift3', 60, 110, 30, 25, 'L', 'lift')}
        ${renderRoomRect('VY001', 60, 150, 100, 120, 'VY001', 'class')}
        ${renderRoomRect('VY002', 60, 280, 100, 120, null, 'class')}
        ${renderRoomRect('VY0Lift4', 60, 410, 30, 25, 'L', 'lift')}
        ${renderRoomRect('VY0Lift5', 60, 440, 30, 25, 'L', 'lift')}
        ${renderRoomRect('VY003', 60, 500, 100, 140, null, 'class')}
        ${renderRoomRect('VY004', 60, 650, 100, 140, null, 'class')}
        ${renderRoomRect('VY0Lift6', 60, 800, 30, 25, 'L', 'lift')}
        ${renderRoomRect('VY0Lift7', 60, 830, 30, 25, 'L', 'lift')}
        ${renderRoomRect('VY0Lift8', 60, 860, 30, 25, 'L', 'lift')}

        <!-- CENTER COLUMN -->
        ${renderRoomRect('VY024', 170, 190, 100, 160, 'VY024', 'class')}
        ${renderRoomRect('VY026', 280, 290, 80, 100, 'VY026', 'faculty')} 
        ${renderRoomRect('VY027', 170, 500, 180, 65, 'VY027', 'lab')}
        ${renderRoomRect('VY028', 170, 575, 180, 65, 'VY028', 'lab')}
        ${renderRoomRect('VY029', 170, 650, 180, 65, 'VY029', 'lab')}
        ${renderRoomRect('VY030', 170, 725, 180, 65, 'VY030', 'lab')}

        <!-- RIGHT COLUMN -->
        ${renderRoomRect('WR1', 380, 370, 90, 22, '', 'washroom')}
        ${renderRoomRect('WR2', 380, 400, 90, 22, '', 'washroom')}
        ${renderRoomRect('WR3', 380, 430, 90, 22, '', 'washroom')}
        ${renderRoomRect('WR4', 380, 460, 90, 22, '', 'washroom')}
        ${renderRoomRect('VY016', 380, 500, 90, 140, null, 'class')}
        ${renderRoomRect('VY015', 380, 650, 90, 140, null, 'class')}
        ${renderRoomRect('VY007', 380, 800, 90, 55, 'Rest', 'breakout')}
    `;
}

function renderStandardFloorGrid(renderRoomRect) {
    return `
        <!-- LEFT COLUMN -->
        ${renderRoomRect('Lift1', 60, 50, 30, 25, 'L', 'lift')}
        ${renderRoomRect('Lift2', 60, 80, 30, 25, 'L', 'lift')}
        ${renderRoomRect('Lift3', 60, 110, 30, 25, 'L', 'lift')}
        ${renderRoomRect('01', 60, 150, 100, 120)}
        ${renderRoomRect('02', 60, 280, 100, 120)}
        ${renderRoomRect('Lift4', 60, 410, 30, 25, 'L', 'lift')}
        ${renderRoomRect('Lift5', 60, 440, 30, 25, 'L', 'lift')}
        ${renderRoomRect('03', 60, 500, 100, 140)}
        ${renderRoomRect('04', 60, 650, 100, 140)}
        ${renderRoomRect('Lift6', 60, 800, 30, 25, 'L', 'lift')}
        ${renderRoomRect('Lift7', 60, 830, 30, 25, 'L', 'lift')}
        ${renderRoomRect('Lift8', 60, 860, 30, 25, 'L', 'lift')}

        <!-- CENTER COLUMN -->
        ${renderRoomRect('24', 170, 190, 100, 160)}
        ${renderRoomRect('22', 280, 290, 80, 100, null, 'lab')} 
        ${renderRoomRect('26', 170, 500, 180, 65, undefined, 'lab')}
        ${renderRoomRect('27', 170, 575, 180, 65, undefined, 'lab')}
        ${renderRoomRect('28', 170, 650, 180, 65, undefined, 'lab')}
        ${renderRoomRect('29', 170, 725, 180, 65, undefined, 'lab')}

        <!-- RIGHT COLUMN -->
        ${renderRoomRect('18', 380, 370, 90, 22, null, 'washroom')}
        ${renderRoomRect('17', 380, 400, 90, 22, null, 'washroom')}
        ${renderRoomRect('16', 380, 430, 90, 22, null, 'washroom')}
        ${renderRoomRect('15', 380, 460, 90, 22, null, 'washroom')}
        ${renderRoomRect('14', 380, 500, 90, 140)}
        ${renderRoomRect('13', 380, 650, 90, 140)}
        ${renderRoomRect('08', 380, 800, 90, 25, null, 'washroom')}
        ${renderRoomRect('07', 380, 830, 90, 25, null, 'washroom')}
    `;
}
