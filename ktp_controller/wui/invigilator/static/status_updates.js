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

  function connect() {
    const sock = new WebSocket(wsUrl);
    sock.addEventListener("open", () => {
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
      const overlay = document.getElementById("connection-lost-overlay");
      if (overlay !== null) {
        overlay.classList.add("is-visible");
      }
      setTimeout(connect, reconnectDelay);
      reconnectDelay = Math.min(reconnectDelay * 2, maxReconnectDelay);
    });
    sock.addEventListener("error", () => sock.close());
  }

  connect();
})();
