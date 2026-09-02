import app from './app.js';
import { testDatabaseConnection } from './config/database.js';

const port = process.env.BACKEND_PORT || 3000;
const host = '0.0.0.0';

async function startServer() {
  try {
    await testDatabaseConnection();
    console.log('Conexión a PostgreSQL verificada');
  } catch (error) {
    console.error('No se pudo conectar a PostgreSQL:', error.message);
  }

  app.listen(port, host, () => {
    console.log(`Backend escuchando en ${host}:${port}`);
  });
}

startServer();
