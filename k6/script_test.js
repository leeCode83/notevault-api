/**
 * ============================================================
 *  Note Vault API — k6 Performance Test Script
 * ============================================================
 *
 *  Supports three test scenarios via JSON config (--config flag):
 *    • Load Test   → validates normal, sustained traffic behavior
 *    • Stress Test → finds the system's breaking point under heavy load
 *    • Spike Test  → simulates sudden, extreme traffic bursts
 *
 *  Usage:
 *    k6 run --config load_config.json   script_test.js
 *    k6 run --config stress_config.json script_test.js
 *    k6 run --config spike_config.json  script_test.js
 *
 *  Environment variables (can also be set inside each JSON config):
 *    BASE_URL   — API base URL  (default: http://localhost:8000)
 *    TEST_TYPE  — label for logs (default: load)
 * ============================================================
 */

import http from "k6/http";
import { check, group, sleep } from "k6";
import { Counter, Rate, Trend } from "k6/metrics";
import { randomString, randomIntBetween } from "https://jslib.k6.io/k6-utils/1.4.0/index.js";

// ─── Runtime config ──────────────────────────────────────────────────────────
const BASE_URL  = __ENV.BASE_URL  || "http://localhost:8000";
const TEST_TYPE = __ENV.TEST_TYPE || "load";

// ─── Custom Metrics ──────────────────────────────────────────────────────────
const loginFailures      = new Counter("custom_login_failures");
const noteCreateFailures = new Counter("custom_note_create_failures");
const noteReadFailures   = new Counter("custom_note_read_failures");
const noteUpdateFailures = new Counter("custom_note_update_failures");
const errorRate          = new Rate("custom_error_rate");
const loginDuration      = new Trend("custom_login_duration_ms",       true);
const createNoteDuration = new Trend("custom_create_note_duration_ms", true);
const getAllNotesDuration = new Trend("custom_get_all_notes_duration_ms", true);

// ─── Seed data ───────────────────────────────────────────────────────────────
const NOTE_TITLES = [
  "Meeting Notes Q1 2025",
  "Project Alpha Kickoff",
  "Weekly Retrospective",
  "Product Roadmap Ideas",
  "Bug Triage Session",
  "Tech Debt Backlog Review",
  "Performance Review Notes",
  "Architecture Decision Record",
  "Stakeholder Feedback Summary",
  "Deployment Runbook",
];

const NOTE_CONTENTS = [
  "Discussed sprint goals and blockers. Team aligned on delivery timeline for the next two weeks.",
  "Outlined key milestones and deliverables for the new project. Assigned owners for each task.",
  "Team velocity improved by 12%. Main blocker: external dependency on third-party payment API.",
  "Potential features for H2: AI-assisted search, offline mode, and real-time collaboration support.",
  "Critical bugs: #402 (data loss on sync) and #417 (auth token expiry). P0 fix required this week.",
  "Identified 23 items of technical debt. Suggest allocating 20% of sprint capacity to address them.",
  "Annual performance review cycle starts in April. Goals should be updated in the HR portal ahead of time.",
  "ADR-012: Chose PostgreSQL over MongoDB due to relational data requirements and ACID compliance guarantees.",
  "Feedback from stakeholders: prioritise mobile UX, reduce average page load time below 2 seconds.",
  "Pre-deployment checklist: smoke tests passed, database migrations applied, feature flags configured.",
];

// ─── Default options (overridden at runtime by --config flag) ─────────────────
export const options = {
  // Fallback thresholds — each JSON config also declares its own thresholds.
  // These apply when running without a --config flag.
  thresholds: {
    http_req_duration:              ["p(95)<2000"],
    http_req_failed:                ["rate<0.05"],
    custom_error_rate:              ["rate<0.05"],
    custom_login_duration_ms:       ["p(95)<1500"],
    custom_create_note_duration_ms: ["p(95)<2000"],
    custom_get_all_notes_duration_ms: ["p(95)<1000"],
  },
};

// ─── Helpers ─────────────────────────────────────────────────────────────────

/** Register a unique test user; returns { email, password } or null on failure. */
function registerUser() {
  const email    = `k6_${randomString(10)}@perf-test.dev`;
  const password = `Str0ng!Pass_${randomString(6)}`;

  const res = http.post(
    `${BASE_URL}/auth/register`,
    JSON.stringify({ email, password }),
    { headers: { "Content-Type": "application/json" } }
  );

  if (res.status !== 200 && res.status !== 201) {
    console.warn(`[Register] FAILED → ${res.status}: ${res.body}`);
    return null;
  }
  return { email, password };
}

/** Login with form-encoded credentials; returns JWT token or null on failure. */
function login(credentials) {
  const start = Date.now();

  const res = http.post(
    `${BASE_URL}/auth/login`,
    { username: credentials.email, password: credentials.password },
    { headers: { "Content-Type": "application/x-www-form-urlencoded" } }
  );

  loginDuration.add(Date.now() - start);

  const ok = check(res, {
    "[Login] HTTP 200":         (r) => r.status === 200,
    "[Login] has access_token": (r) => {
      try { return !!JSON.parse(r.body).access_token; }
      catch { return false; }
    },
  });

  errorRate.add(!ok);
  if (!ok) { loginFailures.add(1); return null; }

  return JSON.parse(res.body).access_token;
}

/** Create a note with a random title/content; returns the new note id or null. */
function createNote(token) {
  const title   = NOTE_TITLES[randomIntBetween(0, NOTE_TITLES.length - 1)];
  const content = NOTE_CONTENTS[randomIntBetween(0, NOTE_CONTENTS.length - 1)];
  const start   = Date.now();

  const res = http.post(
    `${BASE_URL}/note/create`,
    JSON.stringify({ title, content }),
    { headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` } }
  );

  createNoteDuration.add(Date.now() - start);

  const ok = check(res, {
    "[Create Note] HTTP 200/201": (r) => r.status === 200 || r.status === 201,
  });

  errorRate.add(!ok);
  if (!ok) { noteCreateFailures.add(1); return null; }

  try {
    const body = JSON.parse(res.body);
    // Handle different Supabase response shapes
    if (Array.isArray(body)) return body[0]?.id ?? null;
    return body?.id ?? body?.data?.[0]?.id ?? null;
  } catch { return null; }
}

/** Fetch all notes (public endpoint). */
function getAllNotes() {
  const start = Date.now();
  const res   = http.get(`${BASE_URL}/note/`);
  getAllNotesDuration.add(Date.now() - start);

  const ok = check(res, {
    "[Get All Notes] HTTP 200":        (r) => r.status === 200,
    "[Get All Notes] body is an array": (r) => {
      try { return Array.isArray(JSON.parse(r.body)); }
      catch { return false; }
    },
  });

  errorRate.add(!ok);
  if (!ok) noteReadFailures.add(1);
}

/** Partially update a note's content. */
function updateNote(token, noteId) {
  const newContent = `[k6 update] ${new Date().toISOString()} — ${randomString(16)}`;

  const res = http.patch(
    `${BASE_URL}/note/update`,
    JSON.stringify({ id: noteId, content: newContent }),
    { headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` } }
  );

  const ok = check(res, {
    "[Update Note] HTTP 200": (r) => r.status === 200,
  });

  errorRate.add(!ok);
  if (!ok) noteUpdateFailures.add(1);
}

// ─── Setup ───────────────────────────────────────────────────────────────────

export function setup() {
  console.log("============================================================");
  console.log(` Note Vault k6 Test  |  Type: ${TEST_TYPE.toUpperCase()}`);
  console.log(` Target: ${BASE_URL}`);
  console.log("============================================================");
  return {};
}

// ─── Main VU function ────────────────────────────────────────────────────────
/**
 * Realistic user journey (one full session per iteration):
 *   1. Register account
 *   2. Login → obtain JWT
 *   3. Browse public notes
 *   4. Create a personal note
 *   5. Update that note
 *   6. Browse public notes again (simulate scroll / refresh)
 */
export default function (_data) {
  // --- Step 1: Register ---
  const credentials = registerUser();
  if (!credentials) {
    sleep(randomIntBetween(1, 3));
    return;
  }
  sleep(randomIntBetween(1, 2)); // simulate typing / navigation delay

  group("Auth — Login", function () {
    const token = login(credentials);
    if (!token) { sleep(2); return; }

    sleep(randomIntBetween(1, 2)); // page rendering think-time

    group("Notes — Browse All (GET)", function () {
      getAllNotes();
      sleep(randomIntBetween(2, 4)); // user reads the list
    });

    group("Notes — Create (POST)", function () {
      const noteId = createNote(token);
      sleep(randomIntBetween(1, 2));

      if (noteId) {
        group("Notes — Update (PATCH)", function () {
          updateNote(token, noteId);
          sleep(randomIntBetween(1, 2));
        });
      }
    });

    group("Notes — Browse Again (GET)", function () {
      // Simulates a user refreshing or navigating away and back
      getAllNotes();
      sleep(randomIntBetween(1, 3));
    });
  });

  // Idle time between user sessions (realistic think-time)
  sleep(randomIntBetween(1, 4));
}

// ─── Teardown ────────────────────────────────────────────────────────────────

export function teardown(_data) {
  console.log("============================================================");
  console.log(" Test completed. Review the k6 summary report above.");
  console.log("============================================================");
}
