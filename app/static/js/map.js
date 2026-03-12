/**
 * MIT-WPU Vyas Smart-Room Maintenance Tracker
 * Map Interaction JavaScript
 */

// ============================================
// DOM READY
// ============================================
document.addEventListener('DOMContentLoaded', function () {
    initializeFloorMap();
    initializeReportForm();
    initializeValidation();
});

// Building Outline Path (Approximation of Vyas Building)
const BUILDING_OUTLINE_PATH = `
    <path d="M20 100 L120 20 L480 20 L480 780 L20 780 Z" 
          class="building-outline" />
`;

// ============================================
// FLOOR MAP INITIALIZATION
// ============================================
function initializeFloorMap() {
    const floorSelect = document.getElementById('floorSelect');
    const floorMapContainer = document.getElementById('floorMapContainer');

    if (!floorSelect || !floorMapContainer) return;

    // Floor change - load rooms and render map
    floorSelect.addEventListener('change', function () {
        const floorId = this.value;
        const floorName = this.options[this.selectedIndex].text;
        const floorLevel = this.options[this.selectedIndex].dataset.level;

        if (floorId) {
            loadFloorMap(floorId, floorName, floorLevel);
        } else {
            floorMapContainer.innerHTML = `
                <div class="floor-map-placeholder">
                    <i class="bi bi-building display-1 text-muted"></i>
                    <p class="mt-3">Select a floor to view the interactive map</p>
                </div>
            `;
        }
    });

    // Auto-load if pre-selected
    if (typeof preSelectedFloor !== 'undefined' && preSelectedFloor) {
        const option = floorSelect.querySelector(`option[value="${preSelectedFloor}"]`);
        if (option) {
            floorSelect.value = preSelectedFloor;
            loadFloorMap(preSelectedFloor, option.text, option.dataset.level);
        }
    }
}

// ============================================
// LOAD FLOOR MAP
// ============================================
function loadFloorMap(floorId, floorName, floorLevel) {
    const floorMapContainer = document.getElementById('floorMapContainer');

    // Show loading
    floorMapContainer.innerHTML = `
        <div class="floor-map-placeholder">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <p class="mt-3">Loading floor plan...</p>
        </div>
    `;

    // Fetch rooms for this floor
    fetch(`/api/rooms/floor/${floorId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                renderFloorMap(floorMapContainer, data.rooms, floorLevel);
            } else {
                floorMapContainer.innerHTML = `
                    <div class="floor-map-placeholder">
                        <i class="bi bi-exclamation-triangle display-1 text-warning"></i>
                        <p class="mt-3">Failed to load floor plan</p>
                    </div>
                `;
            }
        })
        .catch(error => {
            console.error('Error loading floor map:', error);
            floorMapContainer.innerHTML = `
                <div class="floor-map-placeholder">
                    <i class="bi bi-exclamation-triangle display-1 text-danger"></i>
                    <p class="mt-3">Error loading floor plan: ${error.message}</p>
                </div>
            `;
        });
}


// ============================================
// RENDER FLOOR MAP
// ============================================
// ============================================
// RENDER FLOOR MAP
// ============================================
// ============================================
// RENDER FLOOR MAP
// ============================================
function renderFloorMap(container, rooms, floorLevel) {
    // Floors with detailed layout
    const detailedFloors = ['1', '2', '3', '4', '5', '7'];

    if (floorLevel === '0') {
        // Render Ground Floor (Visual Layout)
        renderGroundFloor(container, rooms);
    } else if (detailedFloors.includes(floorLevel) && rooms.length >= 10) {
        // Render detailed layout
        renderDetailedLayout(container, rooms, floorLevel);
    } else {
        // Render generic grid layout (6th)
        renderGenericFloor(container, rooms);
    }
}

// ============================================
// RENDER GROUND FLOOR
// ============================================
// ============================================
// RENDER GROUND FLOOR
// ============================================
// ============================================
// RENDER GROUND FLOOR
// ============================================
function renderGroundFloor(container, rooms, isAdmin = false) {
    const findRoom = (num) => rooms.find(r => r.number === num);

    const renderRoomRect = (roomNum, x, y, w, h, labelText, typeOverride) => {
        const room = findRoom(roomNum);
        const roomId = room ? room.id : '';
        const type = typeOverride || (room ? room.room_type : 'unknown');
        const isIssue = room && room.status === 'issue';
        const isInProgress = room && room.status === 'in-progress';

        let className = 'room-poly';

        // Color mapping
        if (type === 'management') className += ' fill-silver';
        else if (type === 'faculty') className += ' fill-orange';
        else if (type === 'lab' || type === 'breakout') className += ' fill-red';
        else if (type === 'class') className += ' fill-blue';
        else if (type === 'washroom') className += ' fill-red';
        else if (type === 'lift') className += ' fill-pink';

        if (isIssue) className += ' has-issue';
        else if (isInProgress) className += ' in-progress';

        const attrs = room ?
            `data-room="${roomNum}" data-room-id="${roomId}" onclick="selectRoom('${roomNum}', ${roomId})"` :
            'class="room-disabled"';

        let circleHtml = '';
        if (isAdmin) {
            const radius = 6;
            const padding = 4;
            const cx = x + w - radius - padding;
            const cy = y + radius + padding;
            
            let circleFill = '#28a745'; // normal (green)
            if (isIssue) circleFill = '#dc3545'; // issue reported (red)
            else if (isInProgress) circleFill = '#ffc107'; // in progress (yellow)
            
            circleHtml = `<circle cx="${cx}" cy="${cy}" r="${radius}" fill="${circleFill}" stroke="white" stroke-width="1.5" />`;
        }

        return `
            <g class="room-group" ${attrs}>
                <rect x="${x}" y="${y}" width="${w}" height="${h}" class="${className}" rx="4" />
                <text x="${x + w / 2}" y="${y + h / 2}" class="room-text" text-anchor="middle" dominant-baseline="middle" fill="white">${labelText || roomNum}</text>
                ${circleHtml}
            </g>
        `;
    };

    // V5 Layout applied to Ground Floor
    // Outline: Perfect Outline with Top Overlap Fix
    const SVG_OUTLINE = `
        <path d="M50 10 L480 350 L480 950 L50 950 Z" 
              class="building-outline" />
    `;

    const svgContent = `
        <svg viewBox="0 0 530 980" width="100%" height="100%" class="interactive-map">
            <defs>
                <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
                    <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
                    <feMerge>
                        <feMergeNode in="coloredBlur"/>
                        <feMergeNode in="SourceGraphic"/>
                    </feMerge>
                </filter>
            </defs>
            
            ${SVG_OUTLINE}

            <!-- LEFT COLUMN (x=60, w=100) -->
            <!-- Top Lifts (3) -->
            ${renderRoomRect('VY0Lift1', 60, 50, 30, 25, 'L', 'lift')}
            ${renderRoomRect('VY0Lift2', 60, 80, 30, 25, 'L', 'lift')}
            ${renderRoomRect('VY0Lift3', 60, 110, 30, 25, 'L', 'lift')}

            <!-- VY001 (Blue) -->
            ${renderRoomRect('VY001', 60, 150, 100, 120, 'VY001', 'class')}
            
            <!-- VY002 (Blue) -->
            ${renderRoomRect('VY002', 60, 280, 100, 120, null, 'class')}

            <!-- Middle Lifts (2) -->
            ${renderRoomRect('VY0Lift4', 60, 410, 30, 25, 'L', 'lift')}
            ${renderRoomRect('VY0Lift5', 60, 440, 30, 25, 'L', 'lift')}

            <!-- LOWER BLOCK START (y=500) -->
            
            <!-- VY003 (Blue) -->
            ${renderRoomRect('VY003', 60, 500, 100, 140, null, 'class')}

            <!-- VY004 (Blue) -->
            ${renderRoomRect('VY004', 60, 650, 100, 140, null, 'class')}

            <!-- Bottom Lifts (3) -->
            ${renderRoomRect('VY0Lift6', 60, 800, 30, 25, 'L', 'lift')}
            ${renderRoomRect('VY0Lift7', 60, 830, 30, 25, 'L', 'lift')}
            ${renderRoomRect('VY0Lift8', 60, 860, 30, 25, 'L', 'lift')}


            <!-- CENTER COLUMN -->
            <!-- VY024 (Tall Blue) -->
            ${renderRoomRect('VY024', 170, 190, 100, 160, 'VY024', 'class')}

            <!-- VY026 (Faculty) - Tucked Slot -->
            ${renderRoomRect('VY026', 280, 290, 80, 100, 'VY026', 'faculty')} 

            <!-- LAB STACK -->
            <!-- VY027 -->
            ${renderRoomRect('VY027', 170, 500, 180, 65, 'VY027', 'lab')}
            <!-- VY028 -->
            ${renderRoomRect('VY028', 170, 575, 180, 65, 'VY028', 'lab')}
            <!-- VY029 -->
            ${renderRoomRect('VY029', 170, 650, 180, 65, 'VY029', 'lab')}
            <!-- VY030 -->
            ${renderRoomRect('VY030', 170, 725, 180, 65, 'VY030', 'lab')}


            <!-- RIGHT COLUMN (x=380) -->
            <!-- Service Stack Top (Using empty washroom slots for visual consistency) -->
            ${renderRoomRect('WR1', 380, 370, 90, 22, '', 'washroom')}
            ${renderRoomRect('WR2', 380, 400, 90, 22, '', 'washroom')}
            ${renderRoomRect('WR3', 380, 430, 90, 22, '', 'washroom')}
            ${renderRoomRect('WR4', 380, 460, 90, 22, '', 'washroom')}

            <!-- VY016 (Class) - Slot 14 pos -->
            ${renderRoomRect('VY016', 380, 500, 90, 140, null, 'class')}

            <!-- VY015 (Class) - Slot 13 pos -->
            ${renderRoomRect('VY015', 380, 650, 90, 140, null, 'class')}

            <!-- VY014 (Lab) - Lower slot or separate? Let's put in Bottom Washroom area or just below -->
            <!-- Putting VY007 (Breakout) in bottom washroom slot -->
            ${renderRoomRect('VY007', 380, 800, 90, 55, 'Rest', 'breakout')}
            
        </svg>
    `;

    container.innerHTML = `
        <div class="vyas-floor-map svg-container">
            ${svgContent}
        </div>
    `;

    // Auto-select room...
    if (typeof preSelectedRoom !== 'undefined' && preSelectedRoom) {
        const roomGroup = container.querySelector(`g[data-room-id="${preSelectedRoom}"]`);
        if (roomGroup) {
            const onclickAttr = roomGroup.getAttribute('onclick');
            if (onclickAttr) eval(onclickAttr);
        }
    }
}

// ============================================
// RENDER DETAILED LAYOUT (SVG)
// ============================================
// ============================================
// RENDER DETAILED LAYOUT (SVG)
// ============================================
function renderDetailedLayout(container, rooms, floorLevel, isAdmin = false) {
    const findRoom = (num) => rooms.find(r => r.number === num);
    const getRoomNum = (suffix) => `VY${floorLevel}${suffix}`;

    const renderRoomRect = (suffix, x, y, w, h, labelText, typeOverride) => {
        const roomNum = getRoomNum(suffix);
        const room = findRoom(roomNum);
        const roomId = room ? room.id : '';
        const type = typeOverride || (room ? room.room_type : 'unknown');
        const isIssue = room && room.status === 'issue';
        const isInProgress = room && room.status === 'in-progress';

        let className = 'room-poly';
        if (type === 'class') className += ' fill-blue';
        else if (type === 'lab') className += ' fill-teal';
        else if (type === 'washroom') className += ' fill-red';
        else if (type === 'faculty') className += ' fill-orange';
        else if (type === 'lift') className += ' fill-pink';

        if (isIssue) className += ' has-issue';
        else if (isInProgress) className += ' in-progress';

        const roomName = room ? (room.name || roomNum) : roomNum;

        const attrs = room ?
            `data-room="${roomNum}" data-room-id="${roomId}" onclick="selectRoom('${roomNum}', ${roomId}, '${roomName.replace(/'/g, "\\'")}')"` :
            'class="room-disabled"';

        // Use provided label OR room number
        // Fix for NULL labels: check for null explicitly
        let displayLabel = labelText;
        if (displayLabel === undefined || displayLabel === null) {
            displayLabel = roomNum;
        }

        let circleHtml = '';
        if (isAdmin) {
            const radius = 6;
            const padding = 4;
            const cx = x + w - radius - padding;
            const cy = y + radius + padding;
            
            let circleFill = '#28a745'; // normal (green)
            if (isIssue) circleFill = '#dc3545'; // issue reported (red)
            else if (isInProgress) circleFill = '#ffc107'; // in progress (yellow)
            
            circleHtml = `<circle cx="${cx}" cy="${cy}" r="${radius}" fill="${circleFill}" stroke="white" stroke-width="1.5" />`;
        }

        return `
            <g class="room-group" ${attrs}>
                <rect x="${x}" y="${y}" width="${w}" height="${h}" class="${className}" rx="4" />
                <text x="${x + w / 2}" y="${y + h / 2}" class="room-text" text-anchor="middle" dominant-baseline="middle" fill="white" font-size="11">${displayLabel}</text>
                ${circleHtml}
            </g>
        `;
    };

    // Right diagonal with a "tip" at top-left
    // V5: Perfect outline, refined interior grid
    // Anchor Line: y=500 (Start of lower block)
    const SVG_OUTLINE = `
        <path d="M50 10 L480 350 L480 950 L50 950 Z" 
              class="building-outline" />
    `;

    const svgContent = `
        <svg viewBox="0 0 530 980" width="100%" height="100%" class="interactive-map">
            <defs>
                <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
                    <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
                    <feMerge>
                        <feMergeNode in="coloredBlur"/>
                        <feMergeNode in="SourceGraphic"/>
                    </feMerge>
                </filter>
            </defs>
            
            ${SVG_OUTLINE}

            <!-- LEFT COLUMN (x=60, w=100) -->
            <!-- Top Lifts (3) - Shifted down to clear diagonal -->
            ${renderRoomRect('Lift1', 60, 50, 30, 25, 'L', 'lift')}
            ${renderRoomRect('Lift2', 60, 80, 30, 25, 'L', 'lift')}
            ${renderRoomRect('Lift3', 60, 110, 30, 25, 'L', 'lift')}

            <!-- VY401 (Blue) -->
            ${renderRoomRect('01', 60, 150, 100, 120)}
            
            <!-- VY402 (Blue) -->
            ${renderRoomRect('02', 60, 280, 100, 120)}

            <!-- Middle Lifts (2) -->
            ${renderRoomRect('Lift4', 60, 410, 30, 25, 'L', 'lift')}
            ${renderRoomRect('Lift5', 60, 440, 30, 25, 'L', 'lift')}

            <!-- LOWER BLOCK START (y=500) -->
            
            <!-- VY403 (Blue) -->
            ${renderRoomRect('03', 60, 500, 100, 140)}

            <!-- VY404 (Blue) -->
            ${renderRoomRect('04', 60, 650, 100, 140)}

            <!-- Bottom Lifts (3) -->
            ${renderRoomRect('Lift6', 60, 800, 30, 25, 'L', 'lift')}
            ${renderRoomRect('Lift7', 60, 830, 30, 25, 'L', 'lift')}
            ${renderRoomRect('Lift8', 60, 860, 30, 25, 'L', 'lift')}


            <!-- CENTER COLUMN -->
            <!-- VY424 (Tall Blue) -->
            ${renderRoomRect('24', 170, 190, 100, 160)}

            <!-- VY422 (Teal) - Tucked -->
            ${renderRoomRect('22', 280, 290, 80, 100, null, 'lab')} 

            <!-- LAB STACK (Teal) -->
            <!-- Aligned with start of VY403 (y=500) -->
            ${renderRoomRect('26', 170, 500, 180, 65, undefined, 'lab')}
            ${renderRoomRect('27', 170, 575, 180, 65, undefined, 'lab')}
            ${renderRoomRect('28', 170, 650, 180, 65, undefined, 'lab')}
            ${renderRoomRect('29', 170, 725, 180, 65, undefined, 'lab')}


            <!-- RIGHT COLUMN (x=380) -->
            <!-- Service Stack Top (Red) -->
            ${renderRoomRect('18', 380, 370, 90, 22, null, 'washroom')}
            ${renderRoomRect('17', 380, 400, 90, 22, null, 'washroom')}
            ${renderRoomRect('16', 380, 430, 90, 22, null, 'washroom')}
            ${renderRoomRect('15', 380, 460, 90, 22, null, 'washroom')}

            <!-- VY414 (Blue) - Aligned with VY403/Lab26 (y=500) -->
            ${renderRoomRect('14', 380, 500, 90, 140)}

            <!-- VY413 (Blue) - Aligned with VY404/Lab28 -->
            ${renderRoomRect('13', 380, 650, 90, 140)}

            <!-- Service Stack Bottom (Red) -->
            ${renderRoomRect('08', 380, 800, 90, 25, null, 'washroom')}
            ${renderRoomRect('07', 380, 830, 90, 25, null, 'washroom')}
        </svg>
    `;
    container.innerHTML = `
        <div class="vyas-floor-map svg-container">
            ${svgContent}
        </div>
    `;

    // Auto-select room logic...
    if (typeof preSelectedRoom !== 'undefined' && preSelectedRoom) {
        const roomGroup = container.querySelector(`g[data-room-id="${preSelectedRoom}"]`);
        if (roomGroup) {
            const onclickAttr = roomGroup.getAttribute('onclick');
            if (onclickAttr) eval(onclickAttr);
        }
    }
}

// ============================================
// RENDER GENERIC FLOOR
// ============================================
function renderGenericFloor(container, rooms) {
    const roomsHtml = rooms.map(room => {
        let roomClass = 'room-block';
        if (room.room_type === 'class') roomClass += ' classroom';
        else if (room.room_type === 'lab') roomClass += ' lab';
        else if (room.room_type === 'washroom') roomClass += ' washroom';

        if (room.status === 'issue') roomClass += ' has-issue';
        else if (room.status === 'in-progress') roomClass += ' in-progress';

        return `
            <div class="${roomClass}" 
                 data-room="${room.number}" 
                 data-room-id="${room.id}"
                 data-type="${room.room_type}"
                 onclick="selectRoom('${room.number}', ${room.id}, '${(room.name || room.number).replace(/'/g, "\\'")}')">
                <span class="room-label">${room.number}</span>
            </div>
        `;
    }).join('');

    container.innerHTML = `
        <div class="vyas-floor-map">
            <div class="floor-layout generic">
                <div class="generic-grid">
                    ${roomsHtml}
                </div>
            </div>
        </div>
    `;

    // Auto-select room if pre-selected
    if (typeof preSelectedRoom !== 'undefined' && preSelectedRoom) {
        const roomBlock = container.querySelector(`[data-room-id="${preSelectedRoom}"]`);
        if (roomBlock) {
            roomBlock.click();
        }
    }
}

// ============================================
// SELECT ROOM
// ============================================
function selectRoom(roomNumber, roomId, roomName) {
    // Update hidden input
    const roomInput = document.getElementById('room_id');
    if (roomInput) {
        roomInput.value = roomId;
    }

    // Display Name if available, otherwise Number
    const displayName = roomName || roomNumber;

    // Update display
    const display = document.getElementById('selectedRoomDisplay');
    if (display) {
        display.innerHTML = `
            <div class="room-selected">
                <i class="bi bi-check-circle-fill me-2"></i>
                <span class="room-number">${displayName}</span>
                <small class="d-block">Selected</small>
            </div>
        `;
    }

    // Highlight on map
    // Reset previous
    document.querySelectorAll('.room-group').forEach(el => el.classList.remove('selected'));
    document.querySelectorAll('.room-poly').forEach(el => el.classList.remove('selected'));

    const roomGroup = document.querySelector(`g[data-room="${roomNumber}"]`);
    if (roomGroup) {
        roomGroup.classList.add('selected');
        const poly = roomGroup.querySelector('.room-poly');
        if (poly) poly.classList.add('selected');
    }

    // Load assets for this room
    loadAssets(roomId);
}

// ============================================
// LOAD ASSETS
// ============================================
function loadAssets(roomId) {
    const assetSelect = document.getElementById('asset_id');
    if (!assetSelect) return;

    fetch(`/api/assets/${roomId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                assetSelect.innerHTML = '<option value="">Select Asset (Optional)</option>';
                data.assets.forEach(asset => {
                    const option = document.createElement('option');
                    option.value = asset.id;
                    option.textContent = `${asset.name} (${asset.asset_type})`;
                    assetSelect.appendChild(option);
                });
                assetSelect.disabled = false;
            }
        })
        .catch(error => {
            console.error('Error loading assets:', error);
        });
}

// ============================================
// FORM SUBMISSION
// ============================================
function initializeReportForm() {
    const reportForm = document.getElementById('reportForm');
    if (!reportForm) return;

    reportForm.addEventListener('submit', handleFormSubmit);
}

function handleFormSubmit(e) {
    e.preventDefault();

    const form = e.target;
    const submitBtn = document.getElementById('submitBtn');
    const errorAlert = document.getElementById('errorAlert');
    const errorMessage = document.getElementById('errorMessage');

    // Client-side validation
    if (!validateForm()) {
        return;
    }

    // Check room selected
    const roomId = document.getElementById('room_id').value;
    if (!roomId) {
        showErrors(['Please select a room from the map']);
        return;
    }

    // Disable submit button
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="bi bi-hourglass-split me-2"></i>Submitting...';
    }

    // Hide error alert
    if (errorAlert) {
        errorAlert.style.display = 'none';
    }

    // Submit form via AJAX
    const formData = new FormData(form);

    fetch(form.action, {
        method: 'POST',
        body: formData,
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showSuccessModal(data.ticket_id);
                form.reset();
                resetRoomSelection();
            } else {
                showErrors(data.errors || ['An error occurred']);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showErrors(['Network error. Please try again.']);
        })
        .finally(() => {
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = '<i class="bi bi-send me-2"></i>Submit Report';
            }
        });
}

function resetRoomSelection() {
    const roomInput = document.getElementById('room_id');
    const display = document.getElementById('selectedRoomDisplay');
    const assetSelect = document.getElementById('asset_id');

    if (roomInput) roomInput.value = '';
    if (display) {
        display.innerHTML = `
            <div class="room-placeholder">
                <i class="bi bi-door-open"></i>
                <span>No room selected</span>
            </div>
        `;
    }
    if (assetSelect) {
        assetSelect.innerHTML = '<option value="">Select Asset</option>';
        assetSelect.disabled = true;
    }

    document.querySelectorAll('.room-block').forEach(block => {
        block.classList.remove('selected');
    });
}

// ============================================
// FORM VALIDATION
// ============================================
function initializeValidation() {
    // PRN validation - numeric only
    const prnInput = document.getElementById('prn');
    if (prnInput) {
        prnInput.addEventListener('input', function () {
            this.value = this.value.replace(/[^0-9]/g, '');
        });
    }

    // Email validation
    const emailInput = document.getElementById('reporter_email');
    if (emailInput) {
        emailInput.addEventListener('blur', function () {
            validateEmail(this);
        });
    }
}

function validateForm() {
    let isValid = true;

    // Validate PRN
    const prnInput = document.getElementById('prn');
    if (prnInput && prnInput.value) {
        if (!/^\d+$/.test(prnInput.value)) {
            prnInput.classList.add('is-invalid');
            isValid = false;
        } else {
            prnInput.classList.remove('is-invalid');
        }
    }

    // Validate Email
    const emailInput = document.getElementById('reporter_email');
    if (emailInput && emailInput.value) {
        if (!validateEmail(emailInput)) {
            isValid = false;
        }
    }

    return isValid;
}

function validateEmail(input) {
    const email = input.value.toLowerCase().trim();
    const isValid = email.endsWith('@mitwpu.edu.in');

    if (!isValid && email) {
        input.classList.add('is-invalid');
        return false;
    } else {
        input.classList.remove('is-invalid');
        return true;
    }
}

// ============================================
// SUCCESS MODAL
// ============================================
function showSuccessModal(ticketId) {
    const modal = document.getElementById('successModal');
    const ticketIdElement = document.getElementById('successTicketId');

    if (ticketIdElement) {
        ticketIdElement.textContent = '#' + ticketId.toString().padStart(4, '0');
    }

    if (modal) {
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
    }
}

function closeSuccessModal() {
    const modal = document.getElementById('successModal');
    if (modal) {
        const bsModal = bootstrap.Modal.getInstance(modal);
        if (bsModal) {
            bsModal.hide();
        }
    }
}

// ============================================
// ERROR HANDLING
// ============================================
function showErrors(errors) {
    const errorAlert = document.getElementById('errorAlert');
    const errorMessage = document.getElementById('errorMessage');

    if (errorAlert && errorMessage) {
        errorMessage.innerHTML = Array.isArray(errors)
            ? errors.join('<br>')
            : errors;
        errorAlert.style.display = 'block';
        errorAlert.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
}

// ============================================
// UTILITY FUNCTIONS
// ============================================
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-IN', {
        day: '2-digit',
        month: 'short',
        year: 'numeric'
    });
}

// ============================================
// FILE UPLOAD PREVIEW
// ============================================
document.addEventListener('DOMContentLoaded', function () {
    const fileInput = document.getElementById('image');
    if (!fileInput) return;

    fileInput.addEventListener('change', function () {
        const file = this.files[0];
        if (file) {
            // Validate file size (16MB max)
            if (file.size > 16 * 1024 * 1024) {
                alert('File size must be less than 16MB');
                this.value = '';
                return;
            }

            // Validate file type
            const allowedTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/gif', 'image/webp'];
            if (!allowedTypes.includes(file.type)) {
                alert('Only image files (PNG, JPG, GIF, WEBP) are allowed');
                this.value = '';
                return;
            }
        }
    });
});
