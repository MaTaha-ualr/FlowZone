import { useCallback, useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ArrowLeft, Upload, Search, FileText, X, ChevronRight, AlertTriangle, CheckCircle, Loader2, FileImage, File } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import type { DocumentItem } from '@/types'
import { getDocuments, searchDocuments, uploadDocument } from '@/lib/api'
import { useAuth } from '@/context/AuthContext'

const MOCK_DOCS: DocumentItem[] = [
  { id: '1', user_id: 'u1', name: 'Court Order — Case #2024-1187.pdf', type: 'pdf', status: 'verified', uploaded_at: '2024-11-15T10:00:00Z', url: '#', rag_snippets: ['"Defendant shall complete 40 hours of community service"', '"Curfew set to 9:00 PM weekdays"'] },
  { id: '2', user_id: 'u1', name: 'School Transcript — Fall 2024.pdf', type: 'pdf', status: 'verified', uploaded_at: '2024-12-01T14:30:00Z', url: '#' },
  { id: '3', user_id: 'u1', name: 'Mentor Meeting Notes — Jan 2025.pdf', type: 'pdf', status: 'processing', uploaded_at: '2025-01-10T09:00:00Z' },
  { id: '4', user_id: 'u1', name: 'ID Photo.jpg', type: 'image', status: 'verified', uploaded_at: '2024-10-20T16:00:00Z', url: '#' },
]

const STATUS_ICON: Record<string, typeof CheckCircle> = {
  verified: CheckCircle,
  processing: Loader2,
  uploaded: File,
  rejected: AlertTriangle,
}

const STATUS_COLOR: Record<string, string> = {
  verified: '#10B981',
  processing: '#00A8E8',
  uploaded: '#A1A1AA',
  rejected: '#DC2626',
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' ? value as Record<string, unknown> : {}
}

function stringValue(value: unknown, fallback = ''): string {
  return typeof value === 'string' && value.length > 0 ? value : fallback
}

function documentTypeFromName(filename: string): DocumentItem['type'] {
  const ext = filename.split('.').pop()?.toLowerCase()
  if (ext === 'jpg' || ext === 'jpeg' || ext === 'png') return 'image'
  if (ext === 'txt') return 'txt'
  if (ext === 'doc' || ext === 'docx') return 'doc'
  return 'pdf'
}

function documentStatus(status: unknown): DocumentItem['status'] {
  if (status === 'verified' || status === 'processing' || status === 'uploaded' || status === 'rejected') return status
  return 'uploaded'
}

function snippetsFrom(value: unknown): string[] | undefined {
  if (!Array.isArray(value)) return undefined
  const snippets = value.filter((item): item is string => typeof item === 'string')
  return snippets.length > 0 ? snippets : undefined
}

function documentFromApi(doc: unknown): DocumentItem {
  const record = asRecord(doc)
  const filename = stringValue(record.name, stringValue(record.filename, 'Document'))
  return {
    id: stringValue(record.id, crypto.randomUUID()),
    user_id: stringValue(record.user_id),
    name: filename,
    type: documentTypeFromName(filename),
    status: documentStatus(record.status || record.processing_status),
    uploaded_at: stringValue(record.uploaded_at, stringValue(record.created_at, new Date().toISOString())),
    url: stringValue(record.url) || undefined,
    rag_snippets: snippetsFrom(record.rag_snippets),
  }
}

export default function Documents() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const [docs, setDocs] = useState<DocumentItem[]>(MOCK_DOCS)
  const [query, setQuery] = useState('')
  const [dragOver, setDragOver] = useState(false)
  const [selectedDoc, setSelectedDoc] = useState<DocumentItem | null>(null)
  const [searchResults, setSearchResults] = useState<DocumentItem[] | null>(null)

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(true)
  }, [])

  useEffect(() => {
    if (!user?.id) return
    getDocuments(user.id)
      .then((data) => {
        const mapped = Array.isArray(data) ? data.map(documentFromApi) : []
        if (mapped.length > 0) setDocs(mapped)
      })
      .catch(() => undefined)
  }, [user?.id])

  const addLocalDoc = useCallback((file: globalThis.File) => {
    const newDoc: DocumentItem = {
      id: `new-${Date.now()}`,
      user_id: user?.id || 'local',
      name: file.name,
      type: file.type.startsWith('image/') ? 'image' : documentTypeFromName(file.name),
      status: 'uploaded',
      uploaded_at: new Date().toISOString(),
    }
    setDocs((prev) => [newDoc, ...prev])
  }, [user?.id])

  const handleFile = useCallback(async (file: globalThis.File) => {
    try {
      if (user?.id) {
        const uploaded = await uploadDocument(user.id, file)
        setDocs((prev) => [documentFromApi(uploaded), ...prev])
        return
      }
    } catch {
      // local visual fallback
    }
    addLocalDoc(file)
  }, [addLocalDoc, user?.id])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer.files[0]
    if (file) {
      void handleFile(file)
    }
  }, [handleFile])

  const handleSearch = async () => {
    if (!query.trim()) {
      setSearchResults(null)
      return
    }
    try {
      if (user?.id) {
        const result = asRecord(await searchDocuments(user.id, query))
        const resultItems = Array.isArray(result.results) ? result.results : []
        const snippets = resultItems
          .map((item) => stringValue(asRecord(item).text))
          .filter(Boolean)
        if (snippets.length > 0) {
          setSearchResults([{
            id: 'rag-search',
            user_id: user.id,
            name: `RAG results for "${query}"`,
            type: 'txt',
            status: 'verified',
            uploaded_at: new Date().toISOString(),
            rag_snippets: snippets,
          }])
          return
        }
      }
    } catch {
      // local search fallback
    }
    const filtered = docs.filter((d) => d.name.toLowerCase().includes(query.toLowerCase()))
    setSearchResults(filtered)
  }

  const displayDocs = searchResults ?? docs

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <button onClick={() => navigate('/dashboard')} className="flex items-center gap-1 text-textMuted hover:text-textPrimary transition-colors text-sm">
        <ArrowLeft size={16} /> Back to Dashboard
      </button>

      <h1 className="font-display text-3xl text-brandGold">DOCUMENT VAULT</h1>

      {/* Upload Zone */}
      <div
        onDragOver={handleDrag}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        className={`border-2 border-dashed rounded-fz-lg p-8 text-center transition-colors ${dragOver ? 'border-brandGold bg-brandGold/5' : 'border-borderSubtle bg-bgElevated'}`}
      >
        <Upload size={32} className="mx-auto mb-3 text-brandGold" />
        <p className="text-textSecondary text-sm">Drag and drop documents here, or click to upload</p>
        <input type="file" className="hidden" id="file-upload" onChange={(e) => {
          if (e.target.files?.[0]) {
            handleFile(e.target.files[0])
          }
        }} />
        <label htmlFor="file-upload" className="inline-block mt-3 px-4 py-2 rounded-fz-md bg-brandGold text-textInverse text-sm font-medium hover:bg-brandGoldBright transition-colors cursor-pointer">
          Select File
        </label>
      </div>

      {/* Search */}
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-textMuted" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            placeholder="Search documents..."
            className="w-full pl-9 pr-3 py-2.5 rounded-fz-md bg-bgElevated border border-borderSubtle text-textPrimary placeholder:text-textMuted focus:border-brandGold focus:outline-none text-sm"
          />
        </div>
        <button onClick={handleSearch} className="px-4 py-2 rounded-fz-md bg-brandGold text-textInverse text-sm font-medium hover:bg-brandGoldBright transition-colors">
          Search
        </button>
      </div>

      {/* Doc List */}
      <div className="space-y-2">
        {displayDocs.map((doc) => {
          const StatusIcon = STATUS_ICON[doc.status] || File
          return (
            <motion.div
              key={doc.id}
              layout
              className="flex items-center gap-3 p-4 rounded-fz-md bg-bgElevated border border-borderSubtle hover:border-borderActive transition-colors cursor-pointer"
              onClick={() => setSelectedDoc(doc)}
            >
              <div className="w-10 h-10 rounded-fz-sm flex items-center justify-center shrink-0 bg-bgOverlay">
                {doc.type === 'image' ? <FileImage size={20} className="text-brandPurple" /> : <FileText size={20} className="text-brandBlue" />}
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-textPrimary truncate">{doc.name}</div>
                <div className="text-xs text-textMuted">{new Date(doc.uploaded_at).toLocaleDateString()}</div>
              </div>
              <div className="flex items-center gap-1.5 text-xs font-medium shrink-0" style={{ color: STATUS_COLOR[doc.status] }}>
                <StatusIcon size={12} className={doc.status === 'processing' ? 'animate-spin' : ''} />
                {doc.status.charAt(0).toUpperCase() + doc.status.slice(1)}
              </div>
              <ChevronRight size={16} className="text-textMuted shrink-0" />
            </motion.div>
          )
        })}
      </div>

      {/* Detail Drawer */}
      <AnimatePresence>
        {selectedDoc && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex justify-end bg-black/60"
            onClick={() => setSelectedDoc(null)}
          >
            <motion.div
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              transition={{ type: 'spring', damping: 25, stiffness: 200 }}
              className="w-full max-w-md bg-bgElevated border-l border-borderSubtle p-6 overflow-y-auto"
              onClick={(e: React.MouseEvent<HTMLDivElement>) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between mb-6">
                <h2 className="font-display text-xl text-brandGold">Document</h2>
                <button onClick={() => setSelectedDoc(null)} className="text-textMuted hover:text-textPrimary"><X size={20} /></button>
              </div>

              <div className="w-16 h-16 rounded-fz-lg flex items-center justify-center bg-bgOverlay mb-4">
                {selectedDoc.type === 'image' ? <FileImage size={32} className="text-brandPurple" /> : <FileText size={32} className="text-brandBlue" />}
              </div>

              <h3 className="font-semibold text-textPrimary mb-1">{selectedDoc.name}</h3>
              <div className="flex items-center gap-2 mb-4">
                <span className="text-xs px-2 py-0.5 rounded-fz-sm font-medium uppercase" style={{ backgroundColor: `${STATUS_COLOR[selectedDoc.status]}15`, color: STATUS_COLOR[selectedDoc.status] }}>
                  {selectedDoc.status}
                </span>
                <span className="text-xs text-textMuted">{new Date(selectedDoc.uploaded_at).toLocaleDateString()}</span>
              </div>

              {selectedDoc.rag_snippets && selectedDoc.rag_snippets.length > 0 && (
                <div className="mt-4">
                  <h4 className="text-sm font-semibold text-textPrimary mb-2">Key Snippets</h4>
                  <div className="space-y-2">
                    {selectedDoc.rag_snippets.map((snippet, i) => (
                      <div key={i} className="p-3 rounded-fz-md bg-bgOverlay border border-borderSubtle text-sm text-textSecondary">
                        {snippet}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
