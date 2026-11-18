/** Authored icons, one 1.5px stroke family. MICR symbols follow the E-13B bar shapes. */
const P = { fill: "none", stroke: "currentColor", strokeWidth: 1.5, strokeLinecap: "round", strokeLinejoin: "round" };

export function Arrow(props) {
  return (
    <svg viewBox="0 0 20 20" width="16" height="16" aria-hidden="true" {...props}>
      <path {...P} d="M4 10h11M11 5.5 15.5 10 11 14.5" />
    </svg>
  );
}

export function GitHub(props) {
  return (
    <svg viewBox="0 0 20 20" width="16" height="16" aria-hidden="true" {...props}>
      <path
        {...P}
        d="M7.5 16.5c-3.5 1-3.5-1.8-5-2.2m10 4v-2.7c0-.8.1-1.2-.4-1.7 2.2-.2 4.4-1.1 4.4-4.9 0-1-.4-2-1-2.7.3-.9.3-1.9-.1-2.8 0 0-.9-.3-2.8 1a9.5 9.5 0 0 0-5 0c-1.9-1.3-2.8-1-2.8-1-.4.9-.4 1.9-.1 2.8-.7.7-1 1.7-1 2.7 0 3.8 2.2 4.7 4.4 4.9-.5.5-.5 1-.4 1.7v2.7"
      />
    </svg>
  );
}

export function Sun(props) {
  return (
    <svg viewBox="0 0 20 20" width="16" height="16" aria-hidden="true" {...props}>
      <circle {...P} cx="10" cy="10" r="3.5" />
      <path {...P} d="M10 2v2M10 16v2M2 10h2M16 10h2M4.3 4.3l1.4 1.4M14.3 14.3l1.4 1.4M4.3 15.7l1.4-1.4M14.3 5.7l1.4-1.4" />
    </svg>
  );
}

export function Moon(props) {
  return (
    <svg viewBox="0 0 20 20" width="16" height="16" aria-hidden="true" {...props}>
      <path {...P} d="M16 12.5A6.5 6.5 0 0 1 7.5 4a6.5 6.5 0 1 0 8.5 8.5Z" />
    </svg>
  );
}

export function Transit() {
  return (
    <svg className="micr-sym" viewBox="0 0 10 12" aria-hidden="true">
      <rect x="0" y="0" width="2.4" height="12" fill="currentColor" />
      <rect x="4" y="0" width="6" height="4" fill="currentColor" />
      <rect x="4" y="8" width="6" height="4" fill="currentColor" />
    </svg>
  );
}

export function OnUs() {
  return (
    <svg className="micr-sym" viewBox="0 0 10 12" aria-hidden="true">
      <rect x="0" y="0" width="3" height="8" fill="currentColor" />
      <rect x="4.5" y="0" width="3" height="8" fill="currentColor" />
      <rect x="0" y="9.5" width="10" height="2.5" fill="currentColor" />
    </svg>
  );
}
