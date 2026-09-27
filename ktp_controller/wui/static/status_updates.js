(function () {
  const scheme = location.protocol === "https:" ? "wss" : "ws";
  const wsUrl = `${scheme}://${location.host}/invigilator/ws`;
  let reconnectDelay = 1000;
  const maxReconnectDelay = 8000;
  // Set once the socket has disconnected at least once. Distinguishes
  // a reconnect from the initial page-load connection: a reconnect
  // likely means the app server restarted (new code available), so
  // reload instead of silently resuming.
  let hasDisconnected = false;
  // Showing the overlay is delayed and cancellable: a normal page
  // navigation (e.g. the locale switcher's form submit) also closes
  // the socket as the page unloads, which would otherwise flash the
  // overlay for one frame right before the new page loads. Delaying
  // it lets that kind of momentary close resolve (page gone, or
  // socket back open) before the overlay ever gets a chance to paint.
  const overlayShowDelayMs = 500;
  let overlayShowTimer = null;
  let lostAt = null;
  // Set once the page starts navigating away (logout, locale switch,
  // or this script's own login-redirect/reload below), so a retry
  // that was already scheduled doesn't try to open a new socket or
  // fetch in a document that's being torn down.
  let isUnloading = false;
  window.addEventListener("pagehide", () => {
    isUnloading = true;
  });

  function connect() {
    if (isUnloading) {
      return;
    }
    const sock = new WebSocket(wsUrl);
    sock.addEventListener("open", () => {
      if (overlayShowTimer !== null) {
        clearTimeout(overlayShowTimer);
        overlayShowTimer = null;
      }
      if (hasDisconnected) {
        location.reload();
        return;
      }
      reconnectDelay = 1000;
    });
    sock.addEventListener("message", () => {
      document.body.dispatchEvent(new Event("student-list-update"));
    });
    sock.addEventListener("close", () => {
      hasDisconnected = true;
      if (lostAt === null) {
        lostAt = new Date();
      }
      overlayShowTimer = setTimeout(() => {
        const overlay = document.getElementById("connection-lost-overlay");
        if (overlay !== null) {
          const timestamp = document.getElementById("connection-lost-timestamp");
          if (timestamp !== null) {
            timestamp.textContent = lostAt.toLocaleString(document.documentElement.lang, {
              dateStyle: "short",
              timeStyle: "medium",
            });
          }
          overlay.classList.add("is-visible");
        }
      }, overlayShowDelayMs);
      setTimeout(reconnect, reconnectDelay);
      reconnectDelay = Math.min(reconnectDelay * 2, maxReconnectDelay);
    });
    sock.addEventListener("error", () => sock.close());
  }

  // A closed websocket carries no reliable reason: a real network outage
  // and a rejected handshake (e.g. the session expired while disconnected)
  // both surface identically as a generic abnormal closure. Plain HTTP
  // doesn't have that limitation, so before retrying the socket, probe
  // the page itself and let the server's existing auth handling (login
  // redirect / 403) answer the question directly.
  async function reconnect() {
    if (isUnloading) {
      return;
    }
    try {
      const res = await fetch(location.pathname);
      if (res.redirected && new URL(res.url).pathname === "/login") {
        location.href = res.url;
        return;
      }
      if (res.status === 403) {
        location.reload();
        return;
      }
    } catch {
      // Real network/server outage: fall through and keep retrying the
      // websocket as before.
    }
    connect();
  }

  connect();
})();
