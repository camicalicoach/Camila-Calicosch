const V = "cc-v2";
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) =>
  e.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== V).map((k) => caches.delete(k)))).then(() => self.clients.claim()))
);
self.addEventListener("fetch", (e) => {
  if (e.request.method !== "GET" || new URL(e.request.url).origin !== self.location.origin) return;
  const req = e.request.mode === "navigate" ? new Request(e.request.url) : e.request;
  e.respondWith(
    fetch(req, { cache: "no-store" })
      .then((r) => { const c = r.clone(); caches.open(V).then((x) => x.put(e.request, c)); return r; })
      .catch(() => caches.match(e.request))
  );
});
