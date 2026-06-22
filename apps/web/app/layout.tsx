import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Lead Machine",
  description: "Danish local-business lead engine",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="da">
      <body className="min-h-screen bg-gray-50 text-gray-900 antialiased">
        {children}
      </body>
    </html>
  );
}
