import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { useEffect } from "react";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import { ProtectedRoute } from "@/components/ProtectedRoute";

import Index from "./pages/Index";
import Login from "./pages/Login";
import Register from "./pages/Register";
import VerifyOtp from "./pages/VerifyOtp";
import UploadPage from "./pages/Upload";
import ChatNewV2 from "./pages/ChatNewV2";
import CasePredictor from "./pages/CasePredictor";
import PredictionHistory from "./pages/PredictionHistory";
import RightsPage from "./pages/Rights";
import NotFound from "./pages/NotFound";
import MediationHome from "./pages/mediation/MediationHome";
import CreateDispute from "./pages/mediation/CreateDispute";
import DisputeRoom from "./pages/mediation/DisputeRoom";
import DisputeResult from "./pages/mediation/DisputeResult";

const queryClient = new QueryClient();

function AuthWatcher() {
  const { logout } = useAuth();
  useEffect(() => {
    const handler = () => logout();
    window.addEventListener('sla:unauthorized', handler);
    return () => window.removeEventListener('sla:unauthorized', handler);
  }, [logout]);
  return null;
}

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <AuthProvider>
          <AuthWatcher />
          <Routes>
            {/* Public routes */}
            <Route path="/"             element={<Index />} />
            <Route path="/login"        element={<Login />} />
            <Route path="/register"     element={<Register />} />
            <Route path="/verify-otp"   element={<VerifyOtp />} />
            <Route path="/rights"       element={<RightsPage />} />

            {/* Protected routes */}
            <Route path="/chat"    element={<ProtectedRoute><ChatNewV2 /></ProtectedRoute>} />
            <Route path="/predict"      element={<ProtectedRoute><CasePredictor /></ProtectedRoute>} />
            <Route path="/predictions"  element={<ProtectedRoute><PredictionHistory /></ProtectedRoute>} />
            <Route path="/upload"  element={<ProtectedRoute><UploadPage /></ProtectedRoute>} />

            {/* Mediation routes — all protected */}
            <Route path="/mediation"              element={<ProtectedRoute><MediationHome /></ProtectedRoute>} />
            <Route path="/mediation/create"       element={<ProtectedRoute><CreateDispute /></ProtectedRoute>} />
            <Route path="/mediation/:id/room"     element={<ProtectedRoute><DisputeRoom /></ProtectedRoute>} />
            <Route path="/mediation/:id/result"   element={<ProtectedRoute><DisputeResult /></ProtectedRoute>} />

            <Route path="*" element={<NotFound />} />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
