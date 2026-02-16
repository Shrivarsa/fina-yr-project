import { Routes, Route, Navigate } from "react-router-dom";
import { useAuth } from "./AuthContext";   // ✅ FIXED
import AuthPage from "./AuthPage";
import SCIPDashboard from "./SCIPDashboard";
import Home from "./Home";
import Loader from "./Loader";

function ProtectedRoute({ children }: { children: React.ReactElement }) {

  const { user, isInitialized } = useAuth();

  if (!isInitialized) {
    return <Loader />;
  }

  return user ? children : <Navigate to="/login" replace />;
}

export default function App() {

  const { user, isInitialized } = useAuth();

  if (!isInitialized) {
    return <Loader />;
  }

  return (
    <Routes>

      <Route
        path="/login"
        element={
          user
            ? <Navigate to="/home" replace />
            : <AuthPage />
        }
      />

      <Route
        path="/home"
        element={
          <ProtectedRoute>
            <Home />
          </ProtectedRoute>
        }
      />

      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <SCIPDashboard />
          </ProtectedRoute>
        }
      />

      <Route
        path="*"
        element={
          <Navigate to={user ? "/home" : "/login"} replace />
        }
      />

    </Routes>
  );
}
