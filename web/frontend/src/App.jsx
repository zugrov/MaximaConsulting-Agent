import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { useAuthStore } from './store/authStore'
import Layout from './components/Layout'
import LoginPage from './pages/LoginPage'
import AnalysisPage from './pages/AnalysisPage'
import HistoryPage from './pages/HistoryPage'
import AdminPage from './pages/AdminPage'
import ClientsPage from './pages/ClientsPage'
import ClientCard from './pages/ClientCard'

function ProtectedRoute({ children, requiredRole }) {
  const user = useAuthStore((s) => s.user)
  if (!user) return <Navigate to="/login" replace />
  if (requiredRole && user.role !== requiredRole) return <Navigate to="/" replace />
  return children
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <Layout />
            </ProtectedRoute>
          }
        >
          <Route index element={<Navigate to="/analysis" replace />} />
          <Route path="analysis" element={<AnalysisPage />} />
          <Route path="history" element={<HistoryPage />} />
          <Route path="clients" element={<ClientsPage />} />
          <Route path="clients/:id" element={<ClientCard />} />
          <Route
            path="admin"
            element={
              <ProtectedRoute requiredRole="admin">
                <AdminPage />
              </ProtectedRoute>
            }
          />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
