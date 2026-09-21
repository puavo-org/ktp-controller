(function () {
  const scheme = location.protocol === "https:" ? "wss" : "ws";
  const wsUrl = `${scheme}://${location.host}/invigilator/ws`;
  let reconnectDelay = 1000;
  const maxReconnectDelay = 16000;

  function connect() {
    const sock = new WebSocket(wsUrl);
    sock.addEventListener("open", () => {
      reconnectDelay = 1000;
    });
    sock.addEventListener("message", () => {
      document.body.dispatchEvent(new Event("student-list-update"));
    });
    sock.addEventListener("close", () => {
      setTimeout(connect, reconnectDelay);
      reconnectDelay = Math.min(reconnectDelay * 2, maxReconnectDelay);
    });
    sock.addEventListener("error", () => sock.close());
  }

  connect();
})();
