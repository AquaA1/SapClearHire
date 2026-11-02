import React, { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';

export interface ExpandableTextProps {
  text: string;
  maxChars?: number;
  className?: string;
  moreLabel?: string;
  lessLabel?: string;
  expandLabel?: string;
  collapseLabel?: string;
  quote?: boolean;
  italic?: boolean;
  buttonClassName?: string;
}

export const ExpandableText: React.FC<ExpandableTextProps> = ({
  text,
  maxChars = 200,
  className = '',
  moreLabel,
  lessLabel,
  expandLabel,
  collapseLabel,
  quote = false,
  italic = false,
  buttonClassName = '',
}) => {
  const actualMoreLabel = expandLabel || moreLabel || 'Show more';
  const actualLessLabel = collapseLabel || lessLabel || 'Show less';
  const [isExpanded, setIsExpanded] = useState(false);

  if (!text) return null;

  const cleanText = text.trim();
  const isLong = cleanText.length > maxChars;

  if (!isLong) {
    const formatted = quote ? `"${cleanText}"` : cleanText;
    return (
      <span className={`${italic ? 'italic' : ''} ${className}`}>
        {formatted}
      </span>
    );
  }

  // Find a word boundary near maxChars so we don't slice mid-word
  const previewSlice = cleanText.slice(0, maxChars);
  const lastSpace = previewSlice.lastIndexOf(' ');
  const safePreview = (lastSpace > maxChars * 0.7 ? previewSlice.slice(0, lastSpace) : previewSlice).trim();

  const displayText = isExpanded ? cleanText : `${safePreview}...`;
  const formatted = quote ? `"${displayText}"` : displayText;

  return (
    <span className="inline">
      <span className={`${italic ? 'italic' : ''} ${className}`}>
        {formatted}
      </span>{' '}
      <button
        type="button"
        onClick={() => setIsExpanded(!isExpanded)}
        className={`inline-flex items-center gap-1 text-sm font-semibold text-accent hover:underline cursor-pointer select-none transition-colors ml-1 align-baseline ${buttonClassName}`}
        aria-expanded={isExpanded}
      >
        <span>{isExpanded ? actualLessLabel : actualMoreLabel}</span>
        {isExpanded ? (
          <ChevronUp className="w-3.5 h-3.5 shrink-0" />
        ) : (
          <ChevronDown className="w-3.5 h-3.5 shrink-0" />
        )}
      </button>
    </span>
  );
};
