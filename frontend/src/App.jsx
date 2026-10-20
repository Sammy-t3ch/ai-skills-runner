import { useEffect, useState } from 'react'
const API = import.meta.env.VITE_API_URL || ''

export default function App() {
  const [skills, setSkills] = useState([])
  const [skill, setSkill] = useState('research')
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [log, setLog] = useState([])

  useEffect(() => {
    fetch(`${API}/api/skills`).then(r => r.json()).then(d => {
      setSkills(d.skills || [])
      if (d.skills?.[0]) setSkill(d.skills[0].name)
    }).catch(() => setSkills([
      { name: 'research', title: 'Research Assistant', description: 'Summarize & compare', tools: ['web_search_mock','summarize'] },
      { name: 'ops', title: 'Ops Helper', description: 'Time & notes', tools: ['get_time','save_note','list_notes'] },
      { name: 'math', title: 'Math Skill', description: 'Safe arithmetic', tools: ['calculator'] },
      { name: 'nigeria', title: 'Nigeria Context', description: 'Cities & FX', tools: ['fx_rate','city_info'] },
    ]))
  }, [])

  async function run(msg) {
    const message = (msg || input).trim()
    if (!message || loading) return
    setInput('')
    setLog(l => [...l, { role: 'user', text: message }])
    setLoading(true)
    try {
      const res = await fetch(`${API}/api/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ skill, message }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Failed')
      setLog(l => [...l, { role: 'bot', text: data.reply, tools: data.tool_calls || [], skill: data.skill }])
    } catch (e) {
      setLog(l => [...l, { role: 'bot', text: `Backend offline or error: ${e.message}` }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app">
      <header className="header">
        <div>
          <div className="brand">
            <div className="logo">S</div>
            <div>
              <h1>AI Skills Runner</h1>
              <p className="tag">Composable skills · each skill exposes its own tools</p>
            </div>
          </div>
        </div>
        <span className="badge">Live demo</span>
      </header>

      <div className="skills">
        {skills.map(s => (
          <div key={s.name} className={`skill-card ${skill === s.name ? 'active' : ''}`} onClick={() => setSkill(s.name)}>
            <h3>{s.title}</h3>
            <p>{s.description}</p>
            <div className="tools">{(s.tools || []).join(' · ')}</div>
          </div>
        ))}
      </div>

      <div className="panel">
        {log.length === 0 && (
          <p className="msg" style={{ color: 'var(--muted)' }}>
            Select a skill, then ask something it can do — e.g. research a topic, calculate, check USD/NGN, or save a note.
          </p>
        )}
        {log.map((m, i) => (
          <div key={i} className={`msg ${m.role}`}>
            {m.text}
            {m.tools?.length > 0 && m.tools.map((t, j) => (
              <div key={j} className="tool">
                <span className="n">{t.tool}</span> {JSON.stringify(t.arguments)}
                <div>→ {t.result}</div>
              </div>
            ))}
          </div>
        ))}
      </div>

      <form className="composer" onSubmit={e => { e.preventDefault(); run() }}>
        <input value={input} onChange={e => setInput(e.target.value)} placeholder={`Ask the ${skill} skill…`} disabled={loading} />
        <button type="submit" disabled={loading || !input.trim()}>Run</button>
      </form>
      <p className="footer">Sammy-t3ch/ai-skills-runner · skills are packages of instructions + tools</p>
    </div>
  )
}
