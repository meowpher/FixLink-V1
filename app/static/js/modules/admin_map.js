/**
 * Admin Map Module - Handles admin-specific map interactions, technician assignment, and status updates.
 */

import { renderFloorMap } from './render.js';

/**
 * Initialize the Admin Map view.
 * @param {number} floorId 
 */
export async function initializeAdminMap(floorId) {
    const container = document.getElementById('adminMapContainer');
    if (!container || !floorId) return;

    renderLoading(container);

    try {
        const response = await fetch(`/admin/floor-data/${floorId}`);
        const result = await response.json();

        if (result.success) {
            container.innerHTML = '';
            renderFloorMap(container, result.rooms, result.floor.level.toString(), true);
            
            // Override selectRoom for admin view
            window.selectRoom = (roomNumber, roomId, roomName) => {
                highlightRoom(roomNumber);
                showRoomDetails(roomNumber, roomId);
            };

            // Handle deep-linking to specific room
            const urlParams = new URLSearchParams(window.location.search);
            const target = urlParams.get('room');
            if (target) {
                setTimeout(() => {
                    const el = document.querySelector(`g[data-room="${target}"]`);
                    if (el) {
                        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
                        window.selectRoom(target, null, null);
                        el.classList.add('pulse-focus');
                        setTimeout(() => el.classList.remove('pulse-focus'), 2000);
                    }
                }, 200);
            }
        } else {
            renderError(container, result.error || 'Failed to load floor data');
        }
    } catch (error) {
        renderError(container, error.message);
    }
}

/**
 * Fetch and display room status details in the side panel.
 */
export function showRoomDetails(roomNumber, roomId) {
    const panel = document.getElementById('roomDetailsPanel');
    const panelTitle = document.getElementById('panelRoomNumber');
    const panelBody = document.getElementById('panelBody');

    if (!panel || !panelTitle || !panelBody) return;

    panelTitle.textContent = roomNumber;
    panelBody.innerHTML = '<div class="p-4 text-center"><div class="spinner-border text-primary"></div><div class="mt-2 small text-muted">Fetching status...</div></div>';
    panel.style.display = 'block';

    fetch(`/admin/api/room-status/${roomNumber}`)
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                renderRoomDetails(panelBody, data);
            } else {
                panelBody.innerHTML = `<div class="alert alert-danger m-3 x-small">Error: ${data.error}</div>`;
            }
        })
        .catch(err => {
            panelBody.innerHTML = `<div class="alert alert-danger m-3 x-small">Network error: ${err.message}</div>`;
        });
}

function renderRoomDetails(container, data) {
    const { room, status, active_ticket, professionals } = data;
    
    let html = `
        <div class="mb-3 px-3 pt-3">
            <div class="d-flex justify-content-between align-items-start">
                <div>
                    <h6 class="mb-0 fw-bold">${room.name || room.number}</h6>
                    <p class="text-muted x-small mb-0 uppercase fw-bold">${room.room_type}</p>
                </div>
                <div class="badge ${status === 'issue' ? 'bg-danger' : (['in-progress', 'assigned'].includes(status) ? 'bg-warning text-dark' : 'bg-success')} px-2 py-1">
                    ${status.toUpperCase()}
                </div>
            </div>
        </div>

        <div class="px-3">
            <div class="action-bar d-flex gap-2 mb-4">
                <button onclick="toggleAssignForm()" class="action-btn btn-assign" title="Assign Technician">
                    <i class="bi bi-person-plus-fill"></i>
                </button>
                ${active_ticket ? `
                    <button onclick="completeTicket(${active_ticket.id})" class="action-btn btn-complete" title="Mark as Fixed">
                        <i class="bi bi-check-lg"></i>
                    </button>
                    <button onclick="deleteTicketFromMap(${active_ticket.id})" class="action-btn btn-delete" title="Delete Ticket">
                        <i class="bi bi-trash-fill"></i>
                    </button>
                ` : ''}
                <button onclick="window.focusRoom('${room.number}')" class="action-btn btn-map ms-auto" title="Focus Room">
                    <i class="bi bi-geo-alt-fill"></i>
                </button>
            </div>
        </div>

        <div class="px-3 pb-3">
    `;

    if (status === 'issue' && active_ticket) {
        html += `
            <div class="alert alert-danger border-0 shadow-sm mb-4">
                <div class="d-flex align-items-center mb-2">
                    <i class="bi bi-exclamation-octagon-fill fs-5 me-2"></i>
                    <strong>Needs Attention</strong>
                </div>
                <div class="mb-1"><strong>${active_ticket.issue_type.toUpperCase()}</strong></div>
                <div class="small opacity-75">${active_ticket.description}</div>
            </div>
            
            <div id="assignmentFormContainer" class="assignment-card bg-light rounded p-3 border mb-3" style="display:none;">
                <h6 class="small text-uppercase fw-bold text-muted mb-3">Assign Technician</h6>
                <div class="mb-2">
                    <label class="form-label x-small text-muted mb-1 uppercase fw-bold">Professional</label>
                    <select id="assignProf" class="form-select form-select-sm">
                        <option value="">Select Professional...</option>
                        ${Object.entries(professionals).map(([cat, profs]) => `
                            <optgroup label="${cat}">
                                ${profs.map(p => `<option value="${p.id}">${p.name}</option>`).join('')}
                            </optgroup>
                        `).join('')}
                    </select>
                </div>
                <div class="mb-3">
                    <label class="form-label x-small text-muted mb-1 uppercase fw-bold">Hours</label>
                    <input type="number" id="assignHours" class="form-control form-control-sm" value="2" min="1">
                </div>
                <button onclick="assignTechnician(${active_ticket.id})" class="btn btn-primary btn-sm w-100 shadow-sm">
                    Confirm Assignment
                </button>
            </div>
        `;
    } else if (['in-progress', 'assigned'].includes(status) && active_ticket) {
        html += `
            <div class="alert alert-warning border-0 shadow-sm mb-4">
                <div class="d-flex align-items-center mb-2">
                    <i class="bi bi-tools fs-5 me-2"></i>
                    <strong>Under Maintenance</strong>
                </div>
                <div class="small mb-1"><strong>${active_ticket.issue_type.toUpperCase()}</strong></div>
                <div class="small opacity-75 mb-3">${active_ticket.description}</div>
                <div class="p-2 bg-white bg-opacity-50 rounded border border-warning border-opacity-25">
                    <div class="x-small text-muted text-uppercase fw-bold">Assigned To</div>
                    <div class="small font-weight-bold">${active_ticket.assigned_professional_name}</div>
                    <div class="x-small text-muted">${active_ticket.assigned_professional_category}</div>
                </div>
            </div>
        `;
    } else {
        html += `
            <div class="text-center py-4 px-2">
                <div class="display-6 text-success mb-3">
                    <i class="bi bi-check-circle-fill"></i>
                </div>
                <h6 class="fw-bold">Everything is Normal</h6>
                <p class="text-muted small">No active maintenance issues found.</p>
            </div>
        `;
    }
    
    html += `</div>`;
    container.innerHTML = html;
}

function highlightRoom(roomNumber) {
    document.querySelectorAll('.room-group, .room-poly').forEach(el => el.classList.remove('selected'));
    const roomGroup = document.querySelector(`g[data-room="${roomNumber}"]`);
    if (roomGroup) {
        roomGroup.classList.add('selected');
        const poly = roomGroup.querySelector('.room-poly');
        if (poly) poly.classList.add('selected');
    }
}

// Admin API Actions

export async function assignTechnician(ticketId) {
    const profId = document.getElementById('assignProf').value;
    const hours = document.getElementById('assignHours').value;
    
    if (!profId) return alert('Please select a professional');
    
    try {
        const response = await fetch(`/admin/api/ticket/${ticketId}/assign`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
            },
            body: JSON.stringify({ professional_id: profId, time_limit_hours: hours })
        });
        const result = await response.json();
        if (result.success) {
            location.reload(); 
        } else {
            alert('Error: ' + result.error);
        }
    } catch (e) { console.error(e); }
}

export async function completeTicket(ticketId) {
    if (!confirm('Mark this ticket as resolved?')) return;
    try {
        const response = await fetch(`/admin/tickets/${ticketId}/status`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
            },
            body: JSON.stringify({ status: 'fixed' })
        });
        const result = await response.json();
        if (result.success) location.reload();
    } catch (e) { console.error(e); }
}

export async function deleteTicketFromMap(ticketId) {
    if (!confirm('Are you sure you want to delete this ticket?')) return;
    try {
        const response = await fetch(`/admin/tickets/${ticketId}/delete`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
            }
        });
        const result = await response.json();
        if (result.success) location.reload();
    } catch (e) { console.error(e); }
}

// UI Helpers

export function toggleAssignForm() {
    const container = document.getElementById('assignmentFormContainer');
    if (container) {
        container.style.display = container.style.display === 'none' ? 'block' : 'none';
    }
}

export function closeRoomDetails() {
    const panel = document.getElementById('roomDetailsPanel');
    if (panel) panel.style.display = 'none';
    document.querySelectorAll('.room-group, .room-poly').forEach(el => el.classList.remove('selected'));
}

function renderLoading(container) {
    container.innerHTML = '<div class="spinner-border text-primary m-auto" role="status"></div>';
}

function renderError(container, msg) {
    container.innerHTML = `<div class="alert alert-danger m-auto">${msg}</div>`;
}

// Export to window for HTML event handlers
window.assignTechnician = assignTechnician;
window.completeTicket = completeTicket;
window.deleteTicketFromMap = deleteTicketFromMap;
window.toggleAssignForm = toggleAssignForm;
window.closeRoomDetails = closeRoomDetails;
window.showRoomDetails = showRoomDetails;
