const required = ['DATABASE_URL']
const missing = required.filter((name) => !process.env[name]?.trim())
if (missing.length > 0) {
  console.error(`Missing required database variables: ${missing.join(', ')}`)
  process.exitCode = 2
} else if (!process.env.SUPABASE_DB_CA_CERT?.trim() && !process.env.DATABASE_CA_CERT_PATH?.trim()) {
  console.error('Missing required database TLS variable: SUPABASE_DB_CA_CERT or DATABASE_CA_CERT_PATH')
  process.exitCode = 2
} else {
  try {
    const { pool } = await import('../lib/db.ts')
    await pool.query('select 1')
    console.log('PASS: PostgreSQL connection succeeded with certificate validation enabled.')
    await pool.end()
  } catch (error) {
    console.error(`FAIL: PostgreSQL connection failed with certificate validation enabled: ${error instanceof Error ? error.message : 'unknown error'}`)
    process.exitCode = 1
  }
}
