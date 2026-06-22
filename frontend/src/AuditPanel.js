import React, { useState, useEffect } from 'react'
import { getAuditList, getAuditById, exportAudit } from './api.js'

export default function AuditPanel() {
  var [records, setRecords] = useState([])
  var [total, setTotal] = useState(0)
  var [page, setPage] = useState(1)
  var [filters, setFilters] = useState({ decision: '', date_from: '', date_to: '', search_id: '' })
  var [expanded, setExpanded] = useState(null)
  var [expandedData, setExpandedData] = useState(null)
  var [loading, setLoading] = useState(false)
  var [error, setError] = useState(null)
  var PAGE_SIZE = 20

  function loadRecords(pg, f) {
    setLoading(true)
    var params = { page: pg, page_size: PAGE_SIZE }
    if (f.decision) params.decision = f.decision
    if (f.date_from) params.date_from = f.date_from
    if (f.date_to) params.date_to = f.date_to
    getAuditList(params)
      .then(function(d) { setRecords(d.records || []); setTotal(d.total || 0); setLoading(false) })
      .catch(function(e) { setError(e.message); setLoading(false) })
  }

  useEffect(function() { loadRecords(1, filters) }, [])

  function handleFilter(e) {
    setFilters(function(prev) { return Object.assign({}, prev, { [e.target.name]: e.target.value }) })
  }

  function handleSearch(e) {
    e.preventDefault()
    if (filters.search_id) {
      setLoading(true)
      getAuditById(filters.search_id)
        .then(function(d) { setRecords([d]); setTotal(1); setLoading(false) })
        .catch(function(e) { setError(e.message); setLoading(false) })
    } else {
      setPage(1)
      loadRecords(1, filters)
    }
  }

  function toggleExpand(id) {
    if (expanded === id) { setExpanded(null); return }
    setExpanded(id)
    getAuditById(id).then(setExpandedData).catch(function() {})
  }

  function handleExport(fmt) {
    exportAudit(fmt).then(function(data) {
      if (fmt === 'json') {
        var blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
        var url = URL.createObjectURL(blob)
        var a = document.createElement('a'); a.href = url; a.download = 'audit_export.json'; a.click()
      } else {
        var blob = new Blob([data], { type: 'text/csv' })
        var url = URL.createObjectURL(blob)
        var a = document.createElement('a'); a.href = url; a.download = 'audit_export.csv'; a.click()
      }
    })
  }

  function changePage(p) { setPage(p); loadRecords(p, filters) }

  var totalPages = Math.ceil(total / PAGE_SIZE)

  return React.createElement('div', null,

    React.createElement('div', { className: 'card' },
      React.createElement('h2', null, 'Search & Filter'),
      React.createElement('form', { onSubmit: handleSearch, style: { display: 'flex', gap: '1rem', flexWrap: 'wrap', alignItems: 'flex-end' } },
        React.createElement('div', { className: 'form-group', style: { flex: '1', minWidth: '180px' } },
          React.createElement('label', null, 'Application ID'),
          React.createElement('input', { type: 'text', name: 'search_id', placeholder: 'Paste UUID...', value: filters.search_id, onChange: handleFilter })
        ),
        React.createElement('div', { className: 'form-group', style: { minWidth: '120px' } },
          React.createElement('label', null, 'Decision'),
          React.createElement('select', { name: 'decision', value: filters.decision, onChange: handleFilter },
            React.createElement('option', { value: '' }, 'All'),
            React.createElement('option', { value: 'accept' }, 'Accept'),
            React.createElement('option', { value: 'deny' }, 'Deny')
          )
        ),
        React.createElement('div', { className: 'form-group', style: { minWidth: '140px' } },
          React.createElement('label', null, 'From'),
          React.createElement('input', { type: 'date', name: 'date_from', value: filters.date_from, onChange: handleFilter })
        ),
        React.createElement('div', { className: 'form-group', style: { minWidth: '140px' } },
          React.createElement('label', null, 'To'),
          React.createElement('input', { type: 'date', name: 'date_to', value: filters.date_to, onChange: handleFilter })
        ),
        React.createElement('button', { type: 'submit', className: 'btn btn-primary' }, 'Search'),
        React.createElement('button', { type: 'button', className: 'btn btn-secondary', onClick: function() { handleExport('csv') } }, 'Export CSV'),
        React.createElement('button', { type: 'button', className: 'btn btn-secondary', onClick: function() { handleExport('json') } }, 'Export JSON')
      )
    ),

    error && React.createElement('div', { className: 'alert alert-error' }, error),

    React.createElement('div', { className: 'card' },
      React.createElement('h2', null, 'Decisions (' + total + ' total)'),
      loading ? React.createElement('p', { className: 'loading' }, 'Loading...') :
        records.length === 0 ? React.createElement('p', { className: 'empty' }, 'No records found.') :
        React.createElement('div', { className: 'table-wrap' },
          React.createElement('table', null,
            React.createElement('thead', null,
              React.createElement('tr', null,
                ['Application ID', 'Timestamp', 'Decision', 'Probability', 'Model Version', ''].map(function(h) {
                  return React.createElement('th', { key: h }, h)
                })
              )
            ),
            React.createElement('tbody', null,
              records.map(function(r) {
                return React.createElement(React.Fragment, { key: r.application_id },
                  React.createElement('tr', { style: { cursor: 'pointer' }, onClick: function() { toggleExpand(r.application_id) } },
                    React.createElement('td', null, React.createElement('code', { style: { fontSize: '0.8rem' } }, r.application_id.slice(0, 12) + '...')),
                    React.createElement('td', null, new Date(r.timestamp).toLocaleString()),
                    React.createElement('td', null, React.createElement('span', { className: 'badge ' + (r.decision === 'accept' ? 'badge-accept' : 'badge-deny') }, r.decision)),
                    React.createElement('td', null, (r.probability * 100).toFixed(1) + '%'),
                    React.createElement('td', null, r.model_version),
                    React.createElement('td', null, React.createElement('span', { style: { color: '#e94560', fontSize: '0.8rem' } }, expanded === r.application_id ? 'Hide' : 'Details'))
                  ),
                  expanded === r.application_id && expandedData && React.createElement('tr', null,
                    React.createElement('td', { colSpan: 6, style: { background: '#f8fafc', padding: '1rem' } },
                      React.createElement('div', { style: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' } },
                        React.createElement('div', null,
                          React.createElement('strong', null, 'Input Features'),
                          React.createElement('pre', { style: { fontSize: '0.78rem', marginTop: '0.4rem', whiteSpace: 'pre-wrap' } },
                            JSON.stringify(expandedData.input_features, null, 2)
                          )
                        ),
                        React.createElement('div', null,
                          React.createElement('strong', null, 'SHAP Values (top 5)'),
                          React.createElement('pre', { style: { fontSize: '0.78rem', marginTop: '0.4rem', whiteSpace: 'pre-wrap' } },
                            JSON.stringify(
                              Object.fromEntries(
                                Object.entries(expandedData.shap_values || {})
                                  .sort(function(a, b) { return Math.abs(b[1]) - Math.abs(a[1]) })
                                  .slice(0, 5)
                                  .map(function(e) { return [e[0], e[1].toFixed(4)] })
                              ), null, 2
                            )
                          ),
                          expandedData.fairness_flags && React.createElement('div', { style: { marginTop: '0.5rem' } },
                            React.createElement('strong', null, 'Fairness at Decision Time'),
                            React.createElement('pre', { style: { fontSize: '0.78rem', marginTop: '0.4rem', whiteSpace: 'pre-wrap' } },
                              JSON.stringify(expandedData.fairness_flags, null, 2)
                            )
                          )
                        )
                      )
                    )
                  )
                )
              })
            )
          ),

          totalPages > 1 && React.createElement('div', { style: { display: 'flex', gap: '0.5rem', marginTop: '1rem', justifyContent: 'center' } },
            React.createElement('button', { className: 'btn btn-secondary', onClick: function() { changePage(page - 1) }, disabled: page === 1 }, 'Prev'),
            React.createElement('span', { style: { padding: '0.5rem 1rem', fontSize: '0.88rem' } }, 'Page ' + page + ' / ' + totalPages),
            React.createElement('button', { className: 'btn btn-secondary', onClick: function() { changePage(page + 1) }, disabled: page === totalPages }, 'Next')
          )
        )
    )
  )
}
