'use client'

import { useState, useEffect, useRef } from 'react'
import './page.css'

// API base URLs
const CHAOS_API = typeof window !== 'undefined' ? 'http://localhost:8000' : 'http://chaos-app:8000'
const AGENT_API = typeof window !== 'undefined' ? 'http://localhost:8001' : 'http://codeweaver-agent:8001'

interface LogEntry {
    timestamp: string
    service: string
    message: string
    logLevel?: string
    duration?: string
}

interface Plan {
    id: string
    root_cause: string
    file_name: string
    line_number: number
    code_snippet: string
    action: string
    target: string
    reason: string
}

interface ServiceStatus {
    name: string
    status: 'active' | 'degraded' | 'down'
}

export default function Dashboard() {
    const [systemStatus, setSystemStatus] = useState<string>('OPTIMAL')
    const [uptime, setUptime] = useState<string>('99.99%')
    const [latency, setLatency] = useState<string>('42ms')
    const [logs, setLogs] = useState<LogEntry[]>([])
    const [plan, setPlan] = useState<Plan | null>(null)
    const [isProcessing, setIsProcessing] = useState(false)
    const terminalEndRef = useRef<HTMLDivElement>(null)

    const [services, setServices] = useState<ServiceStatus[]>([
        { name: 'AuthService', status: 'active' },
        { name: 'PaymentService', status: 'active' },
        { name: 'InventoryCore', status: 'active' },
        { name: 'NotificationEngine', status: 'active' }
    ])

    // Scroll terminal to bottom
    useEffect(() => {
        terminalEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [logs])

    // Fetch system health
    const fetchHealth = async () => {
        try {
            const res = await fetch(`${CHAOS_API}/health`, { signal: AbortSignal.timeout(1000) })
            if (res.ok) {
                // Check if we are really okay or if broken mode is on (simulate check via buy endpoint)
                try {
                    const check = await fetch(`${CHAOS_API}/buy`, { signal: AbortSignal.timeout(1000) })
                    if (!check.ok) {
                        setSystemStatus('CRITICAL')
                        setLatency('TIMEOUT')
                        setServices(prev => prev.map(s => s.name === 'PaymentService' ? { ...s, status: 'down' } : s))
                    } else {
                        setSystemStatus('OPTIMAL')
                        setLatency('42ms')
                        setServices(prev => prev.map(s => ({ ...s, status: 'active' })))
                    }
                } catch (e) {
                    setSystemStatus('CRITICAL')
                }
            }
        } catch (error) {
            setSystemStatus('OFFLINE')
        }
    }

    // Fetch pending plan
    const fetchPlan = async () => {
        try {
            const res = await fetch(`${AGENT_API}/plan/pending`, { signal: AbortSignal.timeout(2000) })
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

    const approvePlan = async () => {
        if (isProcessing) return
        setIsProcessing(true)
        try {
            const res = await fetch(`${AGENT_API}/plan/approve`, { method: 'POST', signal: AbortSignal.timeout(5000) })
            if (res.ok) {
                setPlan(null)
                alert('Plan Approved! Agent is executing fix...')
            }
        } catch (error) {
            alert('Failed to approve plan.')
        } finally {
            setIsProcessing(false)
        }
    }

    const rejectPlan = async () => {
        if (isProcessing) return
        setIsProcessing(true)
        try {
            const res = await fetch(`${AGENT_API}/plan/reject`, { method: 'POST', signal: AbortSignal.timeout(5000) })
            if (res.ok) {
                setPlan(null)
            }
        } catch (error) {
            alert('Failed to reject plan.')
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
        <div className="ide-container">
            {/* 1. Activity Bar */}
            <div className="activity-bar">
                <div className="activity-icon active" title="Explorer">
                    <svg viewBox="0 0 24 24"><path d="M20 6h-8l-2-2H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2zm0 12H4V8h16v10z" /></svg>
                </div>
                <div className="activity-icon" title="Search">
                    <svg viewBox="0 0 24 24"><path d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z" /></svg>
                </div>
                <div className="activity-icon" title="Source Control">
                    <svg viewBox="0 0 24 24"><path d="M18 13c-.47 0-.91.13-1.29.35l-2.61-4.8a3.985 3.985 0 00-1.1-6.55V1h-2v1.17A3.96 3.96 0 009.61 8.2l-2.61 4.8A4.01 4.01 0 003 15c0 2.21 1.79 4 4 4s4-1.79 4-4c0-.46-.07-.9-.19-1.32l2.64-4.86c.2.06.4.11.62.11.22 0 .42-.05.62-.11l2.64 4.86c-.12.42-.19.86-.19 1.32 0 2.21 1.79 4 4 4s4-1.79 4-4-1.79-4-4-4zM7 17c-1.1 0-2-.9-2-2s.9-2 2-2 2 .9 2 2-.9 2-2 2zm4-13c1.1 0 2 .9 2 2s-.9 2-2 2-2-.9-2-2 .9-2 2-2zm6 13c-1.1 0-2-.9-2-2s.9-2 2-2 2 .9 2 2-.9 2-2 2z" /></svg>
                </div>
                <div className="activity-icon" title="Debug">
                    <svg viewBox="0 0 24 24"><path d="M19 8l-4 4h3c0 3.31-2.69 6-6 6a5.87 5.87 0 01-2.8-.7l-1.46 1.46A7.93 7.93 0 0012 20c4.42 0 8-3.58 8-8h3l-4-4zM6 12c0-3.31 2.69-6 6-6 1.01 0 1.97.25 2.8.7l1.46-1.46A7.93 7.93 0 0012 4c-4.42 0-8 3.58-8 8H1l4 4 4-4H6z" /></svg>
                </div>
            </div>

            {/* 2. Explorer Sidebar */}
            <div className="explorer-sidebar">
                <div className="sidebar-header">EXPLORER</div>

                <div className="explorer-section">
                    <div className="explorer-title">
                        <span>▼ CODEWEAVER PROJECTS</span>
                    </div>
                    <div className="explorer-content">
                        <div className="explorer-item">
                            <span className={`status-dot ${systemStatus === 'OPTIMAL' ? 'green' : 'red'}`}></span>
                            chaos-app
                        </div>
                        <div className="explorer-item" style={{ marginLeft: '20px', color: '#858585' }}>
                            Health: {uptime}
                        </div>
                        <div className="explorer-item" style={{ marginLeft: '20px', color: '#858585' }}>
                            Latency: {latency}
                        </div>
                        <div className="explorer-item">
                            <span className="status-dot green"></span>
                            codeweaver-agent
                        </div>
                        <div className="explorer-item">
                            <span className="status-dot green"></span>
                            dashboard-next
                        </div>

                        {services.map(s => (
                            s.name !== 'AuthService' && // Just show extra services
                            <div key={s.name} className="explorer-item" style={{ marginLeft: '10px', opacity: 0.8 }}>
                                <span className={`status-dot ${s.status === 'active' ? 'green' : 'red'}`}></span>
                                {s.name}
                            </div>
                        ))}
                    </div>
                </div>

                <div className="explorer-section">
                    <div className="explorer-title">
                        <span>▼ OUTLINE</span>
                    </div>
                </div>
                <div className="explorer-section">
                    <div className="explorer-title">
                        <span>▼ TIMELINE</span>
                    </div>
                </div>
            </div>

            {/* 3. Main Editor Area */}
            <div className="editor-area">

                {/* Pane 1: Problem Log */}
                <div className="editor-group flex-grow">
                    <div className="tab-header">
                        <div className="tab active">
                            <img src="https://raw.githubusercontent.com/vscode-icons/vscode-icons/master/icons/file-type-log.svg" className="tab-icon" alt="" />
                            Problem.log
                            <span className="tab-close">×</span>
                        </div>
                    </div>
                    <div className="editor-content problem-log">
                        {plan ? (
                            <>
                                <div className="log-entry error">[ERROR] {new Date().toISOString().replace('T', ' ').split('.')[0]} ConnectionRefusedError: Unable to connect to database at 192.168.1.55 [{plan.file_name}:{plan.line_number}]</div>
                                <div className="log-entry" style={{ marginTop: '10px', opacity: 0.8 }}>Stack Trace:</div>
                                <div className="log-entry">{plan.code_snippet}</div>
                                <div className="log-entry" style={{ marginTop: '10px', color: '#cca700' }}>Analysis: {plan.root_cause}</div>
                            </>
                        ) : (
                            <div className="log-entry" style={{ color: '#6a9955' }}>// No active problems detected. System running optimally.</div>
                        )}
                    </div>
                </div>

                {/* Pane 2: Fix Plan */}
                <div className="editor-group flex-grow">
                    <div className="tab-header">
                        <div className="tab active">
                            <img src="https://raw.githubusercontent.com/vscode-icons/vscode-icons/master/icons/file-type-python.svg" className="tab-icon" alt="" />
                            Fix.py (Proposed Plan)
                            <span className="tab-close">×</span>
                        </div>
                    </div>
                    <div className="editor-content fix-plan">
                        {plan ? (
                            <>
                                <div><span className="python-keyword">def</span> <span className="python-function">remediate_issue</span>():</div>
                                <div style={{ paddingLeft: '20px' }}>
                                    <span className="python-string">"""</span><br />
                                    <span className="python-string">Plan ID: {plan.id}</span><br />
                                    <span className="python-string">Reason: {plan.reason}</span><br />
                                    <span className="python-string">"""</span>
                                </div>
                                <div style={{ paddingLeft: '20px', marginTop: '10px' }}>
                                    <span className="python-comment"># Execute method: {plan.action} on {plan.target}</span>
                                </div>
                                <div style={{ paddingLeft: '20px' }}>
                                    target = <span className="python-string">"{plan.target}"</span>
                                </div>
                                <div style={{ paddingLeft: '20px' }}>
                                    action = <span className="python-string">"{plan.action}"</span>
                                </div>
                                <div style={{ paddingLeft: '20px', marginTop: '10px' }}>
                                    <span className="python-keyword">return</span> system.execute(target, action)
                                </div>

                                <div className="action-bar">
                                    <button className="btn-vscode" onClick={approvePlan} disabled={isProcessing}>
                                        {isProcessing ? 'Executing...' : '✓ APPROVE FIX'}
                                    </button>
                                    <button className="btn-vscode secondary" onClick={rejectPlan} disabled={isProcessing}>
                                        ✕ REJECT
                                    </button>
                                </div>
                            </>
                        ) : (
                            <div style={{ color: '#6a9955' }}>
                                <span className="python-comment"># Waiting for agent to generate remediation plan...</span>
                            </div>
                        )}
                    </div>
                </div>

                {/* Pane 3: Terminal */}
                <div className="editor-group fixed-height">
                    <div className="tab-header">
                        <div className="tab active">
                            <img src="https://raw.githubusercontent.com/vscode-icons/vscode-icons/master/icons/file-type-shell.svg" className="tab-icon" alt="" />
                            Terminal (CodeWeaver Agent)
                            <span className="tab-close">×</span>
                        </div>
                        <div className="tab">
                            Debug Console
                        </div>
                    </div>
                    <div className="terminal-content">
                        {logs.map((log, idx) => (
                            <div key={idx} className="term-line">
                                <span className="term-time">[{log.timestamp}]</span>
                                <span className="term-tag info">[INFO]</span>
                                <span className="term-srv">{log.service || 'System'}</span>
                                <span className="term-msg">{log.message}</span>
                            </div>
                        ))}
                        <div ref={terminalEndRef} />
                    </div>
                </div>

            </div>
        </div>
    )
}
