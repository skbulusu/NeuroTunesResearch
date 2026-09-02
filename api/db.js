// ====================================================================
// server/db.js  —  Shared MySQL access layer for the NeuroTunes platform
// --------------------------------------------------------------------
// Provides a single connection pool + a promise-based query() helper that
// the NeuroTunes routers (legacy /api/neurotunes and the new /api/v1)
// use for durable session/generation/feedback persistence.
//
// This module is ADDITIVE. It reads the exact same environment variables
// that server/app.js already uses (dbHost / dbUsername / dbPWD / dbName),
// so it works unchanged inside the existing docker-compose "web-core"
// machine where netrai-server talks to the netrai-db (MySQL 8.3) container.
//
// It intentionally does NOT alter the pool created in app.js — running a
// second small pool from the same router is safe and avoids touching the
// patent-/production-critical bootstrap code in app.js.
// ====================================================================

import mysql from 'mysql2';

const dbConfig = {
  host: process.env.dbHost,
  user: process.env.dbUsername,
  password: process.env.dbPWD,
  database: process.env.dbName,
};

// A small, dedicated pool for the NeuroTunes research-platform routers.
const pool = mysql.createPool({
  ...dbConfig,
  connectionLimit: 5,
  waitForConnections: true,
  queueLimit: 0,
});

/**
 * Promise-based query helper.
 * @param {string} sql - parameterised SQL (use ? placeholders)
 * @param {Array}  params - bound parameters
 * @returns {Promise<Array>} resolved rows
 */
export function query(sql, params = []) {
  return new Promise((resolve, reject) => {
    pool.query(sql, params, (err, results) => {
      if (err) reject(err);
      else resolve(results);
    });
  });
}

/**
 * Returns true when a live DB connection can be obtained.
 * Used by health checks and to let routers degrade gracefully
 * (fall back to in-memory) when the DB is momentarily unavailable.
 */
export async function isDbHealthy() {
  try {
    await query('SELECT 1');
    return true;
  } catch (_e) {
    return false;
  }
}

export { pool };
export default { query, isDbHealthy, pool };
