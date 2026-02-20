/**
 * Animated background with serpentine pattern + floating gradient orbs.
 * Ported from serpent-rag-ui.jsx.
 */

export default function AnimatedBG() {
  return (
    <div className="fixed inset-0 z-0 overflow-hidden pointer-events-none">
      {/* Scale pattern */}
      <svg
        width="100%"
        height="100%"
        className="absolute opacity-[0.03]"
      >
        <defs>
          <pattern
            id="snakeScale"
            x="0"
            y="0"
            width="40"
            height="40"
            patternUnits="userSpaceOnUse"
          >
            <path
              d="M20 0 Q30 10 20 20 Q10 30 20 40"
              stroke="#C8F547"
              strokeWidth="0.5"
              fill="none"
            />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#snakeScale)" />
      </svg>

      {/* Floating gradient orbs */}
      <div
        className="absolute -top-[20%] -right-[10%] w-[600px] h-[600px] animate-serpent-float"
        style={{
          background:
            'radial-gradient(circle, rgba(139,92,246,0.06) 0%, transparent 70%)',
        }}
      />
      <div
        className="absolute -bottom-[15%] -left-[5%] w-[500px] h-[500px] animate-serpent-float-reverse"
        style={{
          background:
            'radial-gradient(circle, rgba(200,245,71,0.04) 0%, transparent 70%)',
        }}
      />
      <div
        className="absolute top-[40%] left-[50%] w-[400px] h-[400px] animate-serpent-float-delayed"
        style={{
          background:
            'radial-gradient(circle, rgba(45,212,168,0.03) 0%, transparent 70%)',
        }}
      />
    </div>
  );
}
