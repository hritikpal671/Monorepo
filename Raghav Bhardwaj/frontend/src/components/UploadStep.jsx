import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { AgGridReact } from 'ag-grid-react'
import 'ag-grid-community/styles/ag-grid.css'
import 'ag-grid-community/styles/ag-theme-alpine.css'
import toast from 'react-hot-toast'
import clsx from 'clsx'
import {
  AlertCircle,
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  Database,
  FileUp,
  Info,
  Link2,
  Upload,
} from 'lucide-react'
import { datasetsAPI } from '../api'

const SOURCE_TYPES = [
  { id: 'file', label: 'File Upload', icon: FileUp, hint: 'CSV / XLSX' },
  { id: 'api', label: 'API Connection', icon: Link2, hint: 'REST endpoint' },
  { id: 'sql', label: 'SQL Connection', icon: Database, hint: 'PG / MySQL / MSSQL' },
]

const INIT_CONNECTION = {
  file: {},
  api: { url: '', authType: 'None', headers: '' },
  sql: { dbType: 'PostgreSQL', host: '', port: '', username: '', database: '' },
}

const CLASSIFICATION_OPTIONS = [
  { value: 'FACT', label: 'FACT', subtitle: 'Transaction-level' },
  { value: 'DIM', label: 'DIM', subtitle: 'Master / reference' },
]

function StatusChip({ ok, label }) {
  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-full border',
        ok
          ? 'border-emerald-700/50 bg-emerald-900/20 text-emerald-300'
          : 'border-surface-600/60 bg-surface-800/40 text-slate-500'
      )}
    >
      {ok && <CheckCircle2 className="w-3 h-3" />}
      {label}
    </span>
  )
}

function PreviewModal({
  dsLabel,
  dsType,
  preview,
  classification,
  selectedColumns,
  onSelectedColumnsChange,
  onClassificationChange,
  onClose,
}) {
  const gridRef = useRef(null)
  const rows = preview?.rows || []
  const columns = preview?.columns || []
  const visibleColumns = selectedColumns.length ? selectedColumns : columns

  const columnDefs = useMemo(
    () =>
      visibleColumns.map((field) => ({
        field,
        filter: true,
        sortable: true,
        resizable: true,
        minWidth: 130,
        valueFormatter: (p) => p.value ?? '-',
      })),
    [visibleColumns]
  )

  useEffect(() => {
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = ''
    }
  }, [])

  return (
    <div className="fixed inset-0 z-50 flex flex-col" style={{ background: 'var(--bg)' }}>
      <div
        className="h-14 flex-shrink-0 flex items-center justify-between px-5 border-b border-surface-700/60"
        style={{ background: 'var(--header-bg)' }}
      >
        <div className="flex items-center gap-3">
          <button type="button" onClick={onClose} className="btn-ghost px-2 py-1.5">
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div className="w-px h-5 bg-surface-600/60" />
          <div>
            <span className="text-[11px] font-bold uppercase tracking-widest text-slate-400">{dsType}</span>
            <p className="text-sm font-bold text-slate-100 leading-tight">{dsLabel} - Preview Data</p>
          </div>
        </div>

        <div className="hidden sm:flex items-center gap-2">
          <StatusChip ok={rows.length > 0} label="Preview loaded" />
          <StatusChip ok={columns.length > 0} label={`${columns.length} cols`} />
        </div>

        <div className="flex items-center gap-2 flex-wrap justify-end">
          <div className="flex items-center gap-2 rounded-xl border border-surface-700/70 bg-surface-900/30 p-1">
            {CLASSIFICATION_OPTIONS.map(({ value, label }) => {
              const active = classification === value
              return (
                <button
                  key={value}
                  type="button"
                  onClick={() => onClassificationChange(value)}
                  className={clsx(
                    'h-8 px-3 rounded-lg text-xs font-semibold transition-all',
                    active
                      ? 'bg-brand-500/15 text-brand-200 border border-brand-500/40'
                      : 'text-slate-400 hover:text-slate-200'
                  )}
                >
                  {label}
                </button>
              )
            })}
          </div>

          <button
            type="button"
            onClick={onClose}
            disabled={!classification}
            className={clsx(
              'btn-primary',
              !classification && 'opacity-50 cursor-not-allowed'
            )}
          >
            Save &amp; Close
          </button>
        </div>
      </div>

      <div className="flex-1 min-h-0 flex flex-col lg:flex-row">
        <div className="w-full lg:w-[320px] flex-shrink-0 border-b lg:border-b-0 lg:border-r border-surface-700/40" style={{ background: 'var(--bg-elev)' }}>
          <div className="px-4 py-3 border-b border-surface-700/40">
            <p className="text-xs font-bold uppercase tracking-widest text-slate-400">Column Selector</p>
            <p className="text-[11px] text-slate-500 mt-0.5">
              Select columns to show in the preview grid.
            </p>
          </div>
          <div className="p-3 space-y-3">
            <div className="flex items-center gap-2">
              <button
                type="button"
                className="text-[11px] font-semibold text-brand-300 hover:text-brand-200"
                onClick={() => onSelectedColumnsChange(columns)}
              >
                Select All
              </button>
              <span className="text-slate-600">·</span>
              <button
                type="button"
                className="text-[11px] font-semibold text-slate-500 hover:text-slate-300"
                onClick={() => onSelectedColumnsChange([])}
              >
                Clear
              </button>
            </div>
            <div className="max-h-[42vh] overflow-y-auto rounded-xl border border-surface-700/60 bg-surface-900/30">
              <div className="divide-y divide-surface-700/50">
                {columns.map((column) => {
                  const checked = selectedColumns.includes(column)
                  return (
                    <label
                      key={column}
                      className={clsx(
                        'flex items-center gap-3 px-3 py-2.5 text-sm cursor-pointer transition-colors',
                        checked ? 'bg-brand-500/10 text-slate-100' : 'text-slate-400 hover:bg-surface-800/50'
                      )}
                    >
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => {
                          onSelectedColumnsChange(
                            checked
                              ? selectedColumns.filter((value) => value !== column)
                              : [...selectedColumns, column]
                          )
                        }}
                        className="h-4 w-4 rounded border-surface-600 bg-surface-800 accent-brand-500 cursor-pointer flex-shrink-0"
                      />
                      <span className="truncate font-medium">{column}</span>
                    </label>
                  )
                })}
              </div>
            </div>
          </div>
        </div>

        <div className="flex-1 min-h-0 flex flex-col">
          <div
            className="flex-shrink-0 px-4 py-3 border-b border-surface-700/40 flex items-center justify-between gap-3"
            style={{ background: 'var(--bg-elev)' }}
          >
            <div>
              <p className="text-xs font-bold uppercase tracking-widest text-slate-400">Raw Data Preview</p>
              <p className="text-[11px] text-slate-500 mt-0.5">
                Top {rows.length} rows - {visibleColumns.length} selected of {columns.length} columns
              </p>
            </div>
          </div>

          <div className="flex-1 ag-theme-alpine-dark overflow-hidden">
            <AgGridReact
              ref={gridRef}
              rowData={rows}
              columnDefs={columnDefs}
              suppressCellFocus
              defaultColDef={{ resizable: true, minWidth: 120 }}
            />
          </div>
        </div>
      </div>
    </div>
  )
}

function DatasetCard({ label, type, projectId, existingDataset, onUploaded, onReadyChange }) {
  const [dataset, setDataset] = useState(existingDataset || null)
  const [preview, setPreview] = useState(null)
  const [sourceType, setSourceType] = useState('file')
  const [connection, setConnection] = useState(INIT_CONNECTION)
  const [uploading, setUploading] = useState(false)
  const [showPreview, setShowPreview] = useState(false)
  const [classification, setClassification] = useState('')
  const [selectedColumns, setSelectedColumns] = useState([])

  useEffect(() => {
    setDataset(existingDataset || null)
  }, [existingDataset])

  useEffect(() => {
    if (!dataset) {
      setPreview(null)
      setSelectedColumns([])
      return
    }

    let cancelled = false
    datasetsAPI
      .preview(projectId, dataset.id, 50)
      .then((pv) => {
        if (!cancelled) {
          setPreview(pv)
          setSelectedColumns(pv.columns || [])
        }
      })
      .catch(() => {})

    return () => {
      cancelled = true
    }
  }, [dataset, projectId])

  useEffect(() => {
    if (dataset) {
      onUploaded(dataset)
    }
  }, [dataset, onUploaded])

  const ready = Boolean(dataset && preview)

  useEffect(() => {
    onReadyChange(type, ready)
  }, [onReadyChange, ready, type])

  const columns = preview?.columns || dataset?.columns?.map((c) => c.column_name) || []

  const onDrop = useCallback(
    async (files) => {
      const file = files[0]
      if (!file) return

      setUploading(true)
      try {
        const ds = await datasetsAPI.upload(projectId, type, file)
        const pv = await datasetsAPI.preview(projectId, ds.id, 50)
        setDataset(ds)
        setPreview(pv)
        setSelectedColumns(pv.columns || [])
        toast.success(`${label} uploaded - ${ds.row_count} rows`)
      } catch (err) {
        toast.error(err.response?.data?.detail || 'Upload failed')
      } finally {
        setUploading(false)
      }
    },
    [label, projectId, type]
  )

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'text/csv': ['.csv'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
    },
    maxFiles: 1,
    disabled: uploading || sourceType !== 'file',
  })

  const chips = [
    { label: dataset ? `${dataset.row_count?.toLocaleString()} rows` : 'No file', ok: !!dataset },
    { label: preview ? `${columns.length} cols` : 'Preview pending', ok: !!preview },
    { label: classification || 'Classify', ok: !!classification },
    { label: ready ? 'Ready' : 'Pending', ok: ready },
  ]

  return (
    <>
      <div
        className={clsx('card flex flex-col overflow-hidden transition-all duration-200', ready ? 'border-emerald-700/40' : '')}
      >
        <div className="flex items-center justify-between px-4 py-3 border-b border-surface-700/50" style={{ background: 'var(--bg-elev)' }}>
          <div className="flex items-center gap-2.5">
            <span className="text-[10px] font-black px-2 py-0.5 rounded-md uppercase tracking-widest bg-surface-700/80 text-slate-300 border border-surface-600/80">
              {type}
            </span>
            <p className="text-sm font-bold text-slate-100">{label}</p>
          </div>
          {ready && (
            <span className="flex items-center gap-1 text-xs font-semibold text-emerald-300">
              <CheckCircle2 className="w-3.5 h-3.5" /> Ready
            </span>
          )}
        </div>

        <div className="flex gap-1 px-4 pt-3 pb-0">
          {SOURCE_TYPES.map(({ id, label: lbl, icon: Icon }) => (
            <button
              key={id}
              type="button"
              onClick={() => setSourceType(id)}
              className={clsx(
                'flex items-center gap-1.5 h-8 px-3 rounded-t-lg text-xs font-semibold border border-b-0 transition-all',
                sourceType === id
                  ? 'border-surface-600/80 bg-surface-800/80 text-slate-100'
                  : 'border-transparent text-slate-500 hover:text-slate-300'
              )}
            >
              <Icon className="w-3.5 h-3.5" />
              {lbl}
            </button>
          ))}
        </div>

        <div className="flex-1 p-4 space-y-3 border-t border-surface-700/40" style={{ background: 'var(--bg-elev)' }}>
          {sourceType === 'file' && (
            <div
              {...getRootProps()}
              className={clsx(
                'border-2 border-dashed rounded-xl p-5 text-center cursor-pointer transition-all duration-150 select-none',
                isDragActive
                  ? 'border-brand-500 bg-brand-500/10'
                  : dataset
                  ? 'border-emerald-700/50 bg-emerald-900/10'
                  : 'border-surface-600/70 hover:border-surface-500/80 bg-surface-900/40'
              )}
            >
              <input {...getInputProps()} />
              {uploading ? (
                <div className="flex flex-col items-center gap-2">
                  <div className="animate-spin rounded-full h-7 w-7 border-2 border-brand-500 border-t-transparent" />
                  <p className="text-xs text-slate-400">Uploading...</p>
                </div>
              ) : dataset ? (
                <div className="flex flex-col items-center gap-1">
                  <CheckCircle2 className="w-7 h-7 text-emerald-400" />
                  <p className="text-sm font-semibold text-emerald-300">{dataset.file_name}</p>
                  <p className="text-xs text-slate-500">Drop a new file to replace</p>
                </div>
              ) : (
                <div className="flex flex-col items-center gap-2">
                  <Upload className="w-7 h-7 text-slate-500" />
                  <p className="text-xs text-slate-400">{isDragActive ? 'Drop it...' : 'Drag and drop or click'}</p>
                  <p className="text-[11px] text-slate-600">CSV or XLSX</p>
                </div>
              )}
            </div>
          )}

          {sourceType === 'api' && (
            <div className="space-y-2.5">
              <input
                className="input text-xs"
                placeholder="API URL https://..."
                value={connection.api.url}
                onChange={(e) => setConnection({ ...connection, api: { ...connection.api, url: e.target.value } })}
              />
              <div className="grid grid-cols-2 gap-2">
                <select
                  className="input text-xs"
                  value={connection.api.authType}
                  onChange={(e) => setConnection({ ...connection, api: { ...connection.api, authType: e.target.value } })}
                >
                  <option>None</option>
                  <option>Bearer Token</option>
                  <option>Basic Auth</option>
                  <option>API Key</option>
                </select>
                <input
                  className="input text-xs"
                  placeholder='{"X-Key": "..."}'
                  value={connection.api.headers}
                  onChange={(e) => setConnection({ ...connection, api: { ...connection.api, headers: e.target.value } })}
                />
              </div>
              <div className="flex items-center gap-2 text-[11px] text-slate-500 bg-surface-900/40 rounded-lg px-3 py-2 border border-surface-700/40">
                <Info className="w-3.5 h-3.5 text-brand-400 flex-shrink-0" />
                Prototype mode - upload a CSV/XLSX sample below to populate the preview.
              </div>
              <div
                {...getRootProps()}
                className="border border-dashed border-surface-600/60 rounded-xl p-4 text-center cursor-pointer hover:border-surface-500/80 transition-all"
              >
                <input {...getInputProps()} />
                {dataset ? (
                  <p className="text-xs text-emerald-300 font-semibold">{dataset.file_name}</p>
                ) : (
                  <p className="text-xs text-slate-500">Upload sample data for preview</p>
                )}
              </div>
            </div>
          )}

          {sourceType === 'sql' && (
            <div className="space-y-2.5">
              <div className="grid grid-cols-3 gap-2">
                <select
                  className="input text-xs"
                  value={connection.sql.dbType}
                  onChange={(e) => setConnection({ ...connection, sql: { ...connection.sql, dbType: e.target.value } })}
                >
                  <option>PostgreSQL</option>
                  <option>MySQL</option>
                  <option>SQL Server</option>
                  <option>Oracle</option>
                </select>
                <input
                  className="input text-xs"
                  placeholder="Host"
                  value={connection.sql.host}
                  onChange={(e) => setConnection({ ...connection, sql: { ...connection.sql, host: e.target.value } })}
                />
                <input
                  className="input text-xs"
                  placeholder="Port"
                  value={connection.sql.port}
                  onChange={(e) => setConnection({ ...connection, sql: { ...connection.sql, port: e.target.value } })}
                />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <input
                  className="input text-xs"
                  placeholder="Username"
                  value={connection.sql.username}
                  onChange={(e) => setConnection({ ...connection, sql: { ...connection.sql, username: e.target.value } })}
                />
                <input
                  className="input text-xs"
                  placeholder="Database"
                  value={connection.sql.database}
                  onChange={(e) => setConnection({ ...connection, sql: { ...connection.sql, database: e.target.value } })}
                />
              </div>
              <div className="flex items-center gap-2 text-[11px] text-slate-500 bg-surface-900/40 rounded-lg px-3 py-2 border border-surface-700/40">
                <Info className="w-3.5 h-3.5 text-brand-400 flex-shrink-0" />
                Prototype mode - upload a CSV/XLSX sample below to populate the preview.
              </div>
              <div
                {...getRootProps()}
                className="border border-dashed border-surface-600/60 rounded-xl p-4 text-center cursor-pointer hover:border-surface-500/80 transition-all"
              >
                <input {...getInputProps()} />
                {dataset ? (
                  <p className="text-xs text-emerald-300 font-semibold">{dataset.file_name}</p>
                ) : (
                  <p className="text-xs text-slate-500">Upload sample data for preview</p>
                )}
              </div>
            </div>
          )}

          <div className="flex flex-wrap gap-1.5 pt-1">
            {chips.map(({ label: chipLabel, ok }) => (
              <StatusChip key={chipLabel} ok={ok} label={chipLabel} />
            ))}
          </div>
        </div>

        <div className="flex items-center justify-between px-4 py-3 border-t border-surface-700/40">
          <p className="text-[11px] text-slate-500">
            {ready
              ? `${columns.length} columns previewed`
              : dataset
              ? 'Preview the uploaded data before continuing'
              : 'Upload data first'}
          </p>
          <button
            type="button"
            disabled={!dataset}
            onClick={() => setShowPreview(true)}
            className={clsx(
              'inline-flex items-center gap-1.5 h-8 px-3 rounded-lg text-xs font-semibold border transition-all',
              dataset
                ? 'border-brand-500/50 bg-brand-500/10 text-brand-300 hover:bg-brand-500/20'
                : 'border-surface-700/40 text-slate-600 cursor-not-allowed opacity-50'
            )}
          >
            <Database className="w-3.5 h-3.5" />
            Preview Data
          </button>
        </div>
      </div>

      {showPreview && (
        <PreviewModal
          dsLabel={label}
          dsType={type}
          preview={preview}
          classification={classification}
          selectedColumns={selectedColumns}
          onSelectedColumnsChange={setSelectedColumns}
          onClassificationChange={setClassification}
          onClose={() => setShowPreview(false)}
        />
      )}
    </>
  )
}

export default function UploadStep({ project, datasets, onNext, onBack }) {
  const [sourceDs, setSourceDs] = useState(datasets?.find((d) => d.dataset_type === 'source') || null)
  const [targetDs, setTargetDs] = useState(datasets?.find((d) => d.dataset_type === 'target') || null)
  const [readyState, setReadyState] = useState({ source: false, target: false })

  useEffect(() => {
    setSourceDs(datasets?.find((d) => d.dataset_type === 'source') || null)
    setTargetDs(datasets?.find((d) => d.dataset_type === 'target') || null)
  }, [datasets])

  const handleReadyChange = useCallback((type, ready) => {
    setReadyState((s) => ({ ...s, [type]: ready }))
  }, [])

  const canProceed = sourceDs && targetDs && readyState.source && readyState.target

  return (
    <div className="flex flex-col h-full">
      <div className="flex-shrink-0 flex items-center justify-between gap-4 px-5 py-3.5 border-b border-surface-700/60">
        <div>
          <p className="text-[11px] uppercase tracking-widest text-slate-500 font-bold">Data Ingestion</p>
          <p className="text-sm font-bold text-slate-100 mt-0.5">Configure Source & Target Datasets</p>
        </div>
        {onBack && (
          <button type="button" className="btn-secondary" onClick={onBack}>
            <ArrowLeft className="w-4 h-4" /> Back
          </button>
        )}
      </div>

      <div className="flex-1 overflow-auto p-5">
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
          <DatasetCard
            label="Source Data"
            type="source"
            projectId={project.id}
            existingDataset={sourceDs}
            onUploaded={setSourceDs}
            onReadyChange={handleReadyChange}
          />
          <DatasetCard
            label="Target Data"
            type="target"
            projectId={project.id}
            existingDataset={targetDs}
            onUploaded={setTargetDs}
            onReadyChange={handleReadyChange}
          />
        </div>
      </div>

      <div className="flex-shrink-0 flex items-center justify-between gap-3 px-5 py-3.5 border-t border-surface-700/60">
        <div className="flex items-center gap-2">
          {!canProceed && (
            <span className="flex items-center gap-1.5 text-xs text-amber-400">
              <AlertCircle className="w-3.5 h-3.5" />
              Configure both Source and Target datasets to continue
            </span>
          )}
        </div>
        <button className="btn-primary" disabled={!canProceed} onClick={() => onNext({ source: sourceDs, target: targetDs })}>
          Save and Continue to Mapping
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  )
}
