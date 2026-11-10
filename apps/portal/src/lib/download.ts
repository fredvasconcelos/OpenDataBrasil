// Download de arquivos gerados no navegador (exportações e imagens do mapa).
// Design System: as cores do mapa são var(--…); antes de serializar, o clone recebe
// as cores já calculadas (resolveSvgColors), e o PNG usa o fundo do tema atual.
import { resolveSvgColors, token } from "./theme";

export function saveBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function svgBlob(svg: SVGSVGElement, caption: string): Blob {
  const clone = svg.cloneNode(true) as SVGSVGElement;
  resolveSvgColors(svg, clone);
  clone.setAttribute("xmlns", "http://www.w3.org/2000/svg");
  const note = document.createElementNS("http://www.w3.org/2000/svg", "desc");
  note.textContent = caption;
  clone.prepend(note);
  return new Blob([new XMLSerializer().serializeToString(clone)], { type: "image/svg+xml" });
}

export async function pngBlob(svg: SVGSVGElement, caption: string, scale = 2): Promise<Blob> {
  const [, , w = 800, h = 480] = (svg.getAttribute("viewBox") ?? "").split(" ").map(Number);
  const url = URL.createObjectURL(svgBlob(svg, caption));
  try {
    const image = new Image();
    await new Promise<void>((resolve, reject) => {
      image.onload = () => resolve();
      image.onerror = () => reject(new Error("imagem inválida"));
      image.src = url;
    });
    const canvas = document.createElement("canvas");
    canvas.width = w * scale;
    canvas.height = (h + 24) * scale;
    const ctx = canvas.getContext("2d");
    if (!ctx) throw new Error("canvas indisponível");
    ctx.scale(scale, scale);
    ctx.fillStyle = token("--odbr-bg-surface", "#fff");
    ctx.fillRect(0, 0, w, h + 24);
    ctx.drawImage(image, 0, 0, w, h);
    ctx.fillStyle = token("--odbr-text-muted", "#555F6E");
    ctx.font = `600 11px ${token("--odbr-font", "system-ui, sans-serif")}`;
    ctx.fillText(caption, 8, h + 16);
    return await new Promise<Blob>((resolve, reject) =>
      canvas.toBlob((b) => (b ? resolve(b) : reject(new Error("falha no PNG"))), "image/png"),
    );
  } finally {
    URL.revokeObjectURL(url);
  }
}
