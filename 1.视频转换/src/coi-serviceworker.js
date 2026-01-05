// Minimal COOP/COEP enabler via Service Worker (coi-serviceworker-like)
// Enables crossOriginIsolated so SharedArrayBuffer can be used on localhost/HTTPS.

self.addEventListener('install', function() { self.skipWaiting(); });
self.addEventListener('activate', function(event) {
  event.waitUntil(self.clients.claim());
});

function withIsolationHeaders(response) {
  const newHeaders = new Headers(response.headers);
  newHeaders.set('Cross-Origin-Opener-Policy', 'same-origin');
  newHeaders.set('Cross-Origin-Embedder-Policy', 'require-corp');
  if (!newHeaders.has('Cross-Origin-Resource-Policy')) {
    newHeaders.set('Cross-Origin-Resource-Policy', 'same-origin');
  }
  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers: newHeaders
  });
}

self.addEventListener('fetch', function(event) {
  const req = event.request;
  const url = new URL(req.url);

  // Only same-origin can be adjusted; cross-origin cannot be intercepted
  if (url.origin !== self.location.origin) return;

  // For navigations, ensure the main document also gets COOP/COEP
  if (req.mode === 'navigate') {
    event.respondWith(
      fetch(req, { cache: 'no-store' })
        .then(withIsolationHeaders)
        .catch(function() { return new Response('Offline', { status: 200, headers: { 'Content-Type': 'text/plain' } }); })
    );
    return;
  }

  // For same-origin subresources, add CORP and the isolation headers
  event.respondWith(
    fetch(req).then(withIsolationHeaders)
  );
});


