import pg from 'pg';

const { Pool } = pg;

const pool = new Pool({
  host: process.env.POSTGRES_HOST || 'postgres',
  port: Number(process.env.POSTGRES_PORT || 5432),
  database: process.env.POSTGRES_DB || 'orion',
  user: process.env.POSTGRES_USER || 'postgres',
  password: String(process.env.POSTGRES_PASSWORD || ''),
  max: 10,
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 5000,
});

export async function testDatabaseConnection() {
  const client = await pool.connect();

  try {
    const result = await client.query(`
      SELECT
        current_database(),
        current_schema()
    `);

    console.log('Base de datos:', result.rows[0]);

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