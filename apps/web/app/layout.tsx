import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CloudTrim",
  description: "Shift-left cloud cost optimizer — a reviewer that remediates.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
