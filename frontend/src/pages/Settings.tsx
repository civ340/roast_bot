import { useEffect, useRef, useState } from 'react'
import { fetchSettings, saveSettings } from '../api/client'
import type { AppSettings } from '../types'

const PROVIDERS = [
  { value: 'ollama',    label: 'Ollama（本地）' },
  { value: 'openai',   label: 'OpenAI' },
  { value: 'anthropic', label: 'Anthropic (Claude)' },
]

const PROVIDER_MODELS: Record<string, string[]> = {
  ollama: [
    'llama3.3', 'llama3.2', 'llama3.1', 'llama3',
    'qwen3', 'qwen2.5:7b', 'qwen2.5:14b', 'qwen2.5:32b', 'qwen2.5',
    'gemma3:4b', 'gemma3:12b', 'gemma3:27b', 'gemma3', 'gemma2',
    'deepseek-r1:7b', 'deepseek-r1:14b', 'deepseek-r1:32b', 'deepseek-r1',
    'mistral', 'mistral-nemo',
    'phi4', 'phi4-mini', 'phi3.5',
    'codellama',
  ],
  openai: [
    'gpt-4.1', 'gpt-4.1-mini', 'gpt-4.1-nano',
    'gpt-4o', 'gpt-4o-mini',
    'o4-mini', 'o3', 'o3-mini',
    'gpt-4-turbo',
  ],
  anthropic: [
    'claude-opus-4-7',
    'claude-sonnet-4-6',
    'claude-haiku-4-5-20251001',
    'claude-3-5-sonnet-20241022',
    'claude-3-5-haiku-20241022',
    'claude-3-opus-20240229',
  ],
}

function Toggle({ label, enabled, onChange }: { label: string; enabled: boolean; onChange: (v: boolean) => void }) {
  return (
    <label className="flex items-center justify-between py-3 border-b border-gray-800 cursor-pointer">
      <span className="text-sm text-gray-300">{label}</span>
      <button
        type="button"
        onClick={() => onChange(!enabled)}
        className={`relative w-11 h-6 rounded-full transition-colors ${enabled ? 'bg-green-600' : 'bg-gray-700'}`}
      >
        <span className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-transform ${enabled ? 'translate-x-6' : 'translate-x-1'}`} />
      </button>
    </label>
  )
}

export default function Settings() {
  const [form, setForm] = useState<AppSettings | null>(null)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [editingKey, setEditingKey] = useState(false)
  const keyInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => { fetchSettings().then(setForm) }, [])

  if (!form) return <div className="p-8 text-gray-500 animate-pulse">載入中...</div>

  const set = (k: keyof AppSettings, v: string) => setForm(f => f ? { ...f, [k]: v } : f)

  const startEditKey = () => {
    setEditingKey(true)
    set('llm_api_key', '')
    setTimeout(() => keyInputRef.current?.focus(), 0)
  }

  const handleSave = async () => {
    if (!form) return
    setSaving(true)
    try {
      const updated = await saveSettings(form)
      setForm(updated)
      setEditingKey(false)
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } finally {
      setSaving(false)
    }
  }

  const suggestedModels = PROVIDER_MODELS[form.llm_provider] ?? []

  return (
    <div className="p-8 max-w-xl">
      <h1 className="text-2xl font-bold mb-6">設定</h1>

      {/* LLM Provider */}
      <section className="mb-8">
        <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">語言模型</h2>
        <div className="space-y-4">
          <div>
            <label className="block text-sm text-gray-400 mb-1">Provider</label>
            <input
              value={form.llm_provider}
              onChange={e => set('llm_provider', e.target.value)}
              list="provider-suggestions"
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-green-500"
              placeholder="e.g. ollama、openai、anthropic"
            />
            <datalist id="provider-suggestions">
              {PROVIDERS.map(p => <option key={p.value} value={p.value}>{p.label}</option>)}
            </datalist>
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-1">模型名稱</label>
            <input
              value={form.llm_model}
              onChange={e => set('llm_model', e.target.value)}
              list="model-suggestions"
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-green-500"
              placeholder="e.g. llama3, gpt-4o"
            />
            <datalist id="model-suggestions">
              {suggestedModels.map(m => <option key={m} value={m} />)}
            </datalist>
          </div>

          {form.llm_provider !== 'ollama' && (
            <div>
              <label className="block text-sm text-gray-400 mb-1">API Key</label>
              {!editingKey && form.llm_api_key === '****' ? (
                <div className="flex items-center gap-2">
                  <div className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-400 tracking-widest">
                    ● ● ● ● ● ● ● ●
                  </div>
                  <button
                    type="button"
                    onClick={startEditKey}
                    className="px-3 py-2 text-sm rounded-lg bg-gray-700 hover:bg-gray-600 text-gray-300 whitespace-nowrap"
                  >
                    修改
                  </button>
                </div>
              ) : (
                <input
                  ref={keyInputRef}
                  type="password"
                  value={form.llm_api_key === '****' ? '' : form.llm_api_key}
                  onChange={e => set('llm_api_key', e.target.value)}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-green-500"
                  placeholder="輸入新的 API Key"
                />
              )}
            </div>
          )}

          {form.llm_provider === 'ollama' && (
            <div>
              <label className="block text-sm text-gray-400 mb-1">Ollama Base URL</label>
              <input
                value={form.llm_base_url}
                onChange={e => set('llm_base_url', e.target.value)}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-green-500"
                placeholder="http://host.docker.internal:11434"
              />
            </div>
          )}
        </div>
      </section>

      {/* Platforms */}
      <section className="mb-8">
        <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-2">啟用平台</h2>
        <Toggle
          label="Telegram 🤖"
          enabled={form.telegram_enabled === 'true'}
          onChange={v => set('telegram_enabled', String(v))}
        />
        <Toggle
          label="LINE 💬"
          enabled={form.line_enabled === 'true'}
          onChange={v => set('line_enabled', String(v))}
        />
        <Toggle
          label="Discord 🎮"
          enabled={form.discord_enabled === 'true'}
          onChange={v => set('discord_enabled', String(v))}
        />
      </section>

      <button
        onClick={handleSave}
        disabled={saving}
        className="px-5 py-2 bg-green-700 hover:bg-green-600 disabled:opacity-50 rounded-lg text-sm font-medium transition-colors"
      >
        {saving ? '儲存中...' : saved ? '✓ 已儲存' : '儲存設定'}
      </button>
    </div>
  )
}
