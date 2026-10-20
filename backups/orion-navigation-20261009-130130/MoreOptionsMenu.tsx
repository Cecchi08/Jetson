import { useEffect, useRef, useState } from 'react';
import { Calculator, MoreHorizontal } from 'lucide-react';
import './MoreOptionsMenu.css';

export default function MoreOptionsMenu() {
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;

    const handleOutside = (event: PointerEvent) => {
      if (!menuRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    };

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false);
    };

    document.addEventListener('pointerdown', handleOutside);
    document.addEventListener('keydown', handleEscape);

    return () => {
      document.removeEventListener('pointerdown', handleOutside);
      document.removeEventListener('keydown', handleEscape);
    };
  }, [open]);

  return (
    <div className="orion-options" ref={menuRef}>
      <button
        type="button"
        className="icon-button"
        aria-label="Más opciones"
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen(!open)}
      >
        <MoreHorizontal size={20} />
      </button>

      {open && (
        <div className="orion-options__dropdown" role="menu">
          <a
            href="http://10.1.1.13:8001/"
            target="_blank"
            rel="noopener noreferrer"
            role="menuitem"
            className="orion-options__item"
            onClick={() => setOpen(false)}
          >
            <Calculator size={18} />
            <span>Calculadora de Envíos</span>
          </a>
        </div>
      )}
    </div>
  );
}
