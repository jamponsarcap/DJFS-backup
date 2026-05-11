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

export interface UploadHistoryEntry {
  filename: string
  uploaded_at: string
  lakehouse_path?: string
}

export const fetchUploadHistory = (clientId: string): Promise<UploadHistoryEntry[]> =>
  api.get(`/upload-statement/${clientId}/last`).then(r => r.data ?? [])

export const undoLastUpload = (clientId: string): Promise<{ status: string; filename: string }> =>
  api.post(`/upload-statement/${clientId}/undo`).then(r => r.data)

export interface MarketRefreshResult {
  refreshed_at: string
  next_refresh_allowed: string
  holdings_updated: number
}

export const refreshMarketData = (): Promise<MarketRefreshResult> =>
  api.post('/market-data/refresh').then(r => r.data)

export interface HoldingsHistorySeries {
  symbol: string
  name: string
  asset_class: string
  values: number[]
}

export interface HoldingsHistory {
  dates: string[]
  series: HoldingsHistorySeries[]
}

export const fetchHoldingsHistory = (clientId: string): Promise<HoldingsHistory> =>
  api.get(`/holdings-history/${clientId}`).then(r => r.data)

export interface LakehouseDocument {
  path: string
  name: string
  size: number
  last_modified: string | null
  locked: boolean
}

export const fetchDocuments = (clientId: string): Promise<LakehouseDocument[]> =>
  api.get(`/documents/${clientId}`).then(r => r.data)

export const lockDocument = (clientId: string, path: string): Promise<{ locked: boolean }> =>
  api.post(`/documents/${clientId}/lock`, { path }).then(r => r.data)

export const unlockDocument = (clientId: string, path: string): Promise<{ locked: boolean }> =>
  api.post(`/documents/${clientId}/unlock`, { path }).then(r => r.data)

export const deleteDocument = (clientId: string, path: string): Promise<{ deleted: boolean }> =>
  api.post(`/documents/${clientId}/delete`, { path }).then(r => r.data)

export const fetchRefreshStatus = (): Promise<{
  last_refreshed: string | null
  next_refresh_allowed: string | null
  cooldown_remaining: number
}> => api.get('/market-data/refresh-status').then(r => r.data)
