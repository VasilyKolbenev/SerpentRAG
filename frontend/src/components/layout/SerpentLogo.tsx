/**
 * SVG serpent logo — ported from serpent-rag-ui.jsx.
 */

interface SerpentLogoProps {
  size?: number;
}

export default function SerpentLogo({ size = 32 }: SerpentLogoProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" fill="none">
      <defs>
        <linearGradient id="serpGrad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#C8F547" />
          <stop offset="50%" stopColor="#2DD4A8" />
          <stop offset="100%" stopColor="#8B5CF6" />
        </linearGradient>
      </defs>
      <path
        d="M72 18c-12 0-18 8-24 16s-12 16-24 16c-8 0-12-4-12-10s6-12 16-12c6 0 10 2 14 6 4-8 10-14 18-14 12 0 18 8 18 20s-8 22-22 30c-10 6-20 8-28 8"
        stroke="url(#serpGrad)"
        strokeWidth="5"
        strokeLinecap="round"
        fill="none"
      />
      <circle cx="30" cy="38" r="2.5" fill="#C8F547" />
      <path
        d="M18 42l-6 3 6 3"
        stroke="#C8F547"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
    </svg>
  );
}
