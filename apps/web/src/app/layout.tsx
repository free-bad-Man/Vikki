import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Vikki",
  description: "Fullstack Platform",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body style={{ margin: 0 }}>{children}</body>
    </html>
  );
}
