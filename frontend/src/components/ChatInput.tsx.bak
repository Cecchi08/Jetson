import { ArrowUp, Paperclip, SlidersHorizontal } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';

interface ChatInputProps { disabled: boolean; onSend: (content: string) => void; }

export function ChatInput({ disabled, onSend }: ChatInputProps) {
  const [value, setValue] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  useEffect(() => { const textarea = textareaRef.current; if (textarea) { textarea.style.height = 'auto'; textarea.style.height = `${Math.min(textarea.scrollHeight, 144)}px`; } }, [value]);
  const submit = () => { if (!value.trim() || disabled) return; onSend(value); setValue(''); };
  return <div className="composer-wrap"><div className="composer"><textarea ref={textareaRef} value={value} onChange={(event) => setValue(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); submit(); } }} placeholder="Escribe un mensaje..." rows={1} disabled={disabled} aria-label="Mensaje para Orion" /><div className="composer__tools"><div><button aria-label="Adjuntar archivo" disabled={disabled}><Paperclip size={17} /></button><button aria-label="Ajustes de respuesta" disabled={disabled}><SlidersHorizontal size={17} /></button></div><button className="send-button" onClick={submit} disabled={disabled || !value.trim()} aria-label="Enviar mensaje"><ArrowUp size={18} /></button></div></div><p className="composer-note">Orion puede cometer errores. Verifica la información importante.</p></div>;
}
