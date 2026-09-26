(function () {
  const scheme = location.protocol === "https:" ? "wss" : "ws";
  const wsUrl = `${scheme}://${location.host}/invigilator/ws`;
  let reconnectDelay = 1000;
  const maxReconnectDelay = 16000;
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

  function connect() {
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
      setTimeout(connect, reconnectDelay);
      reconnectDelay = Math.min(reconnectDelay * 2, maxReconnectDelay);
    });
    sock.addEventListener("error", () => sock.close());
  }

  connect();
})();
