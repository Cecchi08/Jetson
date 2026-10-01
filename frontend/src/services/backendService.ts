import type { Conversation, Message } from '../types';
import { authService } from './authService';

export interface AssistantService {
  getConversations(): Promise<Conversation[]>;

  getMessages(sessionId: string): Promise<Message[]>;

  sendMessage(
    messages: Message[],
    file?: File,
    sessionId?: string
  ): Promise<string>;
}

function authHeaders() {
  return {
    Authorization: `Bearer ${authService.getToken()}`,
  };
}

export const backendService: AssistantService = {
  async getConversations() {
    const response = await fetch(
      '/api/chat/conversations',
      {
        headers: authHeaders(),
      }
    );

    const data = await response.json().catch(() => null);

    if (!response.ok) {
      throw new Error(
        data?.error || 'No se pudieron cargar las conversaciones.'
      );
    }

    return Array.isArray(data) ? data : [];
  },

  async getMessages(sessionId) {
    const response = await fetch(
      `/api/chat/conversations/${encodeURIComponent(sessionId)}/messages`,
      {
        headers: authHeaders(),
      }
    );

    const data = await response.json().catch(() => null);

    if (!response.ok) {
      throw new Error(
        data?.error || 'No se pudieron cargar los mensajes.'
      );
    }

    return Array.isArray(data) ? data : [];
  },

  async sendMessage(messages, file, sessionId) {
    const message =
      messages[messages.length - 1]?.content ?? '';

    if (!sessionId) {
      throw new Error('No existe session_id.');
    }

    const formData = new FormData();

    formData.append('message', message);
    formData.append('session_id', sessionId);

    if (file) {
      formData.append('file', file);
    }

    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: authHeaders(),
      body: formData,
    });

    const data = await response.json().catch(() => null);

    if (!response.ok) {
      throw new Error(
        data?.error ||
        'No se pudo obtener una respuesta del asistente.'
      );
    }

    if (data?.response === undefined || data?.response === null) {
      throw new Error('Respuesta inesperada del servidor.');
    }

    return typeof data.response === 'string'
      ? data.response
      : JSON.stringify(data.response, null, 2);
  },
};
