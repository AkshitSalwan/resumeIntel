import { Pool } from 'pg'

const globalForDb = globalThis as unknown as { resumeIntelPool?: Pool }

const databaseUrl = process.env.DATABASE_URL
if (!databaseUrl) {
  throw new Error('DATABASE_URL is required. Configure the Supabase PostgreSQL connection in .env.local.')
}

export const pool = globalForDb.resumeIntelPool ?? new Pool({
  connectionString: databaseUrl,
  max: 5,
  ssl: { rejectUnauthorized: false },
})

if (process.env.NODE_ENV !== 'production') globalForDb.resumeIntelPool = pool

export async function closePool() {
  await pool.end()
}
