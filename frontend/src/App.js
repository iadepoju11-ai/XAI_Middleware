import React from 'react'
import { BrowserRouter, NavLink, Route, Routes } from 'react-router-dom'
import Dashboard from './Dashboard.js'
import AuditPanel from './AuditPanel.js'

const Placeholder = ({ title }) => (
  <div style={{ padding: '2rem' }}>
    <h2>{title}</h2>
    <p>Coming in Phase 6.</p>
  </div>
)

export default function App() {
  return (
    <BrowserRouter>
      <nav style={{ background: '#1a1a2e', padding: '1rem 2rem', display: 'flex', gap: '1.5rem', alignItems: 'center' }}>
        <span style={{ color: '#e94560', fontWeight: 700, marginRight: '1rem' }}>XAI Compliance</span>
        {['/', '/fairness', '/audit', '/health'].map((path, i) => (
          <NavLink
            key={path}
            to={path}
            end={path === '/'}
            style={({ isActive }) => ({ color: isActive ? '#e94560' : '#ccc', textDecoration: 'none' })}
          >
            {['Credit Scoring', 'Fairness Monitor', 'Audit Trail', 'System Health'][i]}
          </NavLink>
        ))}
      </nav>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/fairness" element={<Placeholder title="Fairness Monitor" />} />
        <Route path="/audit" element={<AuditPanel />} />
        <Route path="/health" element={<Placeholder title="System Health" />} />
      </Routes>
    </BrowserRouter>
  )
}
