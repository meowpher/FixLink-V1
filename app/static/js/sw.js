self.addEventListener('push', function(event) {
    if (event.data) {
        const data = event.data.json();
        const options = {
            body: data.body,
            icon: '/static/images/logo.png', // Assuming a logo exists
            badge: '/static/images/badge.png', // Or similar transparent icon
            vibrate: [100, 50, 100],
            data: {
                dateOfArrival: Date.now(),
                primaryKey: '2'
            },
            actions: [
                {action: 'explore', title: 'View Details',
                    icon: '/static/images/checkmark.png'},
                {action: 'close', title: 'Dismiss',
                    icon: '/static/images/xmark.png'},
            ]
        };
        event.waitUntil(
            self.registration.showNotification(data.title || 'FixLink Update', options)
        );
    }
});

self.addEventListener('notificationclick', function(event) {
    console.log('[Service Worker] Notification click Received.');
    event.notification.close();

    if (event.action === 'explore') {
        // Open the app or a specific URL
        event.waitUntil(
            clients.openWindow('/professional')
        );
    }
});
