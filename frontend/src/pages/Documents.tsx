import { useCallback, useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  ArrowLeft,
  Upload,
  Search,
  FileText,
  X,
  ChevronRight,
  AlertTriangle,
  CheckCircle,
  Loader2,
  FileImage,
  File,
  Lock,
  Tag,
  Calendar,
  Users,
  FileSearch,
  ShieldAlert,
  ExternalLink,
} from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import type { DocumentItem } from '@/types'
import { getDocuments, searchDocuments, uploadDocument } from '@/lib/api'
import { useAuth } from '@/context/AuthContext'

const STATUS_ICON: Record<string, typeof CheckCircle> = {
  verified: CheckCircle,
  completed: CheckCircle,
  processing: Loader2,
  pending: Loader2,
  uploaded: File,
  rejected: AlertTriangle,
  failed: AlertTriangle,
}

const STATUS_COLOR: Record<string, string> = {
  verified: '#10B981',
  completed: '#10B981',
  processing: '#00A8E8',
  pending: '#00A8E8',
  uploaded: '#A1A1AA',
  rejected: '#DC2626',
  failed: '#DC2626',
}

const DOCUMENT_TYPE_LABEL: Record<string, string> = {
  court_legal: 'Court / Legal',
  school_record: 'School Record',
  caseworker_report: 'Caseworker Report',
  parent_communication: 'Parent Communication',
  medical_mental_health: 'Medical / Mental Health',
  uploaded: 'Uploaded',
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' ? (value as Record<string, unknown>) : {}
}

function stringValue(value: unknown, fallback = ''): string {
  return typeof value === 'string' && value.length > 0 ? value : fallback
}

function numberValue(value: unknown): number | undefined {
  return typeof value === 'number' ? value : undefined
}

function documentTypeFromName(filename: string): DocumentItem['type'] {
  const ext = filename.split('.').pop()?.toLowerCase()
  if (ext === 'jpg' || ext === 'jpeg' || ext === 'png' || ext === 'webp' || ext === 'gif') return 'image'
  if (ext === 'txt') return 'txt'
  if (ext === 'doc' || ext === 'docx') return 'doc'
  return 'pdf'
}

function documentStatus(status: unknown): DocumentItem['status'] {
  if (status === 'verified' || status === 'processing' || status === 'uploaded' || status === 'rejected') return status
  if (status === 'completed') return 'verified'
  if (status === 'pending') return 'processing'
  if (status === 'failed') return 'rejected'
  return 'uploaded'
}

function snippetsFrom(value: unknown): string[] | undefined {
  if (!Array.isArray(value)) return undefined
  const snippets = value.filter((item): item is string => typeof item === 'string')
  return snippets.length > 0 ? snippets : undefined
}

function metadataFrom(value: unknown): Record<string, unknown> | undefined {
  const r = asRecord(value)
  return Object.keys(r).length > 0 ? r : undefined
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
    document_type: stringValue(record.document_type) || undefined,
    mime_type: stringValue(record.mime_type) || undefined,
    chunk_count: numberValue(record.chunk_count),
    extracted_metadata: metadataFrom(record.extracted_metadata),
  }
}

/* ─── Drawer subcomponents ─── */

function MetadataField({
  icon: Icon,
  label,
  children,
}: {
  icon: typeof Tag
  label: string
  children: React.ReactNode
}) {
  return (
    <div className="mb-4">
      <div className="flex items-center gap-2 text-xs uppercase tracking-wider text-textMuted mb-1.5">
        <Icon size={12} />
        {label}
      </div>
      <div className="text-sm text-textPrimary leading-relaxed">{children}</div>
    </div>
  )
}

function renderMetadataValue(value: unknown): React.ReactElement | string | null {
  if (value === null || value === undefined || value === '') return null
  if (typeof value === 'string' || typeof value === 'number') return String(value)
  if (Array.isArray(value)) {
    const items = value.filter((v) => v !== null && v !== undefined && v !== '')
    if (items.length === 0) return null
    return (
      <ul className="space-y-1">
        {items.map((v, i) => (
          <li key={i} className="flex gap-2">
            <span className="text-textMuted">·</span>
            <span>{typeof v === 'object' ? JSON.stringify(v) : String(v)}</span>
          </li>
        ))}
      </ul>
    )
  }
  if (typeof value === 'object') {
    return <pre className="text-xs text-textSecondary whitespace-pre-wrap">{JSON.stringify(value, null, 2)}</pre>
  }
  return String(value)
}

function ExtractedMetadataView({ metadata }: { metadata: Record<string, unknown> }) {
  // Pull the well-known fields out, render the rest as generic.
  const headline = metadata.headline
  const summary = metadata.summary
  const whatThisMeans = metadata.what_this_means
  const tags = metadata.tags
  const keyDates = metadata.key_dates
  const keyPeople = metadata.key_people
  const conditions = metadata.conditions || metadata.conditions_or_requirements
  const riskFactors = metadata.risk_factors
  const strengths = metadata.strengths
  const handled = new Set([
    'headline',
    'summary',
    'what_this_means',
    'tags',
    'key_dates',
    'key_people',
    'conditions',
    'conditions_or_requirements',
    'risk_factors',
    'strengths',
    'document_type',
  ])
  const remaining = Object.entries(metadata).filter(([k, v]) => !handled.has(k) && v !== null && v !== undefined && v !== '')

  const hasHeadline = typeof headline === 'string' && headline.length > 0
  const hasSummary = summary !== null && summary !== undefined && summary !== ''
  const hasWhatThisMeans =
    whatThisMeans !== null && whatThisMeans !== undefined && whatThisMeans !== ''
  const hasKeyDates = keyDates !== null && keyDates !== undefined && keyDates !== ''
  const hasKeyPeople = keyPeople !== null && keyPeople !== undefined && keyPeople !== ''
  const hasConditions = conditions !== null && conditions !== undefined && conditions !== ''
  const hasRiskFactors = riskFactors !== null && riskFactors !== undefined && riskFactors !== ''
  const hasStrengths = strengths !== null && strengths !== undefined && strengths !== ''

  return (
    <div>
      {hasHeadline && (
        <p className="text-base text-textPrimary font-medium leading-snug mb-4 pb-3 border-b border-borderSubtle">
          {String(headline)}
        </p>
      )}
      {hasSummary && (
        <MetadataField icon={FileSearch} label="Summary">
          {renderMetadataValue(summary)}
        </MetadataField>
      )}
      {hasWhatThisMeans && (
        <div className="mb-4 p-3 rounded-fz-md bg-brandGold/5 border border-brandGold/20">
          <div className="flex items-center gap-2 text-xs uppercase tracking-wider text-brandGold mb-1.5">
            <ShieldAlert size={12} /> What this means for you
          </div>
          <div className="text-sm text-textPrimary leading-relaxed">
            {renderMetadataValue(whatThisMeans)}
          </div>
        </div>
      )}
      {hasKeyDates && (
        <MetadataField icon={Calendar} label="Key Dates">
          {renderMetadataValue(keyDates)}
        </MetadataField>
      )}
      {hasKeyPeople && (
        <MetadataField icon={Users} label="Key People">
          {renderMetadataValue(keyPeople)}
        </MetadataField>
      )}
      {hasConditions && (
        <MetadataField icon={ShieldAlert} label="Conditions">
          {renderMetadataValue(conditions)}
        </MetadataField>
      )}
      {hasRiskFactors && (
        <MetadataField icon={AlertTriangle} label="Risk Factors">
          {renderMetadataValue(riskFactors)}
        </MetadataField>
      )}
      {hasStrengths && (
        <MetadataField icon={CheckCircle} label="Strengths">
          {renderMetadataValue(strengths)}
        </MetadataField>
      )}
      {Array.isArray(tags) && tags.length > 0 && (
        <MetadataField icon={Tag} label="Tags">
          <div className="flex flex-wrap gap-1.5">
            {tags
              .filter((t): t is string => typeof t === 'string')
              .map((t) => (
                <span key={t} className="px-2 py-0.5 rounded-fz-sm text-xs bg-bgOverlay border border-borderSubtle text-textSecondary">
                  {t}
                </span>
              ))}
          </div>
        </MetadataField>
      )}
      {remaining.length > 0 && (
        <div className="mt-4 pt-4 border-t border-borderSubtle">
          {remaining.map(([k, v]) => (
            <MetadataField key={k} icon={FileText} label={k.replace(/_/g, ' ')}>
              {renderMetadataValue(v)}
            </MetadataField>
          ))}
        </div>
      )}
    </div>
  )
}

/* ─── Page ─── */

export default function Documents() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const [docs, setDocs] = useState<DocumentItem[]>([])
  const [loading, setLoading] = useState(true)
  const [query, setQuery] = useState('')
  const [dragOver, setDragOver] = useState(false)
  const [selectedDoc, setSelectedDoc] = useState<DocumentItem | null>(null)
  const [searchResults, setSearchResults] = useState<DocumentItem[] | null>(null)
  const [uploadError, setUploadError] = useState<string>('')
  const [uploading, setUploading] = useState(false)

  // Session-only blob URLs for files uploaded in this browser session.
  // Keyed by doc id. These expire on reload — backend never stores raw bytes.
  const localPreviewsRef = useRef<Map<string, { url: string; mime: string; name: string }>>(new Map())
  const [previewVersion, setPreviewVersion] = useState(0)

  useEffect(() => {
    if (!user?.id) return
    setLoading(true)
    getDocuments(user.id)
      .then((data) => {
        const mapped = Array.isArray(data) ? data.map(documentFromApi) : []
        setDocs(mapped)
      })
      .catch(() => setDocs([]))
      .finally(() => setLoading(false))
  }, [user?.id])

  // Revoke blob URLs on unmount
  useEffect(() => {
    return () => {
      localPreviewsRef.current.forEach((v) => URL.revokeObjectURL(v.url))
      localPreviewsRef.current.clear()
    }
  }, [])

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(true)
  }, [])

  const handleFile = useCallback(
    async (file: globalThis.File) => {
      setUploadError('')
      if (!user?.id) {
        setUploadError('Sign in to upload documents.')
        return
      }
      setUploading(true)
      try {
        const uploaded = await uploadDocument(user.id, file)
        const item = documentFromApi(uploaded)
        // Stash a session-only preview blob URL for this doc id
        const url = URL.createObjectURL(file)
        localPreviewsRef.current.set(item.id, { url, mime: file.type, name: file.name })
        setPreviewVersion((v) => v + 1)
        setDocs((prev) => [item, ...prev])
      } catch (err) {
        setUploadError(err instanceof Error ? err.message : 'Upload failed')
      } finally {
        setUploading(false)
      }
    },
    [user?.id],
  )

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setDragOver(false)
      const file = e.dataTransfer.files[0]
      if (file) void handleFile(file)
    },
    [handleFile],
  )

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
          setSearchResults([
            {
              id: 'rag-search',
              user_id: user.id,
              name: `RAG results for "${query}"`,
              type: 'txt',
              status: 'verified',
              uploaded_at: new Date().toISOString(),
              rag_snippets: snippets,
            },
          ])
          return
        }
      }
    } catch {
      /* fall through */
    }
    const filtered = docs.filter((d) => d.name.toLowerCase().includes(query.toLowerCase()))
    setSearchResults(filtered)
  }

  const displayDocs = searchResults ?? docs

  // Reference previewVersion so React picks up Map mutations on render
  void previewVersion

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <button onClick={() => navigate('/dashboard')} className="flex items-center gap-1 text-textMuted hover:text-textPrimary transition-colors text-sm">
        <ArrowLeft size={16} /> Back to Dashboard
      </button>

      <div className="flex items-center justify-between">
        <h1 className="font-display text-3xl text-brandGold">DOCUMENT VAULT</h1>
        <div className="flex items-center gap-1.5 text-xs text-textMuted">
          <Lock size={12} />
          Privacy-first storage
        </div>
      </div>

      <p className="text-sm text-textSecondary -mt-2">
        Upload court papers, school records, or other paperwork. FlowZone reads them, extracts the
        important parts (dates, conditions, summaries), then{' '}
        <span className="text-textPrimary font-medium">discards the raw file</span> — your private
        text never sits on a server.
      </p>

      {/* Upload Zone */}
      <div
        onDragOver={handleDrag}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        className={`border-2 border-dashed rounded-fz-lg p-8 text-center transition-colors ${
          dragOver ? 'border-brandGold bg-brandGold/5' : 'border-borderSubtle bg-bgElevated'
        }`}
      >
        {uploading ? (
          <div className="flex flex-col items-center gap-2">
            <Loader2 size={28} className="animate-spin text-brandGold" />
            <p className="text-textSecondary text-sm">Uploading and extracting…</p>
          </div>
        ) : (
          <>
            <Upload size={32} className="mx-auto mb-3 text-brandGold" />
            <p className="text-textSecondary text-sm">Drag and drop documents here, or click to upload</p>
            <input
              type="file"
              className="hidden"
              id="file-upload"
              accept=".pdf,.doc,.docx,.txt,.png,.jpg,.jpeg,.webp"
              onChange={(e) => {
                if (e.target.files?.[0]) void handleFile(e.target.files[0])
                e.currentTarget.value = ''
              }}
            />
            <label
              htmlFor="file-upload"
              className="inline-block mt-3 px-4 py-2 rounded-fz-md bg-brandGold text-textInverse text-sm font-medium hover:bg-brandGoldBright transition-colors cursor-pointer"
            >
              Select File
            </label>
          </>
        )}
        {uploadError && (
          <div className="mt-3 inline-flex items-center gap-2 px-3 py-1.5 rounded-fz-sm bg-safeRed/10 border border-safeRed/30 text-xs text-safeRed">
            <AlertTriangle size={12} /> {uploadError}
          </div>
        )}
      </div>

      {/* Search */}
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-textMuted" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            placeholder="Search by name or content…"
            className="w-full pl-9 pr-3 py-2.5 rounded-fz-md bg-bgElevated border border-borderSubtle text-textPrimary placeholder:text-textMuted focus:border-brandGold focus:outline-none text-sm"
          />
        </div>
        <button
          onClick={handleSearch}
          className="px-4 py-2 rounded-fz-md bg-brandGold text-textInverse text-sm font-medium hover:bg-brandGoldBright transition-colors"
        >
          Search
        </button>
        {searchResults && (
          <button
            onClick={() => {
              setSearchResults(null)
              setQuery('')
            }}
            className="px-3 py-2 rounded-fz-md border border-borderSubtle text-textMuted text-sm"
          >
            Clear
          </button>
        )}
      </div>

      {/* Doc List */}
      <div className="space-y-2">
        {loading && (
          <div className="flex items-center justify-center py-12 text-textMuted">
            <Loader2 size={20} className="animate-spin mr-2" /> Loading documents…
          </div>
        )}
        {!loading && displayDocs.length === 0 && (
          <div className="text-center py-12 text-textMuted text-sm">
            No documents yet. Upload one to see what FlowZone extracts.
          </div>
        )}
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
                {doc.type === 'image' ? (
                  <FileImage size={20} className="text-brandPurple" />
                ) : (
                  <FileText size={20} className="text-brandBlue" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-textPrimary truncate">{doc.name}</div>
                <div className="text-xs text-textMuted">
                  {doc.document_type ? `${DOCUMENT_TYPE_LABEL[doc.document_type] || doc.document_type} · ` : ''}
                  {new Date(doc.uploaded_at).toLocaleDateString()}
                </div>
              </div>
              <div
                className="flex items-center gap-1.5 text-xs font-medium shrink-0"
                style={{ color: STATUS_COLOR[doc.status] }}
              >
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
              <div className="flex items-center justify-between mb-4">
                <h2 className="font-display text-xl text-brandGold">Document</h2>
                <button onClick={() => setSelectedDoc(null)} className="text-textMuted hover:text-textPrimary">
                  <X size={20} />
                </button>
              </div>

              <div className="flex items-center gap-3 mb-4">
                <div className="w-12 h-12 rounded-fz-md flex items-center justify-center bg-bgOverlay shrink-0">
                  {selectedDoc.type === 'image' ? (
                    <FileImage size={24} className="text-brandPurple" />
                  ) : (
                    <FileText size={24} className="text-brandBlue" />
                  )}
                </div>
                <div className="min-w-0">
                  <h3 className="font-semibold text-textPrimary truncate">{selectedDoc.name}</h3>
                  <div className="flex items-center gap-2 mt-0.5 flex-wrap">
                    <span
                      className="text-[10px] px-1.5 py-0.5 rounded-fz-sm font-medium uppercase"
                      style={{
                        backgroundColor: `${STATUS_COLOR[selectedDoc.status]}15`,
                        color: STATUS_COLOR[selectedDoc.status],
                      }}
                    >
                      {selectedDoc.status}
                    </span>
                    {selectedDoc.document_type && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded-fz-sm font-medium uppercase bg-bgOverlay border border-borderSubtle text-textSecondary">
                        {DOCUMENT_TYPE_LABEL[selectedDoc.document_type] || selectedDoc.document_type}
                      </span>
                    )}
                    <span className="text-xs text-textMuted">
                      {new Date(selectedDoc.uploaded_at).toLocaleDateString()}
                    </span>
                  </div>
                </div>
              </div>

              {/* Session-only local preview (only available if uploaded this browser session) */}
              {(() => {
                const preview = localPreviewsRef.current.get(selectedDoc.id)
                if (!preview) return null
                const isImage = preview.mime.startsWith('image/')
                const isPdf = preview.mime === 'application/pdf' || selectedDoc.type === 'pdf'
                return (
                  <div className="mb-5 rounded-fz-md overflow-hidden border border-borderSubtle bg-bgOverlay">
                    <div className="flex items-center justify-between px-3 py-2 bg-bgBase border-b border-borderSubtle">
                      <span className="text-xs text-textMuted">Local preview (this session only)</span>
                      <a
                        href={preview.url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-xs text-brandGold hover:text-brandGoldBright inline-flex items-center gap-1"
                      >
                        Open <ExternalLink size={11} />
                      </a>
                    </div>
                    {isImage ? (
                      <img src={preview.url} alt={preview.name} className="max-h-80 w-full object-contain bg-black" />
                    ) : isPdf ? (
                      <iframe
                        src={preview.url}
                        title={preview.name}
                        className="w-full h-80 bg-black"
                      />
                    ) : (
                      <div className="px-3 py-6 text-center text-xs text-textMuted">
                        Preview not available for this file type. Use Open above.
                      </div>
                    )}
                  </div>
                )
              })()}

              {/* Privacy note for docs without a local preview */}
              {!localPreviewsRef.current.get(selectedDoc.id) && (
                <div className="mb-5 p-3 rounded-fz-md bg-bgOverlay border border-borderSubtle">
                  <div className="flex items-start gap-2">
                    <Lock size={14} className="text-brandGold shrink-0 mt-0.5" />
                    <div className="text-xs text-textSecondary leading-relaxed">
                      The original file isn&apos;t kept on FlowZone&apos;s servers — only the structured
                      info below was extracted at upload time. Re-upload to view the file again in
                      this browser.
                    </div>
                  </div>
                </div>
              )}

              {/* What FlowZone knows */}
              <div className="mb-2">
                <h4 className="text-sm font-semibold text-textPrimary mb-3">What FlowZone has on this</h4>

                {selectedDoc.extracted_metadata && Object.keys(selectedDoc.extracted_metadata).length > 0 ? (
                  <ExtractedMetadataView metadata={selectedDoc.extracted_metadata} />
                ) : selectedDoc.status === 'processing' || selectedDoc.status === 'uploaded' ? (
                  <div className="flex items-center gap-2 text-sm text-textMuted py-2">
                    <Loader2 size={14} className="animate-spin" /> Still extracting…
                  </div>
                ) : (
                  <p className="text-sm text-textMuted py-2">
                    Nothing extracted yet. The processor may have failed — try re-uploading.
                  </p>
                )}

                {(selectedDoc.chunk_count !== undefined || selectedDoc.mime_type) && (
                  <div className="mt-4 pt-4 border-t border-borderSubtle text-xs text-textMuted space-y-1">
                    {selectedDoc.mime_type && <div>MIME: {selectedDoc.mime_type}</div>}
                    {selectedDoc.chunk_count !== undefined && <div>Indexed chunks: {selectedDoc.chunk_count}</div>}
                  </div>
                )}
              </div>

              {selectedDoc.rag_snippets && selectedDoc.rag_snippets.length > 0 && (
                <div className="mt-6">
                  <h4 className="text-sm font-semibold text-textPrimary mb-2">Matching Snippets</h4>
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
