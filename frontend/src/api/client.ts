import axios from 'axios'
import type { Client, PortfolioData, InsightsResponse, ServiceStatus, DocumentUploadResponse } from '../types'

const api = axios.create({ baseURL: '/api' })

export const fetchClients = (): Promise<Client[]> =>
  api.get('/clients').then(r => r.data)

export const fetchPortfolio = (clientId: string): Promise<PortfolioData> =>
  api.get(`/portfolio/${clientId}`).then(r => r.data)

export const fetchInsights = (clientId: string): Promise<InsightsResponse> =>
  api.get(`/insights/${clientId}`).then(r => r.data)

export const fetchStatus = (): Promise<ServiceStatus> =>
  api.get('/status').then(r => r.data)

export const uploadStatement = (clientId: string, file: File): Promise<DocumentUploadResponse> => {
  const form = new FormData()
  form.append('file', file)
  return api.post(`/upload-statement/${clientId}`, form).then(r => r.data)
}
