(function () {
  // Animation timeline, restarted from "elapsed = 0" on every refresh
  // ("beat"), as a pure function of time-since-last-refresh:
  //   0s -> 1s:  quick charge from wherever it currently is up to full
  //              size/color
  //   1s -> 30s: slow discharge to 50% size / lightest green
  //   30s -> 35s: size stays at 50%, color fades from light green to red
  //   35s+:      stays red until the next beat
  //
  // Driven by our own requestAnimationFrame loop (not a CSS transition
  // or keyframes), and restricted to transform/opacity: analyzing a
  // screen recording frame-by-frame showed Firefox measurably dropping
  // repaints under continuous background-color writes (far more
  // duplicate frames than Chrome), since that's a repaint-triggering
  // property in both engines, just a cheaper one for Chrome to keep up
  // with. transform/opacity are compositor-only in both, so "color" is
  // done by crossfading two fixed-color overlay circles (see app.css)
  // instead of literally animating background-color.
  const CHARGE_MS = 1000;
  const DISCHARGE_END_MS = 30000;
  const ALARM_END_MS = 35000;

  const SCALE_FULL = 1;
  const SCALE_MIN = 0.5;
  const LIGHTEN_MAX = 0.82; // overlay opacity at "fully discharged" (lightest green)

  const FULL_STATE = { scale: SCALE_FULL, lighten: 0, alarm: 0 };

  let anchor = Date.now();
  let lastState = FULL_STATE;
  let rechargeFrom = lastState;
  let rafId = null;

  function els() {
    const root = document.getElementById("page-refreshed-status");
    if (root === null) {
      return null;
    }
    const lighten = root.querySelector(".page-refreshed-beacon-lighten");
    const alarm = root.querySelector(".page-refreshed-beacon-alarm");
    if (lighten === null || alarm === null) {
      return null;
    }
    return { root, lighten, alarm };
  }

  function lerp(a, b, t) {
    return a + (b - a) * t;
  }

  // Smoothstep: eases the 0->1 blend so the charge "snaps" into place
  // instead of moving at a constant rate.
  function smoothstep(t) {
    return t * t * (3 - 2 * t);
  }

  // Pure function of time elapsed since a (hypothetical) instant
  // charge, used both to render the steady state and as the charge
  // phase's target.
  function steadyStateAtElapsed(elapsedMs) {
    if (elapsedMs < DISCHARGE_END_MS) {
      const t = (elapsedMs - CHARGE_MS) / (DISCHARGE_END_MS - CHARGE_MS);
      return { scale: lerp(SCALE_FULL, SCALE_MIN, t), lighten: lerp(0, LIGHTEN_MAX, t), alarm: 0 };
    }
    if (elapsedMs < ALARM_END_MS) {
      const t = (elapsedMs - DISCHARGE_END_MS) / (ALARM_END_MS - DISCHARGE_END_MS);
      return { scale: SCALE_MIN, lighten: LIGHTEN_MAX, alarm: lerp(0, 1, t) };
    }
    return { scale: SCALE_MIN, lighten: LIGHTEN_MAX, alarm: 1 };
  }

  function tick() {
    const el = els();
    if (el === null) {
      // This script runs in <head>, before <body> (and
      // #page-refreshed-status) exist yet, so keep polling until the
      // element shows up.
      rafId = requestAnimationFrame(tick);
      return;
    }

    const elapsedMs = Math.max(0, Date.now() - anchor);
    let state;
    if (elapsedMs < CHARGE_MS) {
      const t = smoothstep(elapsedMs / CHARGE_MS);
      state = {
        scale: lerp(rechargeFrom.scale, FULL_STATE.scale, t),
        lighten: lerp(rechargeFrom.lighten, FULL_STATE.lighten, t),
        alarm: lerp(rechargeFrom.alarm, FULL_STATE.alarm, t),
      };
    } else {
      state = steadyStateAtElapsed(elapsedMs);
    }

    lastState = state;
    el.root.style.transform = `scale(${state.scale})`;
    el.lighten.style.opacity = state.lighten;
    el.alarm.style.opacity = state.alarm;

    if (elapsedMs < ALARM_END_MS) {
      rafId = requestAnimationFrame(tick);
    } else {
      // Steady red: nothing left to animate until the next beat().
      rafId = null;
    }
  }

  function ensureAnimating() {
    if (rafId === null) {
      rafId = requestAnimationFrame(tick);
    }
  }

  function beat() {
    rechargeFrom = lastState;
    anchor = Date.now();
    ensureAnimating();
  }

  function updateTitle() {
    const root = document.getElementById("page-refreshed-status");
    if (root === null) {
      return;
    }
    const seconds = Math.max(0, Math.round((Date.now() - anchor) / 1000));
    const template = seconds === 1 ? root.dataset.templateOne : root.dataset.templateOther;
    root.title = template.replace("{n}", seconds);
  }

  document.addEventListener("htmx:afterRequest", beat);

  ensureAnimating();
  updateTitle();
  setInterval(updateTitle, 1000);
})();
