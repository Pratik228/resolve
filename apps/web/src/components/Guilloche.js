/** Security-paper guilloche: overlapping harmonic bands computed from parameters, not an image.
 *  Deterministic per `seed`, so the server and client render identical paths. */
function band({ w, y, amp, waves, phase }) {
  const pts = [];
  const steps = 300;
  for (let i = 0; i <= steps; i++) {
    const t = i / steps;
    const v =
      Math.sin(2 * Math.PI * waves * t + phase) +
      0.35 * Math.sin(2 * Math.PI * waves * 2.03 * t + phase * 2) +
      0.12 * Math.sin(2 * Math.PI * waves * 3.01 * t + phase * 3);
    pts.push(`${(t * w).toFixed(1)},${(y + amp * v).toFixed(1)}`);
  }
  return `M${pts.join("L")}`;
}

function rng(seed) {
  let s = seed >>> 0;
  return () => {
    s = (s * 1664525 + 1013904223) >>> 0;
    return s / 4294967296;
  };
}

export default function Guilloche({ seed = 7, lines = 22, width = 1200, height = 420, className = "" }) {
  const r = rng(seed);
  const paths = [];
  for (let i = 0; i < lines; i++) {
    paths.push(
      band({
        w: width,
        y: height * (0.12 + 0.76 * (i / Math.max(lines - 1, 1))),
        amp: height * (0.07 + 0.05 * r()),
        waves: 2 + Math.floor(r() * 3) + (i % 2) * 0.5,
        phase: i * 0.41 + r() * 2,
      })
    );
  }
  return (
    <svg
      className={`guilloche ${className}`}
      viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio="none"
      aria-hidden="true"
      focusable="false"
    >
      {paths.map((d, i) => (
        <path key={i} d={d} />
      ))}
    </svg>
  );
}
