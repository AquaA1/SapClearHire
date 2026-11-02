import React from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from '../components/shell/Sidebar';
import { TopNavbar } from '../components/shell/TopNavbar';

export const DashboardLayout: React.FC = () => {
  return (
    <div
      className="min-h-screen text-ink font-sans flex overflow-hidden"
      style={{ backgroundColor: 'var(--canvas)' }}
    >
      {/* Fixed Dark Sidebar Rail */}
      <Sidebar />

      {/* Main Content Area */}
      <div
        className="flex-1 flex flex-col min-w-0 h-screen overflow-y-auto"
        style={{ backgroundColor: 'var(--canvas)' }}
      >
        <TopNavbar />
        <main className="flex-1 px-6 md:px-8 pt-5 sm:pt-6 pb-12">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
