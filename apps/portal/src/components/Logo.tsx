// Logo ODBr em texto (Nunito 900): as cores vêm dos tokens --odbr-logo-*,
// então o mesmo componente serve ao tema claro e ao dark.
// Para uso fora do portal (documentos, redes), use os SVGs em design-system/assets/brand.

interface Props {
  size?: number;
  /** Texto para leitores de tela; o logo em si é decorativo. */
  label?: string;
}

export function Logo({ size = 30, label = "ODBr" }: Props) {
  return (
    <span className="logo" style={{ fontSize: size }} role="img" aria-label={label}>
      <span className="o" aria-hidden="true">
        O
      </span>
      <span className="d" aria-hidden="true">
        D
      </span>
      <span className="br" aria-hidden="true">
        Br
      </span>
    </span>
  );
}
