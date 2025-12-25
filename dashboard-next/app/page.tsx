'use client'

import { useState, useEffect } from 'react'
import './page.css'

// API base URLs - browser uses localhost (exposed ports), server uses docker service names
const CHAOS_API = typeof window !== 'undefined' ? 'http://localhost:8000' : 'http://chaos-app:8000'
const AGENT_API = typeof window !== 'undefined' ? 'http://localhost:8001' : 'http://codeweaver-agent:8001'

interface LogEntry {
    timestamp: string
    service: string
    message: string
    duration?: string
}

interface Plan {
    id: string
    root_cause: string
    file_name: string
    line_number: string
    code_snippet: string
    action: string
    reason: string
}

export default function SREConsole() {
    const [systemStatus, setSystemStatus] = useState<'OPTIMAL' | 'CRITICAL' | 'OFFLINE'>('OPTIMAL')
    const [uptime, setUptime] = useState('99.98%')
    const [latency, setLatency] = useState('42ms')
    const [logs, setLogs] = useState<LogEntry[]>([])
    const [plan, setPlan] = useState<Plan | null>(null)
    const [isProcessing, setIsProcessing] = useState(false)
    const [services, setServices] = useState([
        { name: 'Auth', status: 'OK' },
        { name: 'Payment', status: 'OK' },
        { name: 'Inventory', status: 'OK' },
        { name: 'Notification', status: 'OK' }
    ])

    // Fetch system health
    const fetchHealth = async () => {
        try {
            const res = await fetch(`${CHAOS_API}/buy`, {
                method: 'GET',
                signal: AbortSignal.timeout(1000)
            })
            if (res.status === 200) {
                setSystemStatus('OPTIMAL')
                setLatency('42ms')
            } else if (res.status === 500) {
                setSystemStatus('CRITICAL')
                setLatency('TIMEOUT')
            }
        } catch (error) {
            setSystemStatus('OFFLINE')
            setLatency('TIMEOUT')
        }
    }

    // Fetch pending plan
    const fetchPlan = async () => {
        try {
            const res = await fetch(`${AGENT_API}/plan/pending`, {
                signal: AbortSignal.timeout(2000)
            })
            const data = await res.json()
            if (data.status === 'pending' && data.plan) {
                setPlan(data.plan)
            } else {
                setPlan(null)
            }
        } catch (error) {
            // Keep existing plan or null
        }
    }

    // Fetch real logs
    const fetchLogs = async () => {
        try {
            const res = await fetch('/api/logs')
            const data = await res.json()
            if (data.logs && data.logs.length > 0) {
                setLogs(data.logs)
            }
        } catch (error) {
            console.error('Failed to fetch logs:', error)
        }
    }

    // Trigger chaos
    // const triggerIncident = async () => {
    //     try {
    //         await fetch('/api/chaos/chaos/trigger', { method: 'POST' })
    //     } catch (error) {
    //         console.error('Failed to trigger chaos:', error)
    //     }
    // }

    // Approve plan
    const approvePlan = async () => {
        if (isProcessing) return
        setIsProcessing(true)
        try {
            const res = await fetch(`${AGENT_API}/plan/approve`, {
                method: 'POST',
                signal: AbortSignal.timeout(5000)
            })
            if (res.ok) {
                setPlan(null)
            } else {
                console.error('Failed to approve plan: Server returned', res.status)
                alert('Failed to approve plan. Please try again.')
            }
        } catch (error) {
            console.error('Failed to approve plan:', error)
            alert('Failed to approve plan. Please check if the agent service is running.')
        } finally {
            setIsProcessing(false)
        }
    }

    // Reject plan
    const rejectPlan = async () => {
        if (isProcessing) return
        setIsProcessing(true)
        try {
            const res = await fetch(`${AGENT_API}/plan/reject`, {
                method: 'POST',
                signal: AbortSignal.timeout(5000)
            })
            if (res.ok) {
                setPlan(null)
            } else {
                console.error('Failed to reject plan: Server returned', res.status)
                alert('Failed to reject plan. Please try again.')
            }
        } catch (error) {
            console.error('Failed to reject plan:', error)
            alert('Failed to reject plan. Please check if the agent service is running.')
        } finally {
            setIsProcessing(false)
        }
    }

    // Auto-refresh
    useEffect(() => {
        fetchLogs()
        fetchHealth()
        fetchPlan()

        const interval = setInterval(() => {
            fetchLogs()
            fetchHealth()
            fetchPlan()
        }, 2000)

        return () => clearInterval(interval)
    }, [])

    return (
        <div className="console">
            {/* Header */}
            {/* Header */}
            <header className="header">
                <div className="logo">CodeWeaver SRE <span style={{ fontSize: '0.7em', color: '#666' }}>v2.0</span></div>
                <div className={`status-badge ${systemStatus === 'OPTIMAL' ? 'optimal' : systemStatus === 'OFFLINE' ? 'offline' : 'critical'}`}>
                    <span className="status-dot"></span>
                    SYSTEM {systemStatus}
                </div>
            </header>

            {/* Main Content */}
            <div className="main-content">
                {/* Left Sidebar */}
                <aside className="sidebar">
                    <div className="metric-card">
                        <div className="metric-label">UPTIME (7D)</div>
                        <div className="metric-value">{uptime}</div>
                        <div className="metric-bar">
                            <div className="metric-bar-fill" style={{ width: uptime }}></div>
                        </div>
                    </div>

                    <div className="metric-card">
                        <div className="metric-label">AVG LATENCY</div>
                        <div className="metric-value">{latency}</div>
                    </div>

                    <div className="services-card">
                        <div className="metric-label">ACTIVE SERVICES</div>
                        {services.map((service, idx) => (
                            <div key={idx} className="service-row">
                                <span className="service-name">{service.name}</span>
                                <span className="service-status ok">{service.status}</span>
                            </div>
                        ))}
                    </div>
                </aside>

                {/* Terminal */}
                <main className="terminal-section">
                    <div className="terminal-header">
                        <span>LIVE TERMINAL STREAM</span>
                        <div className="terminal-dots">
                            <span className="dot red"></span>
                            <span className="dot yellow"></span>
                            <span className="dot green"></span>
                        </div>
                    </div>
                    <div className="terminal-body">
                        {logs.map((log, idx) => (
                            <div key={idx} className="log-line">
                                <span className="log-time">{log.timestamp}</span>
                                <span className="log-tag">[INFO]</span>
                                <span className="log-service">{log.service}</span>
                                <span className="log-message">{log.message}</span>
                                <span className="log-duration">({log.duration})</span>
                            </div>
                        ))}
                    </div>
                </main>
            </div>

            {/* Incident Panel */}
            {
                (systemStatus === 'CRITICAL' || plan) && (
                    <div className="incident-panel">
                        <h2 className="incident-title">🎯 MISSION CONTROL</h2>

                        {plan ? (
                            <div className="incident-grid">
                                {/* Problem */}
                                <div className="incident-box problem">
                                    <div className="box-header">
                                        <span className="box-header-title">🔴 ERROR LOG</span>
                                        <div className="terminal-dots">
                                            <span className="dot red"></span>
                                            <span className="dot yellow"></span>
                                            <span className="dot green"></span>
                                        </div>
                                    </div>
                                    <div className="box-content">
                                        <div className="info-row">
                                            <span className="info-label">Root Cause:</span>
                                            <span className="info-value error-text">{plan.root_cause}</span>
                                        </div>
                                        <div className="info-row">
                                            <span className="info-label">Location:</span>
                                            <code className="code-inline">{plan.file_name}:{plan.line_number}</code>
                                        </div>
                                        <div className="info-row">
                                            <span className="info-label">Stack Trace:</span>
                                            <pre className="code-block error-block">{plan.code_snippet}</pre>
                                        </div>
                                        <div className="incident-id">Incident ID: {plan.id}</div>
                                    </div>
                                </div>

                                {/* Solution */}
                                <div className="incident-box solution">
                                    <div className="box-header">
                                        <span className="box-header-title">🟢 PROPOSED FIX</span>
                                        <div className="terminal-dots">
                                            <span className="dot red"></span>
                                            <span className="dot yellow"></span>
                                            <span className="dot green"></span>
                                        </div>
                                    </div>
                                    <div className="box-content">
                                        <div className="info-row">
                                            <span className="info-label">Action:</span>
                                            <div className="action-badge">{plan.action.replace('_', ' ').toUpperCase()}</div>
                                        </div>
                                        <div className="info-row">
                                            <span className="info-label">Reasoning:</span>
                                            <p className="reasoning-text">{plan.reason}</p>
                                        </div>
                                        <div className="button-group">
                                            <button
                                                className="btn btn-approve"
                                                onClick={approvePlan}
                                                disabled={isProcessing}
                                            >
                                                {isProcessing ? '⏳ PROCESSING...' : '✅ APPROVE FIX'}
                                            </button>
                                            <button
                                                className="btn btn-reject"
                                                onClick={rejectPlan}
                                                disabled={isProcessing}
                                            >
                                                {isProcessing ? '⏳ PROCESSING...' : '❌ REJECT'}
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        ) : (
                            <div className="waiting-box">
                                <div className="spinner"></div>
                                <p>Waiting for Agent Diagnosis...</p>
                                <small>The SRE Agent is analyzing logs. This may take 5-10 seconds.</small>
                            </div>
                        )}
                    </div>
                )
            }
        </div >
    )
}
