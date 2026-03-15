import type { Metadata } from "next";
import "./globals.css";
import { Header } from "@/components/Layout/Header";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "GOV Tracker",
  description: "Track GOV.UK publications and parliamentary activity locally.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <Providers>
          <div className="min-h-screen">
            <Header />
            {children}
          </div>
        </Providers>
      </body>
    </html>
  );
}
