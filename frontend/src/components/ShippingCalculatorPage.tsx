import { Bot, Calculator, Menu } from 'lucide-react';

interface Props {
  onGoAgent: () => void;
  onMenu: () => void;
}

export function ShippingCalculatorPage({
  onGoAgent,
  onMenu
}: Props) {
  return (
    <>
      <header className="chat-header">
        <button
          type="button"
          className="icon-button menu-button"
          onClick={onMenu}
          aria-label="Abrir menú"
        >
          <Menu size={20} />
        </button>

        <div className="assistant-heading">
          <span className="assistant-heading__icon">
            <Calculator size={16} />
          </span>
          <div>
            <h1>Calculadora de Envíos</h1>
            <p>Herramientas de logística</p>
          </div>
        </div>

        <button
          type="button"
          className="orion-return"
          onClick={onGoAgent}
        >
          <Bot size={17} />
          <span>Orion IA</span>
        </button>
      </header>

      <section className="orion-calculator-view">
        <div className="orion-calculator-view__content">
          <span className="orion-calculator-view__icon">
            <Calculator size={32} />
          </span>

          <h2>Calculadora de Envíos</h2>

          <p>
            La navegación ya está integrada en Orion.
            En la siguiente etapa incorporaremos aquí
            el formulario y las funcionalidades reales
            de la calculadora.
          </p>
        </div>
      </section>
    </>
  );
}
