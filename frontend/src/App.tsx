import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { useEffect } from "react";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { ThemeProvider } from "@/context/ThemeContext";

import Index from "./pages/Index";
import Login from "./pages/Login";
import Register from "./pages/Register";
import VerifyOtp from "./pages/VerifyOtp";
import ChatNewV2 from "./pages/ChatNewV2";
import CasePredictor from "./pages/CasePredictor";
import PredictionHistory from "./pages/PredictionHistory";
import PredictionDetail from "./pages/PredictionDetail";
import RightsPage from "./pages/Rights";
import SharedConversation from "./pages/SharedConversation";
import NotFound from "./pages/NotFound";
import Privacy from "./pages/Privacy";
import Terms from "./pages/Terms";
import Disclaimer from "./pages/Disclaimer";
import MediationHome from "./pages/mediation/MediationHome";
import MediationHistory from "./pages/mediation/MediationHistory";
import CreateDispute from "./pages/mediation/CreateDispute";
import DisputeRoom from "./pages/mediation/DisputeRoom";
import DisputeResult from "./pages/mediation/DisputeResult";
import AboutUs from "./pages/AboutUs";

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
  <ThemeProvider>
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <Toaster />
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
              <Route path="/about"        element={<AboutUs />} />
              <Route path="/shared/:token" element={<SharedConversation />} />
              <Route path="/privacy"      element={<Privacy />} />
              <Route path="/terms"        element={<Terms />} />
              <Route path="/disclaimer"   element={<Disclaimer />} />

              {/* Protected routes */}
              <Route path="/chat"    element={<ProtectedRoute><ChatNewV2 /></ProtectedRoute>} />
              <Route path="/predict"      element={<ProtectedRoute><CasePredictor /></ProtectedRoute>} />
              <Route path="/predictions"  element={<ProtectedRoute><PredictionHistory /></ProtectedRoute>} />
              <Route path="/predictions/:id" element={<ProtectedRoute><PredictionDetail /></ProtectedRoute>} />

              {/* Mediation routes — all protected */}
              <Route path="/mediation"              element={<ProtectedRoute><MediationHome /></ProtectedRoute>} />
              <Route path="/mediation/history"      element={<ProtectedRoute><MediationHistory /></ProtectedRoute>} />
              <Route path="/mediation/create"       element={<ProtectedRoute><CreateDispute /></ProtectedRoute>} />
              <Route path="/mediation/:id/room"     element={<ProtectedRoute><DisputeRoom /></ProtectedRoute>} />
              <Route path="/mediation/:id/result"   element={<ProtectedRoute><DisputeResult /></ProtectedRoute>} />

              <Route path="*" element={<NotFound />} />
            </Routes>
          </AuthProvider>
        </BrowserRouter>
      </TooltipProvider>
    </QueryClientProvider>
  </ThemeProvider>
);

export default App;
