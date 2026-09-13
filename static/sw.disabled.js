const CACHE_NAME = 'lms-cache-v1';
const urlsToCache = [
    '/',
    '/portal',
    '/static/css/chat.css',
    '/static/js/call.js',
    '/static/js/chat.js',
    // add more static assets you want offline
];

self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME)
        .then(cache => cache.addAll(urlsToCache))
    );
});

self.addEventListener('fetch', event => {
    event.respondWith(
        caches.match(event.request)
        .then(response => response || fetch(event.request))
    );
});