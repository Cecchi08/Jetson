import db from '../config/database.js';

function sanitizeText(value, maxLength = 255) {
  if (typeof value !== 'string') {
    return '';
  }

  return value.replace(/\s+/g, ' ').trim().slice(0, maxLength) || 'Sin contenido';
}

export async function persistChatConversation(messages, assistantReply) {
  if (!Array.isArray(messages) || messages.length === 0) {
    return null;
  }

  const lastUserMessage = [...messages].reverse().find((msg) => msg.role === 'user');
  const title = sanitizeText(lastUserMessage?.content || 'Nueva conversación', 60);
  const preview = sanitizeText(assistantReply, 255);

  const conversationResult = await db.query(
    `INSERT INTO conversations (user_id, title, preview, updated_at)
     VALUES ($1, $2, $3, CURRENT_TIMESTAMP)
     RETURNING id`,
    ['demo-user', title, preview]
  );

  const conversationId = conversationResult.rows[0].id;

  for (const msg of messages) {
    await db.query(
      `INSERT INTO messages (conversation_id, role, content)
       VALUES ($1, $2, $3)`,
      [conversationId, msg.role, msg.content]
    );
  }

  await db.query(
    `INSERT INTO messages (conversation_id, role, content)
     VALUES ($1, $2, $3)`,
    [conversationId, 'assistant', assistantReply]
  );

  await db.query(
    `UPDATE conversations
     SET updated_at = CURRENT_TIMESTAMP, preview = $2
     WHERE id = $1`,
    [conversationId, preview]
  );

  return conversationId;
}
