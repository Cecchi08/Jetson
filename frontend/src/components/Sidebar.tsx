import {
  Bot,
  Calculator,
  LogIn,
  LogOut,
  MessageSquarePlus,
  PanelLeftClose,
  Settings2
} from 'lucide-react';

import type { Conversation, User } from '../types';
import type { AppView } from '../views';

interface SidebarProps {
  conversations: Conversation[];
  activeId: string;
  user: User | null;
  isAuthenticated: boolean;
  isOpen: boolean;
  activeView: AppView;
  onViewChange: (view: AppView) => void;
  onSelect: (id: string) => void;
  onNewChat: () => void;
  onLogin: () => void;
  onLogout: () => void;
  onClose: () => void;
}

export function Sidebar({
  conversations,
  activeId,
  user,
  isAuthenticated,
  isOpen,
  activeView,
  onViewChange,
  onSelect,
  onNewChat,
  onLogin,
  onLogout,
  onClose
}: SidebarProps) {

  const getInitials = (username: string) =>
    username
      .split(' ')
      .map((word) => word[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);

  return (
    <aside
      className={`sidebar ${isOpen ? 'sidebar--open' : ''}`}
      aria-label="Barra lateral"
    >
      <div className="sidebar__topline">
        <div className="brand">
          <span className="brand__mark">
            <Bot size={18} />
          </span>
          <span>ORION</span>
        </div>

        <button
          className="icon-button sidebar__close"
          onClick={onClose}
          aria-label="Cerrar menú"
        >
          <PanelLeftClose size={18} />
        </button>
      </div>

      <nav className="orion-navigation" aria-label="Herramientas">
        <button
          type="button"
          className={`orion-navigation__item ${
            activeView === 'agent' ? 'orion-navigation__item--active' : ''
          }`}
          aria-current={activeView === 'agent' ? 'page' : undefined}
          onClick={() => onViewChange('agent')}
        >
          <Bot size={18} />
          <span>Orion IA</span>
        </button>

        {/* Calculadora conservada para reactivarla en el futuro.
        <button
          type="button"
          className={`orion-navigation__item ${
            activeView === 'calculator' ? 'orion-navigation__item--active' : ''
          }`}
          aria-current={activeView === 'calculator' ? 'page' : undefined}
          onClick={() => onViewChange('calculator')}
        >
          <Calculator size={18} />
          <span>Calculadora de Envíos</span>
        </button>
        */}
      </nav>

      {isAuthenticated && activeView === 'agent' && (
        <>
          <button className="new-chat" onClick={onNewChat}>
            <MessageSquarePlus size={17} />
            <span>Nuevo chat</span>
            <kbd>⌘ K</kbd>
          </button>

          <div className="conversation-list">
            <div className="list-label">
              Recientes <span>{conversations.length}</span>
            </div>

            {conversations.map((conversation) => (
              <button
                key={conversation.id}
                className={`conversation ${
                  activeView === 'agent' && conversation.id === activeId
                    ? 'conversation--active'
                    : ''
                }`}
                onClick={() => onSelect(conversation.id)}
              >
                <span className="conversation__icon">
                  <MessageSquarePlus size={15} />
                </span>

                <span className="conversation__copy">
                  <strong>{conversation.title}</strong>
                  <small>{conversation.preview}</small>
                </span>

                <span className="conversation__time">
                  {conversation.updatedAt}
                </span>
              </button>
            ))}
          </div>
        </>
      )}

      <div className="sidebar__footer">
        {isAuthenticated && user ? (
          <>
            <div className="profile">
              <span className="avatar">
                {getInitials(user.username)}
              </span>
              <span className="profile__copy">
                <strong>{user.username}</strong>
                <small>@usuario</small>
              </span>
            </div>

            <button className="settings">
              <Settings2 size={16} />
              <span>Preferencias</span>
              <span className="status-dot" />
            </button>

            <button
              className="logout-btn"
              onClick={onLogout}
              title="Cerrar sesión"
            >
              <LogOut size={16} />
              <span>Cerrar sesión</span>
            </button>
          </>
        ) : (
          <button className="logout-btn" onClick={onLogin}>
            <LogIn size={16} />
            <span>Iniciar sesión</span>
          </button>
        )}

        <p className="version">
          ORION DESKTOP <span>v0.1</span>
        </p>
      </div>
    </aside>
  );
}
