import { callN8n } from '../services/n8nService.js';
import chatPool from '../config/chatDatabase.js';

export async function getConversations(req, res) {
  try {
    const userId = String(req.user?.id ?? '');

    if (!userId) {
      return res.status(401).json({
        error: 'Usuario no identificado',
      });
    }

    const result = await chatPool.query(
      `
      SELECT
        s.session_id,

        COALESCE(
          (
            SELECT c.mensaje
            FROM public.chat c
            WHERE c.session_id = s.session_id
              AND c.rol = 'user'
            ORDER BY c.creado_en ASC
            LIMIT 1
          ),
          'Nueva conversación'
        ) AS title,

        COALESCE(
          (
            SELECT c.mensaje
            FROM public.chat c
            WHERE c.session_id = s.session_id
            ORDER BY c.creado_en DESC
            LIMIT 1
          ),
          'Nueva conversación'
        ) AS preview,

        s.actualizada_en

      FROM public.sesiones s
      WHERE s.usuario_id = $1
      ORDER BY s.actualizada_en DESC
      `,
      [userId]
    );

    return res.json(
      result.rows.map((row) => ({
        id: row.session_id,
        title: row.title.slice(0, 40),
        preview: row.preview,
        updatedAt: row.actualizada_en,
        messages: [],
      }))
    );
  } catch (error) {
    console.error('Error obteniendo conversaciones:', error.message);

    return res.status(500).json({
      error: 'No se pudieron obtener las conversaciones',
    });
  }
}

export async function getMessages(req, res) {
  try {
    const userId = String(req.user?.id ?? '');
    const { sessionId } = req.params;

    if (!userId) {
      return res.status(401).json({
        error: 'Usuario no identificado',
      });
    }

    // Primero comprobamos que la sesión pertenece al usuario autenticado.
    const session = await chatPool.query(
      `
      SELECT session_id
      FROM public.sesiones
      WHERE session_id = $1
        AND usuario_id = $2
      LIMIT 1
      `,
      [sessionId, userId]
    );

    if (session.rowCount === 0) {
      return res.status(404).json({
        error: 'Conversación no encontrada',
      });
    }

    const result = await chatPool.query(
      `
      SELECT
        id,
        rol,
        mensaje,
        creado_en
      FROM public.chat
      WHERE session_id = $1
      ORDER BY creado_en ASC, id ASC
      `,
      [sessionId]
    );

    return res.json(
      result.rows.map((row) => ({
        id: String(row.id),
        role: row.rol === 'assistant' ? 'assistant' : 'user',
        content: row.mensaje,
        createdAt: row.creado_en,
      }))
    );
  } catch (error) {
    console.error('Error obteniendo mensajes:', error.message);

    return res.status(500).json({
      error: 'No se pudieron obtener los mensajes',
    });
  }
}

export async function chat(req, res) {
  try {
    const { message, session_id } = req.body ?? {};
    const userId = String(req.user?.id ?? '');

    if (!userId) {
      return res.status(401).json({
        error: 'Usuario no identificado',
      });
    }

    if (typeof message !== 'string' || !message.trim()) {
      return res.status(400).json({
        error: 'El mensaje es obligatorio',
      });
    }

    if (typeof session_id !== 'string' || !session_id.trim()) {
      return res.status(400).json({
        error: 'El session_id es obligatorio',
      });
    }

    const response = await callN8n({
      id_user: userId,
      session_id: session_id.trim(),
      message: message.trim(),
      file: req.file,
    });

    return res.status(200).json({ response });
  } catch (error) {
    console.error('Error en /api/chat:', error.message);

    if (error?.name === 'TimeoutError') {
      return res.status(504).json({
        error: 'n8n tardó demasiado en responder',
      });
    }

    if (
      error?.message?.includes('ECONNREFUSED') ||
      error?.message?.includes('fetch failed')
    ) {
      return res.status(503).json({
        error: 'n8n no está disponible',
      });
    }

    return res.status(500).json({
      error: error.message || 'No se pudo procesar la solicitud',
    });
  }
}
