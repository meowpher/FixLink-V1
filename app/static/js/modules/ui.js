/**
 * Map UI Module - Handles all DOM manipulation and user interaction.
 */

import { fetchAssetsByRoom } from './api.js';

export const DYNAMIC_ISSUE_TYPES = {
    'lift': [
        { value: 'lights', label: 'Lights' },
        { value: 'door_stuck', label: 'Door stuck' },
        { value: 'lift_not_working', label: 'Lift not working' },
        { value: 'lift_fan', label: 'Lift fan' }
    ],
    'class': [
        { value: 'chairs', label: 'Chairs' },
        { value: 'tables', label: 'Tables' },
        { value: 'power_socket', label: 'Power socket' },
        { value: 'projector', label: 'Projector' },
        { value: 'projector_white_screen', label: 'Projector White Screen' },
        { value: 'black_board', label: 'Black Board' },
        { value: 'left_tv', label: 'Left TV' },
        { value: 'right_tv', label: 'Right TV' },
        { value: 'fans', label: 'Fans' },
        { value: 'lights', label: 'Lights' }
    ],
    'lab': [
        { value: 'tables', label: 'Tables' },
        { value: 'chairs', label: 'Chairs' },
        { value: 'computers', label: 'Computers' },
        { value: 'projector', label: 'Projector' },
        { value: 'projector_white_screen', label: 'Projector White Screen' },
        { value: 'lights', label: 'Lights' },
        { value: 'ac', label: 'AC' },
        { value: 'fans', label: 'Fans' }
    ],
    'washroom': [
        { value: 'toilet', label: 'Toilet' },
        { value: 'toilet_stall', label: 'Toilet stall' },
        { value: 'water', label: 'Water' },
        { value: 'plumbing', label: 'Plumbing' },
        { value: 'cleanliness', label: 'Cleanliness' }
    ],
    'default': [
        { value: 'electrical', label: 'Electrical Issue' },
        { value: 'cleaning', label: 'Cleaning Required' },
        { value: 'furniture', label: 'Furniture Damage' },
        { value: 'ac', label: 'Air Conditioning' },
        { value: 'lights', label: 'Lighting' },
        { value: 'other', label: 'Other' }
    ]
};

/**
 * Handle room selection from the map.
 * @param {string} roomNumber 
 * @param {number} roomId 
 * @param {string} roomName 
 * @param {string} roomType 
 */
export function selectRoom(event, roomNumber, roomId, roomName, roomType) {
    // Update hidden input
    const roomInput = document.getElementById('room_id');
    if (roomInput) roomInput.value = roomId;

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
    document.querySelectorAll('.room-group, .room-poly').forEach(el => el.classList.remove('selected'));
    const roomGroup = document.querySelector(`g[data-room="${roomNumber}"]`);
    if (roomGroup) {
        roomGroup.classList.add('selected');
        const poly = roomGroup.querySelector('.room-poly');
        if (poly) poly.classList.add('selected');
    }

    // Load dynamic fields
    updateIssueTypes(roomType || 'unknown');
}

/**
 * Update the issue type dropdown based on room category.
 * @param {string} roomType 
 */
export function updateIssueTypes(roomType) {
    const issueSelect = document.getElementById('issue_type');
    if (!issueSelect) return;

    const optionsArray = DYNAMIC_ISSUE_TYPES[roomType] || DYNAMIC_ISSUE_TYPES['default'];

    issueSelect.innerHTML = '<option value="">Select Issue Type</option>';
    optionsArray.forEach(issue => {
        const option = document.createElement('option');
        option.value = issue.value;
        option.textContent = issue.label;
        issueSelect.appendChild(option);
    });

    issueSelect.disabled = false;
}

/**
 * Clear the current room selection.
 */
export function resetRoomSelection() {
    const roomInput = document.getElementById('room_id');
    const display = document.getElementById('selectedRoomDisplay');

    if (roomInput) roomInput.value = '';
    if (display) {
        display.innerHTML = `
            <div class="room-placeholder">
                <i class="bi bi-door-open"></i>
                <span>No room selected</span>
            </div>
        `;
    }

    document.querySelectorAll('.room-block, .room-group, .room-poly').forEach(block => {
        block.classList.remove('selected');
    });
}
