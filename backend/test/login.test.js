import assert from 'node:assert/strict';
import { test } from 'node:test';
import bcrypt from 'bcrypt';
import jwt from 'jsonwebtoken';
import db from '../src/config/database.js';
import { login } from '../src/controllers/authController.js';

test('login valida bcrypt y protege el hash', async (t) => {
  const password = 'Clave de prueba 123';
  const empleado = {
    id: 7,
    email: 'empleado@example.com',
    password_hash: await bcrypt.hash(password, 4),
  };
  const query = t.mock.method(db, 'query', async (sql, params) => {
    assert.equal(sql, 'SELECT id, email, password_hash FROM empleados WHERE email = $1');
    assert.deepEqual(params, [empleado.email]);
    return { rows: [empleado] };
  });
  t.mock.method(bcrypt, 'hash', () => { throw new Error('No generar hashes en login'); });
  const logs = t.mock.method(console, 'error', () => {});

  async function request(body) {
    const res = {
      status(code) { this.statusCode = code; return this; },
      json(data) { this.body = data; return this; },
    };
    await login({ body }, res);
    assert.ok(!JSON.stringify(res.body).includes(empleado.password_hash));
    assert.ok(!JSON.stringify(res.body).includes('password_hash'));
    return res;
  }

  const success = await request({ email: ` ${empleado.email} `, password });
  assert.equal(success.statusCode, 200);
  assert.deepEqual(success.body.user, { id: empleado.id, username: empleado.email });
  const claims = jwt.verify(success.body.token, process.env.JWT_SECRET || 'change_this_secret');
  assert.equal(claims.id, empleado.id);
  assert.equal(claims.username, empleado.email);
  assert.equal(claims.exp - claims.iat, 86400);
  assert.equal(claims.password_hash, undefined);

  const failure = await request({ email: empleado.email, password: 'incorrecta' });
  assert.equal(failure.statusCode, 401);
  assert.deepEqual(failure.body, { error: 'Email o contraseña incorrectos' });

  query.mock.mockImplementation(async () => ({ rows: [] }));
  const missing = await request({ email: empleado.email, password });
  assert.equal(missing.statusCode, 401);
  assert.deepEqual(missing.body, failure.body);

  for (const body of [{ password }, { email: [], password }, { email: empleado.email, password: {} }]) {
    assert.equal((await request(body)).statusCode, 400);
  }

  query.mock.mockImplementation(async () => { throw new Error(empleado.password_hash); });
  assert.equal((await request({ email: empleado.email, password })).statusCode, 500);
  assert.ok(!JSON.stringify(logs.mock.calls).includes(empleado.password_hash));
});
