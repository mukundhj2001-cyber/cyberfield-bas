import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import { ToastProvider } from './components/Toast'
import { Dashboard } from './pages/Dashboard'
import { Emails } from './pages/Emails'
import { Approvals } from './pages/Approvals'
import { Crm } from './pages/Crm'
import { Tasks } from './pages/Tasks'
import { Tickets } from './pages/Tickets'
import { Agents } from './pages/Agents'
import { Workflows } from './pages/Workflows'

export default function App() {
  return (
    <ToastProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="emails" element={<Emails />} />
            <Route path="approvals" element={<Approvals />} />
            <Route path="approvals/:id" element={<Approvals />} />
            <Route path="crm" element={<Crm />} />
            <Route path="tickets" element={<Tickets />} />
            <Route path="tasks" element={<Tasks />} />
            <Route path="agents" element={<Agents />} />
            <Route path="workflows" element={<Workflows />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ToastProvider>
  )
}
