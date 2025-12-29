import React, { useEffect, useState } from 'react'
import { apiClient } from '../services/apiClient'

const STORAGE_KEY = 'saved_streams'

const loadSaved = () => {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    return JSON.parse(raw)
  } catch (e) {
    return []
  }
}

const saveSaved = (list) => {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(list))
}

const StreamsSettings = () => {
  const [streams, setStreams] = useState([])
  const [name, setName] = useState('')
  const [url, setUrl] = useState('')
  const [runningList, setRunningList] = useState([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setStreams(loadSaved())
    refreshRunning()
  }, [])

  const refreshRunning = async () => {
    try {
      const list = await apiClient.listStreams()
      setRunningList(Array.isArray(list) ? list.map(i => (typeof i === 'string' ? i : i.name || i.stream_name || '')) : [])
    } catch (e) {
      console.error('Failed to load running streams', e)
      setRunningList([])
    }
  }

  const handleAdd = () => {
    if (!name || !url) return
    const next = [...streams.filter(s => s.name !== name), { name, url }]
    setStreams(next)
    saveSaved(next)
    setName('')
    setUrl('')
  }

  const handleDelete = (n) => {
    const next = streams.filter(s => s.name !== n)
    setStreams(next)
    saveSaved(next)
  }

  const handleStart = async (s) => {
    setLoading(true)
    try {
      await apiClient.startStream({ name: s.name, url: s.url })
      await refreshRunning()
    } catch (e) {
      console.error('Start failed', e)
      alert('Failed to start stream: ' + (e.message || e))
    } finally { setLoading(false) }
  }

  const handleStop = async (s) => {
    setLoading(true)
    try {
      await apiClient.stopStream(s.name)
      await refreshRunning()
    } catch (e) {
      console.error('Stop failed', e)
      alert('Failed to stop stream: ' + (e.message || e))
    } finally { setLoading(false) }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-cyan-50 p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Page Header */}
        <div className="bg-surface-white rounded-2xl border border-slate-200/60 shadow-card overflow-hidden">
          <div className="h-1.5 w-full bg-gradient-to-r from-cyan-500 via-blue-400 to-teal-400" />
          <div className="p-6">
            <div className="flex items-center gap-4">
              <div className="p-3 rounded-xl bg-cyan-50 text-cyan-600 shadow-sm border border-cyan-100">
                <span className="material-icons-round text-2xl">videocam</span>
              </div>
              <div>
                <h1 className="text-2xl font-bold text-slate-800">Camera Streams Settings</h1>
                <p className="text-sm text-slate-500 mt-1">Configure and manage RTSP/stream URLs for live camera feeds</p>
              </div>
            </div>
          </div>
        </div>

        {/* Add Stream Card */}
        <div className="bg-surface-white rounded-2xl border border-slate-200/60 shadow-card overflow-hidden">
          <div className="h-1 w-full bg-gradient-to-r from-cyan-500 via-blue-400 to-teal-400" />
          <div className="p-6">
            <div className="flex items-center gap-3 mb-6">
              <span className="material-icons-round text-cyan-600">add_circle</span>
              <h3 className="text-lg font-bold text-slate-800">Add New Stream</h3>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-semibold text-slate-600 mb-2">Stream Name</label>
                <input 
                  type="text"
                  placeholder="e.g., Main Entrance, Lab Camera" 
                  value={name} 
                  onChange={(e) => setName(e.target.value)}
                  className="w-full px-4 py-3 rounded-xl border border-slate-200 focus:border-cyan-400 focus:ring-2 focus:ring-cyan-100 outline-none transition-all text-slate-800 placeholder-slate-400"
                />
              </div>
              <div>
                <label className="block text-sm font-semibold text-slate-600 mb-2">Stream URL</label>
                <input 
                  type="text"
                  placeholder="rtsp://... or ws://..." 
                  value={url} 
                  onChange={(e) => setUrl(e.target.value)}
                  className="w-full px-4 py-3 rounded-xl border border-slate-200 focus:border-cyan-400 focus:ring-2 focus:ring-cyan-100 outline-none transition-all text-slate-800 placeholder-slate-400"
                />
              </div>
            </div>

            <div className="flex items-center gap-3 mt-6">
              <button 
                onClick={handleAdd}
                disabled={!name || !url}
                className="bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-600 hover:to-blue-600 disabled:from-slate-300 disabled:to-slate-400 text-white font-bold py-3 px-8 rounded-xl transition-all shadow-md hover:shadow-lg transform hover:-translate-y-0.5 active:translate-y-0 flex items-center gap-2 disabled:cursor-not-allowed disabled:transform-none"
              >
                <span className="material-icons-round">save</span>
                Add Stream
              </button>
              <button 
                onClick={refreshRunning}
                className="bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold py-3 px-6 rounded-xl transition-all flex items-center gap-2 border border-slate-200"
              >
                <span className="material-icons-round">refresh</span>
                Refresh Status
              </button>
            </div>
          </div>
        </div>

        {/* Streams List Card */}
        <div className="bg-surface-white rounded-2xl border border-slate-200/60 shadow-card overflow-hidden">
          <div className="h-1 w-full bg-gradient-to-r from-cyan-500 via-blue-400 to-teal-400" />
          <div className="p-6">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <span className="material-icons-round text-cyan-600">format_list_bulleted</span>
                <h3 className="text-lg font-bold text-slate-800">Saved Streams</h3>
                <span className="text-sm text-slate-500 font-semibold px-3 py-1 bg-slate-100 rounded-full">{streams.length} Total</span>
              </div>
              <span className="text-sm text-slate-500 font-semibold px-3 py-1 bg-emerald-50 text-emerald-600 rounded-full flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-500" />
                {runningList.length} Running
              </span>
            </div>

            <div className="space-y-4">
              {streams.length === 0 ? (
                <div className="text-center py-12">
                  <div className="inline-flex p-4 rounded-2xl bg-slate-100 mb-4">
                    <span className="material-icons-round text-slate-400 text-5xl">video_library</span>
                  </div>
                  <p className="text-slate-500 font-medium">No saved streams yet</p>
                  <p className="text-sm text-slate-400 mt-1">Add your first camera stream above to get started</p>
                </div>
              ) : (
                streams.map(s => {
                  const isRunning = runningList.includes(s.name)
                  return (
                    <div key={s.name} className="bg-gradient-to-br from-slate-50 to-blue-50/30 rounded-xl p-5 border border-slate-200/60 hover:shadow-md transition-all">
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex items-start gap-4 flex-1 min-w-0">
                          <div className={`p-3 rounded-xl shadow-sm border ${isRunning ? 'bg-emerald-50 text-emerald-600 border-emerald-200' : 'bg-slate-100 text-slate-500 border-slate-200'}`}>
                            <span className="material-icons-round text-xl">{isRunning ? 'videocam' : 'videocam_off'}</span>
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              <h4 className="text-lg font-bold text-slate-800">{s.name}</h4>
                              {isRunning && (
                                <span className="text-xs text-emerald-600 font-semibold flex items-center gap-1 px-2 py-0.5 bg-emerald-100 rounded-md">
                                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                                  LIVE
                                </span>
                              )}
                            </div>
                            <p className="text-sm text-slate-500 font-mono truncate">{s.url}</p>
                          </div>
                        </div>
                        
                        <div className="flex items-center gap-2 flex-shrink-0">
                          {isRunning ? (
                            <button 
                              onClick={() => handleStop(s)} 
                              disabled={loading}
                              className="bg-rose-500 hover:bg-rose-600 disabled:bg-slate-300 text-white font-semibold py-2.5 px-5 rounded-lg transition-all shadow-sm hover:shadow flex items-center gap-2 disabled:cursor-not-allowed"
                            >
                              <span className="material-icons-round text-lg">stop_circle</span>
                              Stop
                            </button>
                          ) : (
                            <button 
                              onClick={() => handleStart(s)} 
                              disabled={loading}
                              className="bg-emerald-500 hover:bg-emerald-600 disabled:bg-slate-300 text-white font-semibold py-2.5 px-5 rounded-lg transition-all shadow-sm hover:shadow flex items-center gap-2 disabled:cursor-not-allowed"
                            >
                              <span className="material-icons-round text-lg">play_circle</span>
                              Start
                            </button>
                          )}
                          <button 
                            onClick={() => handleDelete(s.name)} 
                            disabled={loading}
                            className="bg-slate-100 hover:bg-rose-50 hover:text-rose-600 disabled:bg-slate-200 text-slate-600 font-semibold py-2.5 px-4 rounded-lg transition-all border border-slate-200 hover:border-rose-200 flex items-center gap-1.5 disabled:cursor-not-allowed"
                          >
                            <span className="material-icons-round text-lg">delete</span>
                            Delete
                          </button>
                        </div>
                      </div>
                    </div>
                  )
                })
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default StreamsSettings
