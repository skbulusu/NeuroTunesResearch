// ====================================================================
// server/scripts/create_api_key.js
// --------------------------------------------------------------------
// Create a NeuroTunes API key for the /api/v1 programmatic API.
//
// Usage (run from the server/ directory, with DB env vars set exactly as
// the server uses them: dbHost, dbUsername, dbPWD, dbName):
//
//   node scripts/create_api_key.js "MIT Music & Health Lab" lab@mit.edu
//   node scripts/create_api_key.js "Quick test key"
//   node scripts/create_api_key.js "High-volume partner" x@y.org --rate 300 --scopes generate,feedback,sessions,read
//
// The full secret key is printed ONCE. Only its SHA-256 hash is stored.
// ====================================================================

import { generateApiKey } from '../apiAuth.js';
import { query as dbQuery } from '../db.js';

function parseArgs(argv) {
  const args = argv.slice(2);
  const positional = [];
  const opts = { rate: 60, scopes: 'generate,feedback,sessions,read' };
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--rate') { opts.rate = parseInt(args[++i], 10) || 60; }
    else if (args[i] === '--scopes') { opts.scopes = args[++i] || opts.scopes; }
    else positional.push(args[i]);
  }
  opts.name = positional[0] || 'Unnamed key';
  opts.email = positional[1] || null;
  return opts;
}

async function main() {
  const opts = parseArgs(process.argv);
  const { key, hash, prefix } = generateApiKey();

  try {
    await dbQuery(
      `INSERT INTO neurotunes_api_keys
         (api_key_hash, key_prefix, name, owner_email, scopes, rate_limit_per_min, active)
       VALUES (?, ?, ?, ?, ?, ?, 1)`,
      [hash, prefix, opts.name, opts.email, opts.scopes, opts.rate]
    );
  } catch (e) {
    console.error('\nFailed to create API key:', e.message);
    console.error('Make sure the neurotunes_api_keys table exists:');
    console.error('  mysql -u <user> -p netraidb < dbScripts/neurotunes_api_keys.sql\n');
    process.exit(1);
  }

  console.log('\n============================================================');
  console.log(' NeuroTunes API key created');
  console.log('============================================================');
  console.log(` Name          : ${opts.name}`);
  console.log(` Owner email   : ${opts.email || '(none)'}`);
  console.log(` Prefix        : ${prefix}`);
  console.log(` Scopes        : ${opts.scopes}`);
  console.log(` Rate limit    : ${opts.rate} req/min`);
  console.log('------------------------------------------------------------');
  console.log(' API KEY (shown ONCE — store it securely):');
  console.log(`   ${key}`);
  console.log('------------------------------------------------------------');
  console.log(' Use it as a header:');
  console.log(`   X-API-Key: ${key}`);
  console.log('============================================================\n');
  process.exit(0);
}

main();
