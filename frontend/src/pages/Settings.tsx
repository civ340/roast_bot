import { useEffect, useState } from 'react'
import { fetchSettings, saveSettings } from '../api/client'
import type { AppSettings } from '../types'

const PROVIDERS = [
  { value: 'ollama',    label: 'Ollama（本地）' },
  { value: 'openai',   label: 'OpenAI' },
  { value: 'anthropic', label: 'Anthropic (Claude)' },
]

const PROVIDER_MODELS: Record<string, string[]> = {
  ollama:    ['llama3', 'llama3.1', 'gemma3', 'mistral', 'qwen2.5'],
  openai:    ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo'],
  anthropic: ['claude-sonnet-4-6', 'claude-opus-4-7', 'claude-haiku-4-5-20251001'],
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

  useEffect(() => { fetchSettings().then(setForm) }, [])

  if (!form) return <div className="p-8 text-gray-500 animate-pulse">載入中...</div>

  const set = (k: keyof AppSettings, v: string) => setForm(f => f ? { ...f, [k]: v } : f)

  const handleSave = async () => {
    if (!form) return
    setSaving(true)
    try {
      const updated = await saveSettings(form)
      setForm(updated)
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
            <select
              value={form.llm_provider}
              onChange={e => set('llm_provider', e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-green-500"
            >
              {PROVIDERS.map(p => (
                <option key={p.value} value={p.value}>{p.label}</option>
              ))}
            </select>
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
              <input
                type="password"
                value={form.llm_api_key}
                onChange={e => set('llm_api_key', e.target.value)}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-green-500"
                placeholder={form.llm_api_key === '****' ? '已設定（輸入新值覆蓋）' : '輸入 API Key'}
              />
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
