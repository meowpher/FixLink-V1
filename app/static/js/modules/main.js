/**
 * Map Main Module - Application entry point and coordination.
 */

import { fetchRoomsByFloor } from './api.js';
import { renderFloorMap } from './render.js';
import { resetRoomSelection } from './ui.js';

document.addEventListener('DOMContentLoaded', () => {
    initializeFloorMap();
    initializeReportForm();
    initializeValidation();
});

/**
 * Initialize floor selection and map loading.
 */
function initializeFloorMap() {
    const floorSelect = document.getElementById('floorSelect');
    const floorMapContainer = document.getElementById('floorMapContainer');
    if (!floorSelect || !floorMapContainer) return;

    floorSelect.addEventListener('change', async function () {
        const floorId = this.value;
        const option = this.options[this.selectedIndex];
        
        if (!floorId) {
            renderPlaceholder(floorMapContainer);
            return;
        }

        try {
            renderLoading(floorMapContainer);
            const rooms = await fetchRoomsByFloor(floorId);
            renderFloorMap(floorMapContainer, rooms, option.dataset.level);
        } catch (error) {
            renderError(floorMapContainer, error.message);
        }
    });

    // Handle pre-selection (Flask injection)
    if (typeof window.preSelectedFloor !== 'undefined' && window.preSelectedFloor) {
        floorSelect.value = window.preSelectedFloor;
        floorSelect.dispatchEvent(new Event('change'));
    }
}

/**
 * Initialize maintenance report form submission.
 */
function initializeReportForm() {
    const reportForm = document.getElementById('reportForm');
    if (!reportForm) return;

    reportForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const submitBtn = document.getElementById('submitBtn');
        const formData = new FormData(reportForm);

        try {
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<i class="bi bi-hourglass-split me-2"></i>Submitting...';
            }

            const response = await fetch(reportForm.action, {
                method: 'POST',
                body: formData,
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            });

            const data = await response.json();

            if (data.success) {
                if (window.showSuccessModal) window.showSuccessModal(data.ticket_id);
                reportForm.reset();
                resetRoomSelection();
            } else {
                if (window.showErrors) window.showErrors(data.errors || [data.error]);
            }
        } catch (error) {
            console.error('Submission error:', error);
            if (window.showErrors) window.showErrors(['Project could not be submitted. Check network.']);
        } finally {
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = '<i class="bi bi-send me-2"></i>Submit Report';
            }
        }
    });
}

/**
 * Basic validation hooks.
 */
function initializeValidation() {
    const prnInput = document.getElementById('prn');
    if (prnInput) {
        prnInput.addEventListener('input', function() {
            this.value = this.value.replace(/[^0-9]/g, '');
        });
    }
}

// Visual Helpers

function renderPlaceholder(container) {
    container.innerHTML = `
        <div class="floor-map-placeholder">
            <i class="bi bi-building display-1 text-muted"></i>
            <p class="mt-3">Select a floor to view the interactive map</p>
        </div>
    `;
}

function renderLoading(container) {
    container.innerHTML = `
        <div class="floor-map-placeholder">
            <div class="spinner-border text-primary" role="status"></div>
            <p class="mt-3">Loading floor plan...</p>
        </div>
    `;
}

function renderError(container, message) {
    container.innerHTML = `
        <div class="floor-map-placeholder">
            <i class="bi bi-exclamation-triangle display-1 text-danger"></i>
            <p class="mt-3">Error: ${message}</p>
        </div>
    `;
}
