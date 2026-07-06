import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ThriftLens",
  description: "Source-backed product research from images and descriptions.",
  icons: {
    icon: "/favicon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const themeScript = `
    (() => {
      try {
        const stored = window.localStorage.getItem("thriftlens-theme");
        document.documentElement.dataset.theme = stored === "light" || stored === "dark" ? stored : "dark";
      } catch {
        document.documentElement.dataset.theme = "dark";
      }
    })();
  `;

  return (
    <html lang="en" data-theme="dark" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body>{children}</body>
    </html>
  );
}
