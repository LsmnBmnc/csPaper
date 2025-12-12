import React from "react";
import { Header } from "./components/layout/Header";
import { Footer } from "./components/layout/Footer";
import { UploadPage } from "./pages/UploadPage";

export default function App() {
  return (
    <div className="app-root">
      <Header />
      <main className="app-main">
        <UploadPage />
      </main>
      <Footer />
    </div>
  );
}
