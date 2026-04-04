/**
 * Map API Module - Handles all backend communication for the interactive map.
 */

/**
 * Fetch rooms for a specific floor.
 * @param {number|string} floorId 
 * @returns {Promise<Array>} List of rooms
 */
export async function fetchRoomsByFloor(floorId) {
    const response = await fetch(`/api/rooms/floor/${floorId}`);
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    const result = await response.json();
    if (!result.success) throw new Error(result.error || 'Failed to load rooms');
    
    // The standardized API returns {success: true, data: {rooms: [...]}}
    return result.data.rooms || [];
}

/**
 * Fetch assets for a specific room.
 * @param {number|string} roomId 
 * @returns {Promise<Array>} List of assets
 */
export async function fetchAssetsByRoom(roomId) {
    const response = await fetch(`/api/assets/${roomId}`);
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    const result = await response.json();
    if (!result.success) throw new Error(result.error || 'Failed to load assets');
    
    return result.data.assets || result.data || [];
}

/**
 * Fetch buildings list.
 * @returns {Promise<Array>} List of buildings
 */
export async function fetchBuildings() {
    const response = await fetch('/api/buildings');
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    const result = await response.json();
    if (!result.success) throw new Error(result.error || 'Failed to load buildings');
    
    return result.data.buildings || result.data || [];
}
