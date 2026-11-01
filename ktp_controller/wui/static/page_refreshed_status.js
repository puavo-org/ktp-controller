(function () {
  // Animation timeline, restarted from "elapsed = 0" on every refresh
  // ("beat"), as a pure function of time-since-last-refresh:
  //   0s -> 1s:  quick charge from wherever it currently is up to full
  //              size/color
  //   1s -> 30s: slow discharge to 50% size / lightest green
  //   30s -> 35s: size stays at 50%, color fades from light green to red
  //   35s+:      stays red until the next beat
  //
  // Driven by our own requestAnimationFrame loop (not a CSS transition):
  // letting the browser's transition engine tween background-color over
  // a long (29s) duration renders visibly coarser in Firefox than in
  // Chrome, since each engine is free to pick its own internal update
  // rate for that. Computing and writing the exact numeric style every
  // frame ourselves renders identically smoothly everywhere.
  const CHARGE_MS = 1000;
  const DISCHARGE_END_MS = 30000;
  const ALARM_END_MS = 35000;

  const SCALE_FULL = 1;
  const SCALE_MIN = 0.5;
  const COLOR_FULL = [22, 163, 74]; // #16a34a
  const COLOR_LIGHT = [220, 252, 231]; // #dcfce7
  const COLOR_ALARM = [220, 38, 38]; // #dc2626

  let anchor = Date.now();
  let lastState = { scale: SCALE_FULL, color: COLOR_FULL };
  let rechargeFrom = lastState;
  let rafId = null;

  function statusEl() {
    return document.getElementById("page-refreshed-status");
  }

  function lerp(a, b, t) {
    return a + (b - a) * t;
  }

  function lerpColor(c1, c2, t) {
    return [lerp(c1[0], c2[0], t), lerp(c1[1], c2[1], t), lerp(c1[2], c2[2], t)];
  }

  function colorToCss(c) {
    return `rgb(${Math.round(c[0])}, ${Math.round(c[1])}, ${Math.round(c[2])})`;
  }

  // Smoothstep: eases the 0->1 blend so the charge "snaps" into place
  // instead of moving at a constant rate.
  function smoothstep(t) {
    return t * t * (3 - 2 * t);
  }

  // Pure function of time elapsed since a (hypothetical) instant charge,
  // used both to render the steady state and as the charge phase's
  // target.
  function steadyStateAtElapsed(elapsedMs) {
    if (elapsedMs < DISCHARGE_END_MS) {
      const t = (elapsedMs - CHARGE_MS) / (DISCHARGE_END_MS - CHARGE_MS);
      return { scale: lerp(SCALE_FULL, SCALE_MIN, t), color: lerpColor(COLOR_FULL, COLOR_LIGHT, t) };
    }
    if (elapsedMs < ALARM_END_MS) {
      const t = (elapsedMs - DISCHARGE_END_MS) / (ALARM_END_MS - DISCHARGE_END_MS);
      return { scale: SCALE_MIN, color: lerpColor(COLOR_LIGHT, COLOR_ALARM, t) };
    }
    return { scale: SCALE_MIN, color: COLOR_ALARM };
  }

  function tick() {
    const el = statusEl();
    if (el === null) {
      // This script runs in <head>, before <body> (and #page-refreshed-status)
      // exist yet, so keep polling until the element shows up.
      rafId = requestAnimationFrame(tick);
      return;
    }

    const elapsedMs = Math.max(0, Date.now() - anchor);
    let state;
    if (elapsedMs < CHARGE_MS) {
      const t = smoothstep(elapsedMs / CHARGE_MS);
      state = {
        scale: lerp(rechargeFrom.scale, SCALE_FULL, t),
        color: lerpColor(rechargeFrom.color, COLOR_FULL, t),
      };
    } else {
      state = steadyStateAtElapsed(elapsedMs);
    }

    lastState = state;
    el.style.transform = `scale(${state.scale})`;
    el.style.backgroundColor = colorToCss(state.color);

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
    const el = statusEl();
    if (el === null) {
      return;
    }
    const seconds = Math.max(0, Math.round((Date.now() - anchor) / 1000));
    const template = seconds === 1 ? el.dataset.templateOne : el.dataset.templateOther;
    el.title = template.replace("{n}", seconds);
  }

  document.addEventListener("htmx:afterRequest", beat);

  ensureAnimating();
  updateTitle();
  setInterval(updateTitle, 1000);
})();
