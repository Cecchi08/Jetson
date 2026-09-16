import pg from 'pg';

const { Pool } = pg;

if (!process.env.DB_URL) {
  throw new Error('DB_URL no está configurada');
}

const pool = new Pool({
  connectionString: process.env.DB_URL,
  ssl: {
    rejectUnauthorized: false,
  },
  max: 10,
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 15000,
});

export async function testDatabaseConnection() {
  const client = await pool.connect();

  try {
    const result = await client.query(`
      SELECT
        current_database(),
        current_schema(),
        current_user
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
