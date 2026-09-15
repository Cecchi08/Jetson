import bcrypt from 'bcrypt';
import db from '../config/database.js';
import { generateToken } from '../middleware/auth.js';

export async function register(req, res) {
  try {
    const { username, password } = req.body;

    // Validación básica
    if (!username || typeof username !== 'string' || username.trim().length < 3) {
      return res.status(400).json({ error: 'El usuario debe tener al menos 3 caracteres' });
    }

    if (!password || typeof password !== 'string' || password.length < 6) {
      return res.status(400).json({ error: 'La contraseña debe tener al menos 6 caracteres' });
    }

    // Verificar que el usuario no exista
    const existingUser = await db.query('SELECT id FROM users WHERE username = $1', [username.trim()]);

    if (existingUser.rows.length > 0) {
      return res.status(409).json({ error: 'El usuario ya existe' });
    }

    // Hash de la contraseña
    const hashedPassword = await bcrypt.hash(password, 10);

    // Insertar usuario
    const result = await db.query(
      'INSERT INTO users (username, password) VALUES ($1, $2) RETURNING id, username',
      [username.trim(), hashedPassword]
    );

    const user = result.rows[0];
    const token = generateToken(user.id, user.username);

    return res.status(201).json({
      message: 'Usuario registrado exitosamente',
      token,
      user: {
        id: user.id,
        username: user.username,
      },
    });
  } catch (error) {
    console.error('Error en register:', error.message);
    return res.status(500).json({ error: 'Error interno del servidor' });
  }
}

export async function login(req, res) {
  try {
    const { email, password } = req.body;

    // Validación básica
    if (typeof email !== 'string' || !email.trim() || typeof password !== 'string' || !password) {
      return res.status(400).json({ error: 'Email y contraseña requeridos' });
    }

    // Buscar usuario
    const result = await db.query('SELECT id, email, password_hash FROM empleados WHERE email = $1', [
      email.trim(),
    ]);

    if (result.rows.length === 0) {
      return res.status(401).json({ error: 'Email o contraseña incorrectos' });
    }

    const empleado = result.rows[0];

    // Verificar contraseña
    const passwordValida = await bcrypt.compare(password, empleado.password_hash);

    if (!passwordValida) {
      return res.status(401).json({ error: 'Email o contraseña incorrectos' });
    }

    // Generar token
    const token = generateToken(empleado.id, empleado.email);

    return res.status(200).json({
      message: 'Sesión iniciada',
      token,
      user: {
        id: empleado.id,
        username: empleado.email,
      },
    });
  } catch (error) {
    console.error('Error en login');
    return res.status(500).json({ error: 'Error interno del servidor' });
  }
}
