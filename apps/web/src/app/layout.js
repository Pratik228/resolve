import "./globals.css";
import Nav from "../components/Nav";

export const metadata = {
  title: "Resolve · Northwind Cloud",
  description: "Eval-gated agentic Tier-2 support engine",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        <div className="shell">
          <Nav />
          <main className="main">{children}</main>
        </div>
      </body>
    </html>
  );
}
