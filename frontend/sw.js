self.addEventListener('push', function(event) {
    const data = event.data ? event.data.json() : {};
    const title = data.title || 'NJ Transit Alert';
    const options = {
        body: data.body || 'Train status update.',
        icon: '/static/icon.png',
        badge: '/static/icon.png'
    };
    event.waitUntil(
        self.registration.showNotification(title, options)
    );
});

self.addEventListener('notificationclick', function(event) {
    event.notification.close();
    event.waitUntil(
        clients.openWindow('/')
    );
});