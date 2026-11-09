/** Microprint rule: the tagline repeated at ~5px, as on a real cheque's signature line. */
const TEXT = "LLMS DECIDE WHAT TO SAY · CODE DECIDES WHAT IS ALLOWED · ";

export default function Microprint({ className = "" }) {
  return (
    <div className={`microprint ${className}`} aria-hidden="true">
      {TEXT.repeat(20)}
    </div>
  );
}
