"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { GitHub, Moon, Sun } from "./Icon";

const ITEMS = [
  ["Console", "/console"],
  ["Approvals", "/approvals"],
  ["Evals", "/evals"],
  ["Break the refund", "/redteam"],
];

function ThemeToggle() {
  const [theme, setTheme] = useState(null);
  useEffect(() => {
    setTheme(document.documentElement.dataset.theme || null);
  }, []);
  function flip() {
    const current =
      theme || (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    const next = current === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try {
      localStorage.setItem("resolve-theme", next);
    } catch {}
    setTheme(next);
  }
  return (
    <button type="button" className="iconbtn" onClick={flip} aria-label="Switch between paper and carbon-copy theme">
      <span className="only-light"><Moon /></span>
      <span className="only-dark"><Sun /></span>
    </button>
  );
}

export default function Nav() {
  const path = usePathname();
  return (
    <header className="nav">
      <div className="nav__inner">
        <Link href="/" className="wordmark" aria-label="Resolve, home">
          Resolve
        </Link>
        <nav aria-label="Main" className="nav__nav">
          <ul className="nav__links">
            {ITEMS.map(([label, href]) => (
              <li key={href}>
                <Link href={href} aria-current={path === href || path.startsWith(href + "/") ? "page" : undefined}>
                  {label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
        <div className="nav__end">
          <a className="iconbtn" href="https://github.com/Pratik228/resolve" aria-label="Source on GitHub">
            <GitHub />
          </a>
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
