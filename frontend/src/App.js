import React, { useState } from 'react'
import { BrowserRouter, NavLink, Route, Routes } from 'react-router-dom'
import Dashboard from './Dashboard.js'
import AuditPanel from './AuditPanel.js'
import FairnessMonitor from './FairnessMonitor.js'
import SystemHealth from './SystemHealth.js'
import './App.css'

const NAV = [
  { to: '/', label: 'Credit Scoring', end: true },
  { to: '/fairness', label: 'Fairness Monitor', end: false },
  { to: '/audit', label: 'Audit Trail', end: false },
  { to: '/health', label: 'System Health', end: false },
]

export default function App() {
  return React.createElement(BrowserRouter, null,
    React.createElement('div', { className: 'app' },
      React.createElement('nav', { className: 'navbar' },
        React.createElement('span', { className: 'brand' }, 'XAI Compliance Dashboard'),
        React.createElement('div', { className: 'nav-links' },
          ...NAV.map(function(item) {
            return React.createElement(NavLink, {
              key: item.to,
              to: item.to,
              end: item.end,
              className: function(p) { return 'nav-link' + (p.isActive ? ' active' : '') }
            }, item.label)
          })
        )
      ),
      React.createElement('main', { className: 'main-content' },
        React.createElement(Routes, null,
          React.createElement(Route, { path: '/', element: React.createElement(Dashboard, null) }),
          React.createElement(Route, { path: '/fairness', element: React.createElement(FairnessMonitor, null) }),
          React.createElement(Route, { path: '/audit', element: React.createElement(AuditPanel, null) }),
          React.createElement(Route, { path: '/health', element: React.createElement(SystemHealth, null) })
        )
      )
    )
  )
}
