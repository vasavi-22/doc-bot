import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { useState } from "react";
import { useAuth } from "./store/AuthContext";
import Sidebar from "./components/Sidebar";
import Dashboard from "./components/Dashboard";
import Documents from "./components/Documents";
import ChatPage from "./components/ChatPage";
import Users from "./components/Users";
import EvaluationDashboard from "./components/EvaluationDashboard";
import LoginPage from "./components/LoginPage";
import RegisterPage from "./components/RegisterPage";

function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center bg-white">
        <div className="w-6 h-6 border-2 border-[#2563EB] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return children;
}

function AppContent() {
  const [activeTab, setActiveTab] = useState("dashboard");
  const [dashboardRefreshKey, setDashboardRefreshKey] = useState(0);
  const { userRole } = useAuth();
  const isAdmin = userRole === "admin";

  const handleTabChange = (tab) => {
    setActiveTab(tab);
    // Increment refresh key when dashboard becomes active so it refetches data
    if (tab === "dashboard") {
      setDashboardRefreshKey((k) => k + 1);
    }
  };

  return (
    <div className="flex h-screen bg-white">
      <Sidebar activeTab={activeTab} onTabChange={handleTabChange} />
      <main className="flex-1 overflow-auto relative">
        <div className={activeTab === "dashboard" ? "h-full" : "hidden h-full"}>
          <Dashboard refreshKey={dashboardRefreshKey} onTabChange={handleTabChange} />
        </div>
        <div className={activeTab === "documents" ? "h-full" : "hidden h-full"}>
          <Documents />
        </div>
        <div className={activeTab === "chat" ? "h-full" : "hidden h-full"}>
          <ChatPage />
        </div>
        {isAdmin && (
          <div className={activeTab === "users" ? "h-full" : "hidden h-full"}>
            <Users />
          </div>
        )}
        {isAdmin && (
          <div className={activeTab === "evaluation" ? "h-full" : "hidden h-full"}>
            <EvaluationDashboard />
          </div>
        )}
      </main>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route
          path="/*"
          element={
            <ProtectedRoute>
              <AppContent />
            </ProtectedRoute>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}