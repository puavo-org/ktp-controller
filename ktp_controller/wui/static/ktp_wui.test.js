"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");

global.window = global;
global.document = { documentElement: { lang: "en" } };
require("./ktp_wui.js");
const { KtpWui } = global;

test("pick uses templateOne for n === 1", () => {
  assert.equal(KtpWui.pick(1, "{n} minute", "{n} minutes"), "1 minute");
});

test("pick uses templateOther for n !== 1", () => {
  assert.equal(KtpWui.pick(0, "{n} minute", "{n} minutes"), "0 minutes");
  assert.equal(KtpWui.pick(2, "{n} minute", "{n} minutes"), "2 minutes");
});

function fakeElement() {
  const attrs = new Map();
  return {
    setAttribute(name, value) {
      attrs.set(name, String(value));
    },
    removeAttribute(name) {
      attrs.delete(name);
    },
    hasAttribute(name) {
      return attrs.has(name);
    },
  };
}

test("setHidden sets the hidden attribute when hiding", () => {
  const el = fakeElement();
  KtpWui.setHidden(el, true);
  assert.equal(el.hasAttribute("hidden"), true);
});

test("setHidden removes the hidden attribute when showing", () => {
  const el = fakeElement();
  el.setAttribute("hidden", "");
  KtpWui.setHidden(el, false);
  assert.equal(el.hasAttribute("hidden"), false);
});

test("formatLongDateTime returns a non-empty string containing the year", () => {
  const formatted = KtpWui.formatLongDateTime(new Date("2026-03-05T12:00:00Z"));
  assert.ok(formatted.length > 0);
  assert.match(formatted, /2026/);
});
