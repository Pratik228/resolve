import "./globals.css";
import { Bodoni_Moda, Herr_Von_Muellerhoff, JetBrains_Mono, Public_Sans } from "next/font/google";
import Nav from "../components/Nav";

const display = Bodoni_Moda({ subsets: ["latin"], variable: "--f-display", display: "swap", style: ["normal", "italic"], adjustFontFallback: false });
const ui = Public_Sans({ subsets: ["latin"], variable: "--f-ui", display: "swap" });
const mono = JetBrains_Mono({ subsets: ["latin"], variable: "--f-mono", display: "swap" });
const script = Herr_Von_Muellerhoff({ subsets: ["latin"], weight: "400", variable: "--f-script", display: "swap" });

export const metadata = {
  title: "Resolve: an agent that can't write its own cheques",
  description:
    "An agentic Tier-2 support engine. The model writes the reply; a deterministic policy engine decides every refund, with human approval above $100 and CI-gated evals.",
};

const themeBoot = `try{var t=localStorage.getItem("resolve-theme");if(t)document.documentElement.dataset.theme=t}catch(e){}`;

export default function RootLayout({ children }) {
  return (
    <html lang="en" className={`${display.variable} ${ui.variable} ${mono.variable} ${script.variable}`} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeBoot }} />
      </head>
      <body>
        <a className="skip" href="#main">
          Skip to content
        </a>
        <Nav />
        <main id="main">{children}</main>
        <footer className="sitefoot">
          <div className="sitefoot__inner">
            <p>
              Resolve is a portfolio project by Pratik Mishra. Northwind Cloud is fictional; every customer, invoice and
              ticket here is synthetic.
            </p>
            <p>
              <a href="https://github.com/Pratik228/resolve">Source, evals and design notes on GitHub</a>
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}
