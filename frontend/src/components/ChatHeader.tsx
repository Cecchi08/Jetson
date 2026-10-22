import { Menu, Sparkles } from 'lucide-react';
import MoreOptionsMenu from './MoreOptionsMenu';
import type { Assistant } from '../types';

interface ChatHeaderProps { assistant: Assistant; onMenu: () => void; onGoCalculator: () => void; }

export function ChatHeader({ assistant, onMenu, onGoCalculator }: ChatHeaderProps) {
  return <header className="chat-header"><button className="icon-button menu-button" onClick={onMenu} aria-label="Abrir menú"><Menu size={20} /></button><div className="assistant-heading"><span className="assistant-heading__icon"><Sparkles size={16} /></span><div><h1>{assistant.name}</h1><p><span className="status-dot" />{assistant.status}</p></div></div>{/* Calculadora conservada para reactivarla en el futuro.
      <MoreOptionsMenu onGoCalculator={onGoCalculator} />
      */}</header>;
}
