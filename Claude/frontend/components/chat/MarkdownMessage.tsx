"use client";

import { memo, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import { Check, Copy } from "lucide-react";

import { cn } from "@/lib/utils";

/**
 * Markdown renderer for assistant messages.
 * - GitHub-flavoured markdown (tables, strikethrough, task lists)
 * - Syntax highlighting via rehype-highlight (highlight.js)
 * - Each code block gets a copy button
 * Memoised so streaming re-renders of the parent don't re-parse settled text.
 */
function CodeBlock({ className, children }: { className?: string; children: React.ReactNode }) {
  const [copied, setCopied] = useState(false);
  const text = String(children);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard unavailable */
    }
  };

  return (
    <div className="group relative">
      <button
        onClick={copy}
        className="absolute right-2 top-2 z-10 rounded-md border border-white/10 bg-white/5 p-1.5 text-white/70 opacity-0 transition-opacity hover:bg-white/10 hover:text-white group-hover:opacity-100"
        aria-label="Salin kode"
      >
        {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
      </button>
      <pre className={className}>{children}</pre>
    </div>
  );
}

export const MarkdownMessage = memo(function MarkdownMessage({
  content,
  className,
}: {
  content: string;
  className?: string;
}) {
  return (
    <div className={cn("prose-chat", className)}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[[rehypeHighlight, { detect: true, ignoreMissing: true }]]}
        components={{
          pre: ({ children }) => <CodeBlock>{children}</CodeBlock>,
          a: ({ href, children }) => (
            <a href={href} target="_blank" rel="noopener noreferrer">
              {children}
            </a>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
});
