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
function renderGroundFloor(container, rooms) {
    const findRoom = (num) => rooms.find(r => r.number === num);

    const renderRoomRect = (roomNum, x, y, w, h, labelText, typeOverride) => {
        const room = findRoom(roomNum);
        const roomId = room ? room.id : '';
        const type = typeOverride || (room ? room.room_type : 'unknown');
        const isIssue = room && room.status === 'issue';

        let className = 'room-poly';

        // Color mapping based on type
        if (type === 'management') className += ' fill-silver';
        else if (type === 'faculty') className += ' fill-orange';
        else if (type === 'lab' || type === 'breakout') className += ' fill-red';
        else if (type === 'class') className += ' fill-blue';
        else if (type === 'washroom') className += ' fill-red';

        if (isIssue) className += ' has-issue';

        // Accessibility/Interaction attributes
        const attrs = room ?
            `data-room="${roomNum}" data-room-id="${roomId}" onclick="selectRoom('${roomNum}', ${roomId})"` :
            'class="room-disabled"';

        return `
            <g class="room-group" ${attrs}>
                <rect x="${x}" y="${y}" width="${w}" height="${h}" class="${className}" rx="4" />
                <text x="${x + w / 2}" y="${y + h / 2}" class="room-text" text-anchor="middle" dominant-baseline="middle">${labelText || roomNum}</text>
            </g>
        `;
    };

    // ViewBox 0 0 500 800
    const svgContent = `
        <svg viewBox="0 0 500 800" width="100%" height="100%" class="interactive-map">
            <defs>
                <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
                    <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
                    <feMerge>
                        <feMergeNode in="coloredBlur"/>
                        <feMergeNode in="SourceGraphic"/>
                    </feMerge>
                </filter>
            </defs>
            
            <!-- CORRIDOR / BACKGROUND STRUCTURE -->
            <path d="M120 0 L120 800 M340 230 L340 800" stroke="#e9ecef" stroke-width="2" fill="none" />

            <!-- LEFT COLUMN -->
            ${renderRoomRect('VY001', 20, 20, 100, 100, '001', 'management')}
            ${renderRoomRect('VY002', 20, 130, 100, 100)}
            
            <!-- Entrance Gap -->
            
            ${renderRoomRect('VY003', 20, 350, 100, 100)}
            ${renderRoomRect('VY004', 20, 460, 100, 100)}

            <!-- TOP CENTER SECTION -->
            ${renderRoomRect('VY024', 140, 20, 100, 100, '024', 'management')}
            ${renderRoomRect('VY026', 140, 130, 100, 80, '026', 'faculty')}

            <!-- CENTER BLOCK -->
            ${renderRoomRect('VY027', 140, 250, 180, 80, '027', 'management')}
            ${renderRoomRect('VY028', 140, 340, 180, 60)}
            ${renderRoomRect('VY029', 140, 410, 180, 60)}
            ${renderRoomRect('VY030', 140, 480, 180, 60)}

            <!-- RIGHT COLUMN -->
            ${renderRoomRect('VY016', 340, 250, 90, 100)}
            ${renderRoomRect('VY015', 340, 360, 90, 100)}
            ${renderRoomRect('VY014', 340, 480, 90, 80, '014', 'lab')}

            <!-- BOTTOM AREA -->
            ${renderRoomRect('VY007', 250, 600, 100, 80, 'Breakout\nArea', 'breakout')}
            
            <!-- You Here Indicator -->
            <g transform="translate(80, 280)">
                 <path d="M0 0 L10 -5 L10 5 Z" fill="#c8102e" />
                 <text x="15" y="4" font-size="12" fill="#333">You Are Here</text>
            </g>
        </svg>
    `;

    container.innerHTML = `
        <div class="vyas-floor-map svg-container">
            ${svgContent}
        </div>
    `;

    // Auto-select room if pre-selected
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
function renderDetailedLayout(container, rooms, floorLevel) {
    const findRoom = (num) => rooms.find(r => r.number === num);

    // Helper to generate room number from suffix (e.g., '01' -> 'VY401')
    const getRoomNum = (suffix) => `VY${floorLevel}${suffix}`;

    const renderRoomRect = (suffix, x, y, w, h, labelText) => {
        const roomNum = getRoomNum(suffix);
        const room = findRoom(roomNum);
        // Default styling if room missing from DB
        const roomId = room ? room.id : '';
        const type = room ? room.room_type : 'unknown';
        const isIssue = room && room.status === 'issue';

        let className = 'room-poly';
        if (type === 'class') className += ' fill-blue';
        else if (type === 'lab') className += ' fill-teal';
        else if (type === 'washroom') className += ' fill-red';

        if (isIssue) className += ' has-issue';

        // Accessibility/Interaction attributes
        const attrs = room ?
            `data-room="${roomNum}" data-room-id="${roomId}" onclick="selectRoom('${roomNum}', ${roomId})"` :
            'class="room-disabled"';

        return `
            <g class="room-group" ${attrs}>
                <rect x="${x}" y="${y}" width="${w}" height="${h}" class="${className}" rx="4" />
                <text x="${x + w / 2}" y="${y + h / 2}" class="room-text" text-anchor="middle" dominant-baseline="middle">${labelText || roomNum}</text>
            </g>
        `;
    };

    // ViewBox 0 0 500 800
    const svgContent = `
        <svg viewBox="0 0 500 800" width="100%" height="100%" class="interactive-map">
            <defs>
                <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
                    <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
                    <feMerge>
                        <feMergeNode in="coloredBlur"/>
                        <feMergeNode in="SourceGraphic"/>
                    </feMerge>
                </filter>
            </defs>
            
            <!-- CORRIDOR / BACKGROUND STRUCTURE (Optional context) -->
            <path d="M130 0 L130 800 M330 300 L330 800" stroke="#e9ecef" stroke-width="2" fill="none" />

            <!-- LEFT COLUMN (Classrooms) -->
            ${renderRoomRect('01', 20, 50, 100, 100)}
            ${renderRoomRect('02', 20, 160, 100, 100)}
            
            <!-- Gap for corridor/stairs -->
            
            ${renderRoomRect('03', 20, 350, 100, 100)}
            ${renderRoomRect('04', 20, 460, 100, 100)}

            <!-- TOP CENTER SECTION -->
            ${renderRoomRect('24', 140, 50, 100, 140)}
            ${renderRoomRect('22', 250, 120, 70, 70)}

            <!-- CENTER LABS SECTION -->
            ${renderRoomRect('26', 140, 350, 180, 60)}
            ${renderRoomRect('27', 140, 420, 180, 60)}
            ${renderRoomRect('28', 140, 490, 180, 60)}
            ${renderRoomRect('29', 140, 560, 180, 60)}

            <!-- RIGHT COLUMN (Classrooms) -->
            ${renderRoomRect('14', 340, 350, 90, 130)}
            ${renderRoomRect('13', 340, 490, 90, 130)}

            <!-- FAR RIGHT STRIP (Washrooms/Staff) -->
            <!-- Top Right cluster -->
            ${renderRoomRect('19', 440, 300, 40, 30, getRoomNum('19').slice(-3))}
            ${renderRoomRect('18', 440, 335, 40, 30, getRoomNum('18').slice(-3))}
            ${renderRoomRect('17', 440, 370, 40, 30, getRoomNum('17').slice(-3))}
            ${renderRoomRect('16', 440, 405, 40, 30, getRoomNum('16').slice(-3))}
            ${renderRoomRect('15', 440, 440, 40, 30, getRoomNum('15').slice(-3))}

            <!-- Bottom Right cluster -->
            ${renderRoomRect('08', 440, 550, 40, 30, getRoomNum('08').slice(-3))}
            ${renderRoomRect('07', 440, 585, 40, 30, getRoomNum('07').slice(-3))}
            
            <!-- You Here Indicator (Static Position for Demo) -->
            <g transform="translate(80, 300)">
                 <path d="M0 0 L10 -5 L10 5 Z" fill="#c8102e" />
                 <text x="15" y="4" font-size="12" fill="#333">You Are Here</text>
            </g>
        </svg>
    `;

    container.innerHTML = `
        <div class="vyas-floor-map svg-container">
            ${svgContent}
        </div>
    `;

    // Auto-select room if pre-selected
    if (typeof preSelectedRoom !== 'undefined' && preSelectedRoom) {
        const roomGroup = container.querySelector(`g[data-room-id="${preSelectedRoom}"]`);
        if (roomGroup) {
            const onclickAttr = roomGroup.getAttribute('onclick');
            if (onclickAttr) {
                eval(onclickAttr);
            }
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

        return `
            <div class="${roomClass}" 
                 data-room="${room.number}" 
                 data-room-id="${room.id}"
                 data-type="${room.room_type}"
                 onclick="selectRoom('${room.number}', ${room.id})">
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
function selectRoom(roomNumber, roomId) {
    // Update hidden input
    const roomInput = document.getElementById('room_id');
    if (roomInput) {
        roomInput.value = roomId;
    }

    // Update display
    const display = document.getElementById('selectedRoomDisplay');
    if (display) {
        display.innerHTML = `
            <div class="room-selected">
                <i class="bi bi-check-circle-fill me-2"></i>
                <span class="room-number">${roomNumber}</span>
                <small class="d-block">Selected</small>
            </div>
        `;
    }

    // Highlight selected room on map
    document.querySelectorAll('.room-block, .room-group').forEach(block => {
        block.classList.remove('selected');
    });

    const selectedBlock = document.querySelector(`[data-room-id="${roomId}"]`);
    if (selectedBlock) {
        selectedBlock.classList.add('selected');
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
