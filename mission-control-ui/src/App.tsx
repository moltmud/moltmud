import { useState, useEffect, useCallback } from 'react'

const API = '/api'

type Task = {
  id: number
  title: string
  description: string
  status: string
  priority: string
  assigned_to: string | null
  created_by: string
  created_at: string
  updated_at: string
  tags: string
}

type Activity = {
  id: number
  actor: string
  action: string
  detail: string
  task_id: number | null
  created_at: string
}

type Heartbeat = {
  agent: string
  status: string
  detail: string
  created_at: string
}

type Mention = {
  id: number
  from_actor: string
  to_actor: string
  message: string
  task_id: number | null
  created_at: string
}

const COLUMNS = ['inbox', 'assigned', 'in_progress', 'review', 'done'] as const
const COLUMN_LABELS: Record<string, string> = {
  inbox: 'Inbox',
  assigned: 'Assigned',
  in_progress: 'In Progress',
  review: 'Review',
  done: 'Done',
}

const PRIORITY_COLORS: Record<string, string> = {
  urgent: '#ef4444',
  high: '#f59e0b',
  normal: '#6b7280',
  low: '#94a3b8',
}

const AGENT_INFO: Record<string, { emoji: string; role: string }> = {
  'moltmud': { emoji: '🏰', role: 'Tavern keeper and world builder' },
  'greeter-bot': { emoji: '🌟', role: 'Welcomes newcomers to the tavern' },
}

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return mins + 'm ago'
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return hrs + 'h ago'
  return Math.floor(hrs / 24) + 'd ago'
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleString()
}

function AgentDetailModal({
  agent,
  heartbeat,
  activity,
  tasks,
  onClose,
}: {
  agent: string
  heartbeat: Heartbeat | null
  activity: Activity[]
  tasks: Task[]
  onClose: () => void
}) {
  const info = AGENT_INFO[agent] || { emoji: '🤖', role: 'Agent' }
  const agentActivity = activity.filter(a => a.actor === agent)
  const agentTasks = tasks.filter(t => t.assigned_to === agent || t.created_by === agent)
  const isAlive = heartbeat?.created_at && (Date.now() - new Date(heartbeat.created_at).getTime()) < 20 * 60 * 1000

  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
        background: 'rgba(0,0,0,0.7)', display: 'flex',
        alignItems: 'center', justifyContent: 'center', zIndex: 1000,
      }}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{
          background: '#1e1e2e', borderRadius: 12, padding: 24,
          width: '90%', maxWidth: 600, maxHeight: '80vh', overflow: 'auto',
          border: '1px solid #333',
        }}
      >
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20 }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <span style={{ fontSize: 32 }}>{info.emoji}</span>
              <div>
                <h2 style={{ margin: 0, fontSize: 20, color: '#e0e0e0' }}>@{agent}</h2>
                <div style={{ fontSize: 12, color: '#888' }}>{info.role}</div>
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'none', border: 'none', color: '#888',
              fontSize: 24, cursor: 'pointer', padding: 0,
            }}
          >
            ×
          </button>
        </div>

        {/* Status */}
        <div style={{
          background: '#12121a', borderRadius: 8, padding: 16, marginBottom: 16,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
            <div style={{
              width: 10, height: 10, borderRadius: '50%',
              background: isAlive ? '#22c55e' : '#ef4444',
            }} />
            <span style={{ fontWeight: 600, color: '#e0e0e0' }}>
              {isAlive ? 'Online' : 'Offline'}
            </span>
          </div>
          {heartbeat && heartbeat.status !== 'never' && (
            <>
              <div style={{ fontSize: 13, color: '#888', marginBottom: 4 }}>
                Status: <span style={{ color: '#e0e0e0' }}>{heartbeat.status}</span>
              </div>
              <div style={{ fontSize: 13, color: '#888', marginBottom: 4 }}>
                Detail: <span style={{ color: '#e0e0e0' }}>{heartbeat.detail || 'none'}</span>
              </div>
              <div style={{ fontSize: 12, color: '#666' }}>
                Last seen: {formatTime(heartbeat.created_at)}
              </div>
            </>
          )}
          {(!heartbeat || heartbeat.status === 'never') && (
            <div style={{ fontSize: 13, color: '#888' }}>No heartbeat recorded</div>
          )}
        </div>

        {/* Tasks */}
        <div style={{ marginBottom: 16 }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, color: '#999', marginBottom: 8, textTransform: 'uppercase' }}>
            Tasks ({agentTasks.length})
          </h3>
          {agentTasks.length === 0 ? (
            <div style={{ fontSize: 13, color: '#666' }}>No tasks associated</div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {agentTasks.slice(0, 5).map(t => (
                <div
                  key={t.id}
                  style={{
                    background: '#12121a', borderRadius: 6, padding: '10px 12px',
                    borderLeft: '3px solid ' + (PRIORITY_COLORS[t.priority] || '#333'),
                  }}
                >
                  <div style={{ fontSize: 13, color: '#e0e0e0', marginBottom: 4 }}>{t.title}</div>
                  <div style={{ display: 'flex', gap: 8, fontSize: 11 }}>
                    <span style={{ color: '#888' }}>{t.status}</span>
                    <span style={{ color: PRIORITY_COLORS[t.priority] }}>{t.priority}</span>
                    <span style={{ color: '#666' }}>{timeAgo(t.updated_at)}</span>
                  </div>
                </div>
              ))}
              {agentTasks.length > 5 && (
                <div style={{ fontSize: 12, color: '#666' }}>+{agentTasks.length - 5} more</div>
              )}
            </div>
          )}
        </div>

        {/* Recent Activity */}
        <div>
          <h3 style={{ fontSize: 14, fontWeight: 600, color: '#999', marginBottom: 8, textTransform: 'uppercase' }}>
            Recent Activity
          </h3>
          {agentActivity.length === 0 ? (
            <div style={{ fontSize: 13, color: '#666' }}>No recent activity</div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {agentActivity.slice(0, 10).map(a => (
                <div
                  key={a.id}
                  style={{
                    background: '#12121a', borderRadius: 6, padding: '8px 12px',
                  }}
                >
                  <div style={{ fontSize: 12, color: '#888' }}>
                    <span style={{ color: '#7c3aed' }}>{a.action}</span>
                    {' '}{a.detail}
                  </div>
                  <div style={{ fontSize: 10, color: '#555', marginTop: 2 }}>{timeAgo(a.created_at)}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function TaskCard({ task, onMove }: { task: Task; onMove: (id: number, status: string) => void }) {
  const colIdx = COLUMNS.indexOf(task.status as typeof COLUMNS[number])
  const nextStatus = colIdx < COLUMNS.length - 1 ? COLUMNS[colIdx + 1] : null
  const prevStatus = colIdx > 0 ? COLUMNS[colIdx - 1] : null

  return (
    <div style={{
      background: '#1e1e2e',
      border: '1px solid ' + (PRIORITY_COLORS[task.priority] || '#333') + '44',
      borderLeft: '3px solid ' + (PRIORITY_COLORS[task.priority] || '#333'),
      borderRadius: 8,
      padding: '12px 14px',
      marginBottom: 8,
    }}>
      <div style={{ fontSize: 13, fontWeight: 600, color: '#e0e0e0', marginBottom: 6 }}>
        {task.title}
      </div>
      {task.description && (
        <div style={{ fontSize: 11, color: '#888', marginBottom: 6 }}>{task.description}</div>
      )}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
          <span style={{
            fontSize: 10,
            padding: '2px 6px',
            borderRadius: 4,
            background: (PRIORITY_COLORS[task.priority] || '#333') + '22',
            color: PRIORITY_COLORS[task.priority],
            fontWeight: 600,
            textTransform: 'uppercase',
          }}>
            {task.priority}
          </span>
          {task.assigned_to && (
            <span style={{ fontSize: 10, color: '#7c8aaa' }}>
              @{task.assigned_to}
            </span>
          )}
        </div>
        <div style={{ display: 'flex', gap: 4 }}>
          {prevStatus && (
            <button onClick={() => onMove(task.id, prevStatus)} style={{
              background: 'none', border: '1px solid #444', borderRadius: 4,
              color: '#888', cursor: 'pointer', fontSize: 11, padding: '2px 6px',
            }}>&#8592;</button>
          )}
          {nextStatus && (
            <button onClick={() => onMove(task.id, nextStatus)} style={{
              background: 'none', border: '1px solid #444', borderRadius: 4,
              color: '#888', cursor: 'pointer', fontSize: 11, padding: '2px 6px',
            }}>&#8594;</button>
          )}
        </div>
      </div>
      <div style={{ fontSize: 10, color: '#555', marginTop: 6 }}>
        {timeAgo(task.updated_at)}
      </div>
    </div>
  )
}

function NewTaskForm({ onCreated }: { onCreated: () => void }) {
  const [open, setOpen] = useState(false)
  const [title, setTitle] = useState('')
  const [priority, setPriority] = useState('normal')
  const [assignee, setAssignee] = useState('')

  const submit = async () => {
    if (!title.trim()) return
    await fetch(API + '/tasks', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        title: title.trim(),
        created_by: 'amerzel',
        priority,
        assigned_to: assignee.trim() || null,
      }),
    })
    setTitle('')
    setAssignee('')
    setPriority('normal')
    setOpen(false)
    onCreated()
  }

  if (!open) {
    return (
      <button onClick={() => setOpen(true)} style={{
        background: '#7c3aed', color: '#fff', border: 'none', borderRadius: 6,
        padding: '8px 16px', cursor: 'pointer', fontSize: 13, fontWeight: 600,
      }}>+ New Task</button>
    )
  }

  return (
    <div style={{
      background: '#1e1e2e', border: '1px solid #333', borderRadius: 8,
      padding: 16, marginBottom: 16,
    }}>
      <input
        placeholder="Task title..."
        value={title}
        onChange={e => setTitle(e.target.value)}
        onKeyDown={e => e.key === 'Enter' && submit()}
        autoFocus
        style={{
          width: '100%', background: '#12121a', border: '1px solid #333', borderRadius: 6,
          padding: '8px 12px', color: '#e0e0e0', fontSize: 13, marginBottom: 8,
          boxSizing: 'border-box',
        }}
      />
      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
        <select value={priority} onChange={e => setPriority(e.target.value)} style={{
          background: '#12121a', border: '1px solid #333', borderRadius: 6,
          padding: '6px 10px', color: '#e0e0e0', fontSize: 12,
        }}>
          <option value="low">Low</option>
          <option value="normal">Normal</option>
          <option value="high">High</option>
          <option value="urgent">Urgent</option>
        </select>
        <input
          placeholder="Assign to..."
          value={assignee}
          onChange={e => setAssignee(e.target.value)}
          style={{
            background: '#12121a', border: '1px solid #333', borderRadius: 6,
            padding: '6px 10px', color: '#e0e0e0', fontSize: 12, flex: 1,
          }}
        />
        <button onClick={submit} style={{
          background: '#7c3aed', color: '#fff', border: 'none', borderRadius: 6,
          padding: '6px 14px', cursor: 'pointer', fontSize: 12, fontWeight: 600,
        }}>Create</button>
        <button onClick={() => setOpen(false)} style={{
          background: 'none', color: '#888', border: '1px solid #444', borderRadius: 6,
          padding: '6px 14px', cursor: 'pointer', fontSize: 12,
        }}>Cancel</button>
      </div>
    </div>
  )
}

function MentionForm({ onSent }: { onSent: () => void }) {
  const [open, setOpen] = useState(false)
  const [to, setTo] = useState('moltmud')
  const [msg, setMsg] = useState('')

  const send = async () => {
    if (!msg.trim()) return
    await fetch(API + '/mentions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ from_actor: 'amerzel', to_actor: to, message: msg.trim() }),
    })
    setMsg('')
    setOpen(false)
    onSent()
  }

  if (!open) {
    return (
      <button onClick={() => setOpen(true)} style={{
        background: 'none', color: '#7c3aed', border: '1px solid #7c3aed', borderRadius: 6,
        padding: '8px 16px', cursor: 'pointer', fontSize: 13, fontWeight: 600,
      }}>@mention</button>
    )
  }

  return (
    <div style={{
      background: '#1e1e2e', border: '1px solid #333', borderRadius: 8,
      padding: 16, marginBottom: 16,
    }}>
      <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
        <span style={{ color: '#7c3aed', fontSize: 13, lineHeight: '32px' }}>@</span>
        <input value={to} onChange={e => setTo(e.target.value)} style={{
          background: '#12121a', border: '1px solid #333', borderRadius: 6,
          padding: '6px 10px', color: '#e0e0e0', fontSize: 12, width: 120,
        }} />
      </div>
      <textarea
        placeholder="Message..."
        value={msg}
        onChange={e => setMsg(e.target.value)}
        rows={2}
        style={{
          width: '100%', background: '#12121a', border: '1px solid #333', borderRadius: 6,
          padding: '8px 12px', color: '#e0e0e0', fontSize: 13, marginBottom: 8,
          boxSizing: 'border-box', resize: 'vertical',
        }}
      />
      <div style={{ display: 'flex', gap: 8 }}>
        <button onClick={send} style={{
          background: '#7c3aed', color: '#fff', border: 'none', borderRadius: 6,
          padding: '6px 14px', cursor: 'pointer', fontSize: 12, fontWeight: 600,
        }}>Send</button>
        <button onClick={() => setOpen(false)} style={{
          background: 'none', color: '#888', border: '1px solid #444', borderRadius: 6,
          padding: '6px 14px', cursor: 'pointer', fontSize: 12,
        }}>Cancel</button>
      </div>
    </div>
  )
}

export default function App() {
  const [tasks, setTasks] = useState<Task[]>([])
  const [activity, setActivity] = useState<Activity[]>([])
  const [heartbeats, setHeartbeats] = useState<Record<string, Heartbeat>>({})
  const [mentions, setMentions] = useState<Mention[]>([])
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    const agents = ['moltmud', 'greeter-bot']
    const [t, a, m, ...hbs] = await Promise.all([
      fetch(API + '/tasks').then(r => r.json()),
      fetch(API + '/activity?limit=30').then(r => r.json()),
      fetch(API + '/mentions/moltmud').then(r => r.json()),
      ...agents.map(agent => fetch(API + '/heartbeat/' + agent).then(r => r.json()))
    ])
    setTasks(t)
    setActivity(a)
    setMentions(m)
    const hbMap: Record<string, Heartbeat> = {}
    agents.forEach((agent, i) => { hbMap[agent] = hbs[i] })
    setHeartbeats(hbMap)
  }, [])

  useEffect(() => {
    refresh()
    const iv = setInterval(refresh, 10000)
    return () => clearInterval(iv)
  }, [refresh])

  const moveTask = async (id: number, status: string) => {
    await fetch(API + '/tasks/status', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task_id: id, status, actor: 'amerzel' }),
    })
    refresh()
  }

  const tasksByCol = Object.fromEntries(COLUMNS.map(c => [c, tasks.filter(t => t.status === c)]))

  return (
    <div style={{ background: '#12121a', color: '#e0e0e0', minHeight: '100vh', fontFamily: "'Inter', system-ui, sans-serif" }}>
      {/* Agent Detail Modal */}
      {selectedAgent && (
        <AgentDetailModal
          agent={selectedAgent}
          heartbeat={heartbeats[selectedAgent] || null}
          activity={activity}
          tasks={tasks}
          onClose={() => setSelectedAgent(null)}
        />
      )}

      {/* Header */}
      <div style={{
        background: '#1a1a2e', borderBottom: '1px solid #252540',
        padding: '16px 24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 20, fontWeight: 700, color: '#e0e0e0' }}>
            Mission Control
          </h1>
          <span style={{ fontSize: 12, color: '#666' }}>MoltMud Operations Dashboard</span>
        </div>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          <MentionForm onSent={refresh} />
          <NewTaskForm onCreated={refresh} />
        </div>
      </div>

      <div style={{ display: 'flex', gap: 0, height: 'calc(100vh - 65px)' }}>
        {/* Main area - task board */}
        <div style={{ flex: 1, overflow: 'auto', padding: 20 }}>
          {/* Agent cards */}
          <div style={{ display: 'flex', gap: 12, marginBottom: 20 }}>
            {['moltmud', 'greeter-bot'].map(agent => {
              const hb = heartbeats[agent]
              const isAlive = hb?.created_at && (Date.now() - new Date(hb.created_at).getTime()) < 20 * 60 * 1000
              const info = AGENT_INFO[agent] || { emoji: '🤖', role: 'Agent' }
              return (
                <div
                  key={agent}
                  onClick={() => setSelectedAgent(agent)}
                  style={{
                    background: '#1e1e2e', border: '1px solid #252540', borderRadius: 8,
                    padding: '12px 16px', minWidth: 220, cursor: 'pointer',
                    transition: 'border-color 0.2s',
                  }}
                  onMouseOver={e => (e.currentTarget.style.borderColor = '#7c3aed')}
                  onMouseOut={e => (e.currentTarget.style.borderColor = '#252540')}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                    <span style={{ fontSize: 18 }}>{info.emoji}</span>
                    <div style={{
                      width: 8, height: 8, borderRadius: '50%',
                      background: isAlive ? '#22c55e' : '#ef4444',
                    }} />
                    <span style={{ fontWeight: 600, fontSize: 14 }}>@{agent}</span>
                  </div>
                  <div style={{ fontSize: 11, color: '#888' }}>
                    {hb?.status === 'never'
                      ? 'No heartbeat recorded'
                      : (hb?.status || 'unknown') + ' \u2014 ' + (hb?.detail || '').slice(0, 30)}
                  </div>
                  <div style={{ fontSize: 10, color: '#555', marginTop: 4 }}>
                    {hb?.created_at ? timeAgo(hb.created_at) : 'never'}
                  </div>
                </div>
              )
            })}

            {/* MUD server status */}
            <div style={{
              background: '#1e1e2e', border: '1px solid #252540', borderRadius: 8,
              padding: '12px 16px', minWidth: 180,
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                <span style={{ fontSize: 18 }}>🎮</span>
                <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#22c55e' }} />
                <span style={{ fontWeight: 600, fontSize: 14 }}>MUD Server</span>
              </div>
              <div style={{ fontSize: 11, color: '#888' }}>Port 4000 (TCP) + 8000 (HTTP)</div>
              <div style={{ fontSize: 10, color: '#555', marginTop: 4 }}>The Crossroads Tavern</div>
            </div>
          </div>

          {/* Unread mentions banner */}
          {mentions.length > 0 && (
            <div style={{
              background: '#7c3aed22', border: '1px solid #7c3aed44', borderRadius: 8,
              padding: '10px 14px', marginBottom: 16,
            }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#a78bfa', marginBottom: 4 }}>
                {mentions.length} unread mention{mentions.length > 1 ? 's' : ''} for @moltmud
              </div>
              {mentions.slice(0, 3).map(m => (
                <div key={m.id} style={{ fontSize: 11, color: '#888', marginTop: 4 }}>
                  <span style={{ color: '#7c3aed' }}>@{m.from_actor}</span>: {m.message}
                </div>
              ))}
            </div>
          )}

          {/* Task board columns */}
          <div style={{ display: 'flex', gap: 12, overflowX: 'auto' }}>
            {COLUMNS.map(col => (
              <div key={col} style={{ flex: 1, minWidth: 200 }}>
                <div style={{
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  marginBottom: 10, padding: '0 4px',
                }}>
                  <span style={{ fontSize: 12, fontWeight: 700, color: '#999', textTransform: 'uppercase', letterSpacing: 1 }}>
                    {COLUMN_LABELS[col]}
                  </span>
                  <span style={{
                    fontSize: 11, background: '#252540', color: '#888',
                    padding: '2px 8px', borderRadius: 10,
                  }}>
                    {tasksByCol[col]?.length || 0}
                  </span>
                </div>
                <div style={{ minHeight: 100 }}>
                  {tasksByCol[col]?.map(t => (
                    <TaskCard key={t.id} task={t} onMove={moveTask} />
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Sidebar - activity feed */}
        <div style={{
          width: 300, borderLeft: '1px solid #252540', background: '#1a1a2e',
          overflow: 'auto', padding: '16px 14px',
        }}>
          <h3 style={{ margin: '0 0 12px', fontSize: 13, fontWeight: 700, color: '#999', textTransform: 'uppercase', letterSpacing: 1 }}>
            Activity
          </h3>
          {activity.map(a => (
            <div key={a.id} style={{
              padding: '8px 0', borderBottom: '1px solid #252540',
            }}>
              <div style={{ fontSize: 12, color: '#e0e0e0' }}>
                <span style={{ color: '#7c3aed', fontWeight: 600 }}>@{a.actor}</span>{' '}
                <span style={{ color: '#888' }}>{a.action}</span>
              </div>
              <div style={{ fontSize: 11, color: '#666', marginTop: 2 }}>{a.detail}</div>
              <div style={{ fontSize: 10, color: '#444', marginTop: 2 }}>{timeAgo(a.created_at)}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
