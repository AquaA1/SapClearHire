import React from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from '../components/shell/Sidebar';
import { TopNavbar } from '../components/shell/TopNavbar';

export const DashboardLayout: React.FC = () => {
  return (
    <div className="min-h-screen bg-canvas text-ink flex overflow-hidden">
      {/* Fixed Dark Sidebar Rail */}
      <Sidebar />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 h-screen overflow-y-auto">
        <TopNavbar />
        <main className="flex-1 px-6 md:px-8 pb-10">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
