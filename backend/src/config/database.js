import path from 'node:path';
import pg from 'pg';
import dotenv from 'dotenv';

const envPath = path.resolve(process.cwd(), '..', '.env');
dotenv.config({ path: envPath });

const { Pool } = pg;

const pool = new Pool({
  host: process.env.POSTGRES_HOST,
  port: Number(process.env.POSTGRES_PORT || 5432),
  database: process.env.POSTGRES_DB,
  user: process.env.POSTGRES_USER,
  password: String(process.env.POSTGRES_PASSWORD || ''),
  max: 10,
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 5000,
});

export async function testDatabaseConnection() {
  const client = await pool.connect();
  try {
    const result = await client.query('SELECT NOW()');
    return result.rows[0];
  } finally {
    client.release();
  }
}

export const db = {
  query: (text, params) => pool.query(text, params),
  getPool: () => pool,
};

export default db;
