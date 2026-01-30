// MetaPM Service Worker with offline support
const CACHE_NAME = 'metapm-v1';
const API_CACHE = 'metapm-api-v1';
const STATIC_ASSETS = [
    '/static/capture.html',
    '/static/manifest.json',
    '/static/dashboard.html',
    '/static/js/offline-data.js'
];

// Install event - cache static assets
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => cache.addAll(STATIC_ASSETS))
            .then(() => self.skipWaiting())
    );
});

// Activate event - clean old caches
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then(keys => {
            return Promise.all(
                keys.filter(key => key !== CACHE_NAME && key !== API_CACHE)
                    .map(key => caches.delete(key))
            );
        }).then(() => self.clients.claim())
    );
});

// Fetch event - handle offline scenarios
self.addEventListener('fetch', (event) => {
    const url = new URL(event.request.url);
    
    // Skip non-GET requests (they go to network, but cache GET responses later)
    if (event.request.method !== 'GET') {
        return;
    }
    
    // Static assets - cache first
    if (url.pathname.startsWith('/static/')) {
        event.respondWith(
            caches.match(event.request)
                .then(response => {
                    if (response) return response;
                    return fetch(event.request)
                        .then(fetchResponse => {
                            if (fetchResponse.status === 200) {
                                const responseClone = fetchResponse.clone();
                                caches.open(CACHE_NAME)
                                    .then(cache => cache.put(event.request, responseClone));
                            }
                            return fetchResponse;
                        });
                })
                .catch(() => caches.match('/static/dashboard.html'))
        );
        return;
    }
    
    // API requests - network first, cache as fallback
    if (url.pathname.startsWith('/api/')) {
        event.respondWith(
            fetch(event.request)
                .then(response => {
                    if (response.status === 200) {
                        const responseClone = response.clone();
                        caches.open(API_CACHE)
                            .then(cache => cache.put(event.request, responseClone));
                    }
                    return response;
                })
                .catch(() => {
                    // Return cached response if available
                    return caches.match(event.request)
                        .then(response => {
                            if (response) {
                                // Mark as stale
                                const headers = new Headers(response.headers);
                                headers.append('X-From-Cache', 'true');
                                return new Response(response.body, {
                                    status: response.status,
                                    statusText: response.statusText,
                                    headers: headers
                                });
                            }
                            return new Response(JSON.stringify({
                                error: 'Offline',
                                message: 'Data not available offline'
                            }), {
                                status: 503,
                                statusText: 'Service Unavailable',
                                headers: { 'Content-Type': 'application/json' }
                            });
                        });
                })
        );
        return;
    }
    
    // Default - network first
    event.respondWith(
        fetch(event.request)
            .catch(() => caches.match(event.request))
    );
});

