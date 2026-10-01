import pg from 'pg';

const { Pool } = pg;

const chatPool = new Pool({
  host: process.env.POSTGRESCHAT_HOST,
  port: Number(process.env.POSTGRESCHAT_PORT || 5432),
  database: process.env.POSTGRESCHAT_DB,
  user: process.env.POSTGRESCHAT_USER,
  password: process.env.POSTGRESCHAT_PASSWORD,
});

chatPool.on('error', (error) => {
  console.error('Error PostgreSQL chats:', error.message);
});

export default chatPool;
