import katex from "katex";
import "katex/dist/katex.min.css";

export function Tex({ children, block = false }: { children: string; block?: boolean }) {
  const html = katex.renderToString(children, { displayMode: block, throwOnError: false });
  return <span className={block ? "block overflow-x-auto py-2" : ""} dangerouslySetInnerHTML={{ __html: html }} />;
}
