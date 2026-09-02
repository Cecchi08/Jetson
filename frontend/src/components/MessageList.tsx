import { Copy, RotateCcw, UserRound, Bot } from 'lucide-react';
import type { Message } from '../types';

interface MessageListProps {
  messages: Message[];
  streamingMessage: string | null;
  isGenerating: boolean;
}

function renderMessage(content: string) {
  const parts = content.split(/(\/pdfs\/[^\s]+)/g);

  return parts.map((part, index) => {
    if (part.startsWith('/pdfs/')) {
      const url = `${window.location.origin}${part}`;

      return (
        <a
          key={index}
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className="pdf-link"
        >
          Descargar PDF
        </a>
      );
    }

    return <span key={index}>{part}</span>;
  });
}

export function MessageList({ messages, streamingMessage, isGenerating }: MessageListProps) {
  return (
    <>
      {messages.map((message) => {
        const isUser = message.role === 'user';

        return (
          <article
            key={message.id}
            className={`message-row ${isUser ? 'message-row--user' : ''}`}
          >
            <div
              className={`message-avatar ${
                isUser
                  ? 'message-avatar--user'
                  : 'message-avatar--assistant'
              }`}
            >
              {isUser ? <UserRound size={16} /> : <Bot size={16} />}
            </div>

            <div className="message-content">
              <div className="message-meta">
                <strong>{isUser ? 'Tú' : 'Orion'}</strong>
                <time>{isUser ? 'Ahora' : 'Asistente'}</time>
              </div>

              <p className="message-text">
                {renderMessage(message.content)}
              </p>

              {!isUser && (
                <div className="message-actions">
                  <button aria-label="Copiar mensaje">
                    <Copy size={13} />
                  </button>

                  <button aria-label="Regenerar respuesta">
                    <RotateCcw size={13} />
                  </button>
                </div>
              )}
            </div>
          </article>
        );
      })}
    </>
  );
}
