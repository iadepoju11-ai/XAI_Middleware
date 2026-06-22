import React, { useState, useEffect } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine, ResponsiveContainer, Cell } from 'recharts'
import { getFairness } from './api.js'

var THRESHOLD = 0.80
var REFRESH_MS = 10000

export default function FairnessMonitor() {
  var [data, setData] = useState(null)
  var [error, setError] = useState(null)
  var [lastUpdated, setLastUpdated] = useState(null)

  function refresh() {
    getFairness()
      .then(function(d) { setData(d); setLastUpdated(new Date()); setError(null) })
      .catch(function(e) { setError(e.message) })
  }

  useEffect(function() {
    refresh()
    var id = setInterval(refresh, REFRESH_MS)
    return function() { clearInterval(id) }
  }, [])

  var noData = !data || data.message
  var ratio = data && data.demographic_parity_ratio
  var dpDiff = data && data.demographic_parity_difference
  var eoDiff = data && data.equalized_odds_difference
  var alert = data && data.alert
  var rates = data && data.group_acceptance_rates ? Object.entries(data.group_acceptance_rates).map(function(e) {
    return { name: e[0] === '0' ? 'Female (0)' : 'Male (1)', rate: Math.round(e[1] * 100) }
  }) : []

  return React.createElement('div', null,

    alert && React.createElement('div', { className: 'alert alert-warn' },
      'Fairness alert: demographic parity ratio ' + (ratio ? ratio.toFixed(3) : '?') + ' is below threshold ' + THRESHOLD
    ),

    !alert && !noData && React.createElement('div', { className: 'alert alert-success' },
      'Fairness within threshold. Demographic parity ratio: ' + (ratio ? ratio.toFixed(3) : 'N/A')
    ),

    noData && React.createElement('div', { className: 'alert alert-info' },
      data ? data.message : 'Loading fairness data...'
    ),

    React.createElement('div', { className: 'grid-3', style: { marginBottom: '1.5rem' } },
      React.createElement('div', { className: 'kpi' },
        React.createElement('div', { className: 'kpi-label' }, 'Parity Ratio'),
        React.createElement('div', { className: 'kpi-value ' + (!ratio ? '' : ratio >= THRESHOLD ? 'kpi-pass' : 'kpi-fail') },
          ratio ? ratio.toFixed(3) : '—'
        ),
        React.createElement('div', { className: 'kpi-sub' }, 'Target ≥ ' + THRESHOLD)
      ),
      React.createElement('div', { className: 'kpi' },
        React.createElement('div', { className: 'kpi-label' }, 'Parity Difference'),
        React.createElement('div', { className: 'kpi-value ' + (dpDiff == null ? '' : Math.abs(dpDiff) <= 0.20 ? 'kpi-pass' : 'kpi-warn') },
          dpDiff != null ? dpDiff.toFixed(3) : '—'
        ),
        React.createElement('div', { className: 'kpi-sub' }, 'Target ≤ 0.20')
      ),
      React.createElement('div', { className: 'kpi' },
        React.createElement('div', { className: 'kpi-label' }, 'Equalised Odds Diff'),
        React.createElement('div', { className: 'kpi-value' }, eoDiff != null ? eoDiff.toFixed(3) : '—'),
        React.createElement('div', { className: 'kpi-sub' }, 'Informational')
      )
    ),

    rates.length > 0 && React.createElement('div', { className: 'card' },
      React.createElement('h2', null, 'Acceptance Rate by Sex (' + (data && data.n_decisions) + ' decisions in window)'),
      React.createElement(ResponsiveContainer, { width: '100%', height: 250 },
        React.createElement(BarChart, { data: rates, margin: { top: 10, right: 20, bottom: 5, left: 0 } },
          React.createElement(CartesianGrid, { strokeDasharray: '3 3', stroke: '#f0f4f8' }),
          React.createElement(XAxis, { dataKey: 'name' }),
          React.createElement(YAxis, { domain: [0, 100], tickFormatter: function(v) { return v + '%' } }),
          React.createElement(Tooltip, { formatter: function(v) { return v + '%' } }),
          React.createElement(ReferenceLine, { y: THRESHOLD * 100, stroke: '#e94560', strokeDasharray: '4 4', label: 'Threshold' }),
          React.createElement(Bar, { dataKey: 'rate', name: 'Acceptance Rate' },
            rates.map(function(entry, i) {
              return React.createElement(Cell, { key: i, fill: entry.rate >= THRESHOLD * 100 ? '#10b981' : '#ef4444' })
            })
          )
        )
      )
    ),

    React.createElement('div', { style: { fontSize: '0.78rem', color: '#9ca3af', textAlign: 'right' } },
      lastUpdated ? 'Last updated: ' + lastUpdated.toLocaleTimeString() : '',
      ' (auto-refresh every 10s) ',
      React.createElement('button', { className: 'btn btn-secondary', style: { padding: '0.2rem 0.7rem', fontSize: '0.78rem', marginLeft: '0.5rem' }, onClick: refresh }, 'Refresh')
    )
  )
}
