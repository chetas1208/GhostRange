type CodeBlockProps = {
  code: string;
  title?: string;
};

export function CodeBlock({ code, title }: CodeBlockProps) {
  return (
    <div className="code-block">
      {title && <div className="code-block-title">{title}</div>}
      <pre>
        <code>{code}</code>
      </pre>
    </div>
  );
}
