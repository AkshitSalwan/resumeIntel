import { Pool } from 'pg'
import { readFileSync } from 'node:fs'

const globalForDb = globalThis as unknown as { resumeIntelPool?: Pool }

const databaseUrl = process.env.DATABASE_URL
if (!databaseUrl) {
  throw new Error('DATABASE_URL is required. Configure the Supabase PostgreSQL connection in .env.local.')
}

function getDatabaseCa() {
  const certificate = process.env.SUPABASE_DB_CA_CERT?.trim()
  const certificatePath = process.env.DATABASE_CA_CERT_PATH?.trim()
  if (certificate && certificatePath) {
    throw new Error('Configure only one of SUPABASE_DB_CA_CERT or DATABASE_CA_CERT_PATH.')
  }
  if (certificate) return certificate.replace(/\\n/g, '\n')
  if (certificatePath) {
    try {
      return readFileSync(certificatePath, 'utf8')
    } catch (error) {
      throw new Error(`Could not read DATABASE_CA_CERT_PATH: ${error instanceof Error ? error.message : 'unknown error'}`)
    }
  }
  return undefined
}

const databaseCa = getDatabaseCa()

export const pool = globalForDb.resumeIntelPool ?? new Pool({
  connectionString: databaseUrl,
  max: 5,
  ssl: {
    ...(databaseCa ? { ca: databaseCa } : {}),
    rejectUnauthorized: true,
  },
})

if (process.env.NODE_ENV !== 'production') globalForDb.resumeIntelPool = pool

export async function closePool() {
  await pool.end()
}
