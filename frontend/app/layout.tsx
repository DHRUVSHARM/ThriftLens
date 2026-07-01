import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ThriftLens",
  description: "Source-backed product research from images and descriptions.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
