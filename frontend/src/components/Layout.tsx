import { Outlet } from "react-router-dom";
import Navbar from "./Navbar";

export default function Layout() {
  return (
    <div className="min-h-screen bg-bgBase text-textPrimary font-body">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[100] focus:rounded-fz-md focus:bg-brandGold focus:px-4 focus:py-2 focus:text-sm focus:font-medium focus:text-textInverse"
      >
        Skip to main content
      </a>
      <Navbar />
      <main
        id="main-content"
        tabIndex={-1}
        className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 outline-none"
      >
        <Outlet />
      </main>
    </div>
  );
}
