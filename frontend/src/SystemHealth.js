import React, { useState, useEffect } from 'react'
import { getHealth } from './api.js'

export default function SystemHealth() {
  var [data, setData] = useState(null)
  var [error, setError] = useState(null)

  function refresh() {
    getHealth()
      .then(function(d) { setData(d); setError(null) })
      .catch(function(e) { setError(e.message) })
  }

  useEffect(function() {
    refresh()
    var id = setInterval(refresh, 15000)
    return function() { clearInterval(id) }
  }, [])

  if (error) return React.createElement('div', { className: 'alert alert-error' }, error)
  if (!data) return React.createElement('p', { className: 'loading' }, 'Loading system health...')

  var upHours = (data.uptime_seconds / 3600).toFixed(1)

  return React.createElement('div', null,

    React.createElement('div', { className: 'alert ' + (data.status === 'ok' ? 'alert-success' : 'alert-error') },
      'System status: ' + (data.status || 'unknown').toUpperCase()
    ),

    React.createElement('div', { className: 'grid-3', style: { marginBottom: '1.5rem' } },
      React.createElement('div', { className: 'kpi' },
        React.createElement('div', { className: 'kpi-label' }, 'Model Version'),
        React.createElement('div', { className: 'kpi-value', style: { fontSize: '1.4rem' } }, data.model_version || '—'),
        React.createElement('div', { className: 'kpi-sub' }, data.model_name || '')
      ),
      React.createElement('div', { className: 'kpi' },
        React.createElement('div', { className: 'kpi-label' }, 'CV AUC'),
        React.createElement('div', { className: 'kpi-value ' + (data.cv_auc >= 0.80 ? 'kpi-pass' : 'kpi-fail') },
          data.cv_auc ? data.cv_auc.toFixed(3) : '—'
        ),
        React.createElement('div', { className: 'kpi-sub' }, 'Target > 0.80')
      ),
      React.createElement('div', { className: 'kpi' },
        React.createElement('div', { className: 'kpi-label' }, 'Uptime'),
        React.createElement('div', { className: 'kpi-value', style: { fontSize: '1.4rem' } }, upHours + 'h'),
        React.createElement('div', { className: 'kpi-sub' }, data.uptime_seconds + 's')
      )
    ),

    React.createElement('div', { className: 'card' },
      React.createElement('h2', null, 'System Details'),
      React.createElement('table', null,
        React.createElement('tbody', null,
          [
            ['Features', data.n_features + ' (one-hot encoded)'],
            ['Database', data.database_url],
            ['Kafka', data.kafka_enabled ? 'Enabled' : 'Disabled (KAFKA_ENABLED=false)'],
            ['Status', data.status],
          ].map(function(row) {
            return React.createElement('tr', { key: row[0] },
              React.createElement('td', { style: { fontWeight: 600, width: '160px', color: '#4a5568' } }, row[0]),
              React.createElement('td', null, row[1])
            )
          })
        )
      )
    ),

    React.createElement('div', { style: { textAlign: 'right' } },
      React.createElement('button', { className: 'btn btn-secondary', onClick: refresh }, 'Refresh'),
      React.createElement('span', { style: { marginLeft: '0.5rem', fontSize: '0.78rem', color: '#9ca3af' } }, '(auto-refresh every 15s)')
    )
  )
}
