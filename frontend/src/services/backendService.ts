import type { Message } from '../types';
import { authService } from './authService';
import type { ChatMode } from '../components/ChatInput';

export interface AssistantService {
  sendMessage(messages: Message[], mode?: ChatMode): Promise<string>;
}

export const backendService: AssistantService = {
  async sendMessage(messages, mode = 'chat') {
    try {
      const message = messages[messages.length - 1]?.content ?? '';
      const token = authService.getToken();

      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          message,
          mode,
        }),
      });

      const data = await response.json().catch(() => null);

      if (!response.ok) {
        throw new Error(
          data?.error || 'No se pudo obtener una respuesta del asistente.'
        );
      }

      if (data?.response === undefined || data?.response === null) {
        throw new Error('Respuesta inesperada del servidor.');
      }

      if (typeof data.response === 'string') {
        return data.response;
      }

      return JSON.stringify(data.response, null, 2);

    } catch (error) {
      if (error instanceof Error) throw error;

      throw new Error(
        'No se pudo conectar con el asistente. Verificá que el backend esté ejecutándose.'
      );
    }
  },
};
