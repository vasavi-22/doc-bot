import { useState } from "react";
import Sidebar from "./components/Sidebar";
import Dashboard from "./components/Dashboard";
import Documents from "./components/Documents";
import ChatPage from "./components/ChatPage";

export default function App() {
  const [activeTab, setActiveTab] = useState("dashboard");

  return (
    <div className="flex h-screen bg-white">
      <Sidebar activeTab={activeTab} onTabChange={setActiveTab} />
      <main className="flex-1 overflow-auto">
        {activeTab === "dashboard" && <Dashboard />}
        {activeTab === "documents" && <Documents />}
        {activeTab === "chat" && <ChatPage />}
      </main>
    </div>
  );
}