import bcrypt from 'bcrypt';
import db from '../config/database.js';
import { generateToken } from '../middleware/auth.js';

export async function register(req, res) {
  return res.status(403).json({
    error: 'El registro público está deshabilitado',
  });
}

export async function login(req, res) {
  try {
    const { email, password } = req.body ?? {};

    // Validación
    if (
      typeof email !== 'string' ||
      !email.trim() ||
      typeof password !== 'string' ||
      !password
    ) {
      return res.status(400).json({
        error: 'Email y contraseña requeridos',
      });
    }

    const normalizedEmail = email.trim().toLowerCase();

    // Buscar por email personal O corporativo
    const result = await db.query(
      `
        SELECT
          id,
          nombre,
          apellido,
          email_personal,
          email_corporativo,
          password_hash,
          activo
        FROM public.empleados
        WHERE LOWER(email_personal) = $1
           OR LOWER(email_corporativo) = $1
        LIMIT 1
      `,
      [normalizedEmail]
    );

    if (result.rows.length === 0) {
      return res.status(401).json({
        error: 'Email o contraseña incorrectos',
      });
    }

    const empleado = result.rows[0];

    if (!empleado.activo || !empleado.password_hash) {
      return res.status(401).json({
        error: 'Email o contraseña incorrectos',
      });
    }

    // Comparar contraseña contra hash bcrypt
    const passwordValida = await bcrypt.compare(
      password,
      empleado.password_hash
    );

    if (!passwordValida) {
      return res.status(401).json({
        error: 'Email o contraseña incorrectos',
      });
    }

    const empleadoEmail =
      empleado.email_corporativo ||
      empleado.email_personal;

    // Generar JWT
    const token = generateToken(
      empleado.id,
      empleadoEmail
    );

    return res.status(200).json({
      message: 'Sesión iniciada',
      token,
      user: {
        id: empleado.id,
        username: empleadoEmail,
        nombre: empleado.nombre,
        apellido: empleado.apellido,
      },
    });

  } catch (error) {
    console.error('Error en login:', error.message);

    return res.status(500).json({
      error: 'Error interno del servidor',
    });
  }
}
