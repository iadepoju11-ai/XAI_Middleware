import axios from 'axios'

const client = axios.create({ baseURL: '/api' })

const extractError = (err) =>
  err?.response?.data?.error ?? err?.message ?? 'Unknown error'

export const scoreApplication = (payload) =>
  client.post('/score', payload).then((r) => r.data).catch((e) => { throw new Error(extractError(e)) })

export const getAuditList = (params = {}) =>
  client.get('/audit', { params }).then((r) => r.data).catch((e) => { throw new Error(extractError(e)) })

export const getAuditById = (applicationId) =>
  client.get(`/audit/${applicationId}`).then((r) => r.data).catch((e) => { throw new Error(extractError(e)) })

export const exportAudit = (format = 'json') =>
  client.get('/audit/export', { params: { format }, responseType: format === 'csv' ? 'blob' : 'json' })
    .then((r) => r.data).catch((e) => { throw new Error(extractError(e)) })

export const getFairness = () =>
  client.get('/fairness').then((r) => r.data).catch((e) => { throw new Error(extractError(e)) })

export const getHealth = () =>
  client.get('/health').then((r) => r.data).catch((e) => { throw new Error(extractError(e)) })
