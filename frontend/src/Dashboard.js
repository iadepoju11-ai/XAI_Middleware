import React, { useState } from 'react'
import { scoreApplication } from './api.js'

var PURPOSES = ['car','furniture/equipment','radio/tv','domestic appliance','repairs','education','business','vacation/others']
var EMPLOYMENTS = ['unemployed','<1','1<=X<4','4<=X<7','>=7']

function ShapWaterfall(props) {
  var factors = props.factors
  if (!factors) return null
  var all = (factors.positive || []).concat(factors.negative || [])
  if (all.length === 0) return React.createElement('p', { className: 'empty' }, 'No SHAP values available')

  var maxAbs = Math.max.apply(null, all.map(function(f) { return Math.abs(f.value) })) || 1

  return React.createElement('div', null,
    all.map(function(f) {
      var pct = Math.round((Math.abs(f.value) / maxAbs) * 100)
      var isPos = f.value >= 0
      return React.createElement('div', { key: f.feature, className: 'shap-bar-row' },
        React.createElement('span', { className: 'shap-label', title: f.feature }, f.feature),
        React.createElement('div', { className: 'shap-bar-track' },
          React.createElement('div', {
            className: isPos ? 'shap-bar-fill-pos' : 'shap-bar-fill-neg',
            style: { width: pct + '%' }
          })
        ),
        React.createElement('span', { className: 'shap-val' }, (f.value > 0 ? '+' : '') + f.value.toFixed(3))
      )
    })
  )
}

var FORM_DEFAULTS = { credit_amount: 5000, duration: 12, age: 30, purpose: 'car', employment: '1<=X<4', existing_credits: 1, sex: 0 }

export default function Dashboard() {
  var [form, setForm] = useState(FORM_DEFAULTS)
  var [result, setResult] = useState(null)
  var [loading, setLoading] = useState(false)
  var [error, setError] = useState(null)

  function handleChange(e) {
    var val = e.target.type === 'number' ? Number(e.target.value) : e.target.value
    setForm(function(prev) { return Object.assign({}, prev, { [e.target.name]: val }) })
  }

  function handleSubmit(e) {
    e.preventDefault()
    setLoading(true)
    setError(null)
    scoreApplication(form)
      .then(function(data) { setResult(data); setLoading(false) })
      .catch(function(err) { setError(err.message); setLoading(false) })
  }

  var probPct = result ? Math.round(result.probability * 100) : 0
  var fairAlert = result && result.fairness_flags && result.fairness_flags.alert

  return React.createElement('div', null,
    React.createElement('div', { className: 'grid-2' },

      // --- Input form ---
      React.createElement('div', { className: 'card' },
        React.createElement('h2', null, 'Application Details'),
        React.createElement('form', { onSubmit: handleSubmit },
          React.createElement('div', { className: 'grid-2' },
            React.createElement('div', { className: 'form-group' },
              React.createElement('label', null, 'Credit Amount (DM)'),
              React.createElement('input', { type: 'number', name: 'credit_amount', value: form.credit_amount, onChange: handleChange, min: 1, required: true })
            ),
            React.createElement('div', { className: 'form-group' },
              React.createElement('label', null, 'Duration (months)'),
              React.createElement('input', { type: 'number', name: 'duration', value: form.duration, onChange: handleChange, min: 1, required: true })
            ),
            React.createElement('div', { className: 'form-group' },
              React.createElement('label', null, 'Age'),
              React.createElement('input', { type: 'number', name: 'age', value: form.age, onChange: handleChange, min: 18, max: 120, required: true })
            ),
            React.createElement('div', { className: 'form-group' },
              React.createElement('label', null, 'Existing Credits'),
              React.createElement('input', { type: 'number', name: 'existing_credits', value: form.existing_credits, onChange: handleChange, min: 1 })
            )
          ),
          React.createElement('div', { className: 'form-group' },
            React.createElement('label', null, 'Purpose'),
            React.createElement('select', { name: 'purpose', value: form.purpose, onChange: handleChange },
              PURPOSES.map(function(p) { return React.createElement('option', { key: p, value: p }, p) })
            )
          ),
          React.createElement('div', { className: 'form-group' },
            React.createElement('label', null, 'Employment Duration'),
            React.createElement('select', { name: 'employment', value: form.employment, onChange: handleChange },
              EMPLOYMENTS.map(function(e) { return React.createElement('option', { key: e, value: e }, e === 'unemployed' ? 'Unemployed' : e + ' years') })
            )
          ),
          React.createElement('div', { className: 'form-group' },
            React.createElement('label', null, 'Sex (fairness attribute only)'),
            React.createElement('select', { name: 'sex', value: form.sex, onChange: handleChange },
              React.createElement('option', { value: 0 }, 'Female (0)'),
              React.createElement('option', { value: 1 }, 'Male (1)')
            )
          ),
          React.createElement('button', { type: 'submit', className: 'btn btn-primary', disabled: loading },
            loading ? 'Scoring...' : 'Submit Application'
          )
        )
      ),

      // --- Result panel ---
      React.createElement('div', { className: 'card' },
        React.createElement('h2', null, 'Decision Result'),

        error && React.createElement('div', { className: 'alert alert-error' }, error),

        !result && !error && React.createElement('p', { className: 'empty' }, 'Submit an application to see results.'),

        result && React.createElement('div', null,
          React.createElement('div', { style: { marginBottom: '1rem' } },
            React.createElement('span', { className: 'badge ' + (result.decision === 'accept' ? 'badge-accept' : 'badge-deny') },
              result.decision.toUpperCase()
            ),
            React.createElement('span', { style: { marginLeft: '1rem', fontSize: '0.88rem', color: '#6b7280' } },
              'ID: ' + result.application_id.slice(0, 8) + '...'
            )
          ),

          React.createElement('div', { style: { marginBottom: '1rem' } },
            React.createElement('div', { style: { fontWeight: 600 } }, 'Probability: ' + probPct + '%'),
            React.createElement('div', { className: 'prob-meter' },
              React.createElement('div', {
                className: 'prob-fill',
                style: { width: probPct + '%', background: result.decision === 'accept' ? '#10b981' : '#ef4444' }
              })
            )
          ),

          React.createElement('div', { style: { marginBottom: '0.5rem', fontWeight: 600, fontSize: '0.88rem' } }, 'SHAP Explanation — Top Factors'),
          React.createElement(ShapWaterfall, { factors: result.top_factors }),

          React.createElement('div', { style: { marginTop: '1rem' } },
            fairAlert
              ? React.createElement('div', { className: 'alert alert-warn' }, 'Fairness alert: demographic parity ratio below 0.80')
              : React.createElement('div', { className: 'alert alert-success' }, 'Fairness: no flag (parity within threshold)')
          ),

          React.createElement('div', { style: { fontSize: '0.78rem', color: '#9ca3af', marginTop: '0.5rem' } },
            'Model v' + result.model_version + '  |  Latency: ' + result.latency_ms + 'ms'
          )
        )
      )
    )
  )
}
