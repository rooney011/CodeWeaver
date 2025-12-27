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
    involved_files?: string[]
    line_number: number
    code_snippet: string
    action: string
    target: string
    reason: string
    python_script?: string // The autonomous code
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
    const [activeTab, setActiveTab] = useState<string>('Problem.log')
    const terminalEndRef = useRef<HTMLDivElement>(null)

    const [services, setServices] = useState<ServiceStatus[]>([
        { name: 'AuthService', status: 'active' },
        { name: 'PaymentService', status: 'active' },
        { name: 'InventoryCore', status: 'active' },
        { name: 'NotificationEngine', status: 'active' }
    ])

    // Notification system
    const [notification, setNotification] = useState<{
        message: string;
        type: 'success' | 'error' | 'info';
    } | null>(null)

    const showNotification = (message: string, type: 'success' | 'error' | 'info' = 'info') => {
        setNotification({ message, type })
        setTimeout(() => setNotification(null), 4000)
    }

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
                        // Check headers/body for latency warning
                        const data = await check.json()
                        if (data.note === 'High Latency') {
                            setSystemStatus('DEGRADED')
                            setLatency(data.latency)
                            setServices(prev => prev.map(s => s.name === 'PaymentService' ? { ...s, status: 'degraded' } : s))
                        } else {
                            setSystemStatus('OPTIMAL')
                            setLatency('42ms')
                            setServices(prev => prev.map(s => ({ ...s, status: 'active' })))
                        }
                    }
                } catch (e) {
                    setSystemStatus('CRITICAL')
                    setServices(prev => prev.map(s => s.name === 'PaymentService' ? { ...s, status: 'down' } : s))
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
                // If new plan comes in, default to first involved file if available, else problem.log
                // Only switch if we aren't already looking at a file
                if (activeTab === 'Problem.log' && data.plan.involved_files && data.plan.involved_files.length > 0) {
                    // Optionally auto-switch, but user might want to see log first. Let's keep Problem.log as default.
                }
            } else {
                setPlan(null)
                if (activeTab !== 'Problem.log') setActiveTab('Problem.log')
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
                showNotification('Plan Approved! Agent is executing fix...', 'success')
                // Immediately refresh health to clear red status
                setTimeout(() => {
                    fetchHealth()
                    fetchLogs()
                }, 1000)
            }
        } catch (error) {
            showNotification('Failed to approve plan', 'error')
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
                showNotification('Plan rejected', 'info')
            }
        } catch (error) {
            showNotification('Failed to reject plan', 'error')
        } finally {
            setIsProcessing(false)
        }
    }

    // Chaos Control Functions
    const triggerChaos = async (type: string) => {
        try {
            let endpoint = '/chaos/trigger'
            if (type === 'memory') endpoint = '/chaos/trigger/memory'
            if (type === 'latency') endpoint = '/chaos/trigger/latency'
            if (type === 'cascade') endpoint = '/chaos/trigger/cascade'

            await fetch(`${CHAOS_API}${endpoint}`, { method: 'POST' })
            showNotification(`Chaos triggered: ${type}`, 'info')
        } catch (e) {
            showNotification('Failed to trigger chaos', 'error')
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
                    </div>
                </div>

                {/* CHAOS CONTROL SECTION */}
                <div className="explorer-section">
                    <div className="explorer-title">
                        <span>▼ CHAOS CONTROL</span>
                    </div>
                    <div className="explorer-content" style={{ padding: '10px' }}>
                        <button className="btn-vscode small" onClick={() => triggerChaos('db')} style={{ width: '100%', marginBottom: '5px' }}>
                            ⚡ Break DB
                        </button>
                        <button className="btn-vscode small" onClick={() => triggerChaos('memory')} style={{ width: '100%', marginBottom: '5px' }}>
                            📝 Memory Leak
                        </button>
                        <button className="btn-vscode small" onClick={() => triggerChaos('latency')} style={{ width: '100%', marginBottom: '5px' }}>
                            🐢 Latency Spike
                        </button>
                        <button className="btn-vscode small" onClick={() => triggerChaos('cascade')} style={{ width: '100%' }}>
                            🌊 Cascade Fail
                        </button>
                    </div>
                </div>
            </div>

            {/* 3. Main Editor Area */}
            <div className="editor-area">

                {/* Pane 1: Dynamic Tabs & File Content */}
                <div className="editor-group flex-grow">
                    <div className="tab-header">
                        {/* Always show Problem.log */}
                        <div
                            className={`tab ${activeTab === 'Problem.log' ? 'active' : ''}`}
                            onClick={() => setActiveTab('Problem.log')}
                        >
                            <img src="https://raw.githubusercontent.com/vscode-icons/vscode-icons/master/icons/file-type-log.svg" className="tab-icon" alt="" />
                            Problem.log
                        </div>

                        {/* Dynamic Tabs for Involved Files */}
                        {plan && plan.involved_files && plan.involved_files.map((file, idx) => (
                            <div
                                key={idx}
                                className={`tab ${activeTab === file ? 'active' : ''}`}
                                onClick={() => setActiveTab(file)}
                            >
                                <img src="https://raw.githubusercontent.com/vscode-icons/vscode-icons/master/icons/file-type-python.svg" className="tab-icon" alt="" />
                                {file}
                                <span className="tab-close">×</span>
                            </div>
                        ))}
                    </div>

                    <div className="editor-content problem-log">
                        {activeTab === 'Problem.log' ? (
                            // View 1: Problem Log Summary
                            plan ? (
                                <>
                                    <div className="log-entry error">[ERROR] {new Date().toISOString().replace('T', ' ').split('.')[0]} {plan.root_cause}</div>
                                    <div className="log-entry" style={{ marginTop: '10px', opacity: 0.8 }}>Impacted Files:</div>
                                    {plan.involved_files?.map(f => (
                                        <div key={f} className="log-entry" style={{ paddingLeft: '10px' }}>- {f}</div>
                                    ))}
                                    <div className="log-entry" style={{ marginTop: '10px', color: '#cca700' }}>Analysis: {plan.reason}</div>
                                </>
                            ) : (
                                <div className="log-entry" style={{ color: '#6a9955' }}>// No active problems detected. System running optimally.</div>
                            )
                        ) : (
                            // View 2: Code Viewer for specific file
                            <>
                                <div className="log-entry" style={{ color: '#858585' }}>// Viewing {activeTab} (Snapshot at failure)</div>
                                <div className="log-entry error">
                                    {plan?.code_snippet || "// Stack trace unavailable"}
                                </div>
                            </>
                        )}
                    </div>
                </div>

                {/* Pane 2: Fix Plan */}
                <div className="editor-group flex-grow">
                    <div className="tab-header">
                        <div className="tab active">
                            <img src="https://raw.githubusercontent.com/vscode-icons/vscode-icons/master/icons/file-type-python.svg" className="tab-icon" alt="" />
                            Fix.py (Generated)
                            <span className="tab-close">×</span>
                        </div>
                        <div className="tab success" style={{ background: '#1e3a1e' }}>
                            🛡️ AST Verified
                        </div>
                    </div>
                    <div className="editor-content fix-plan">
                        {plan ? (
                            <>
                                {plan.python_script ? (
                                    <>
                                        <div className="log-entry" style={{ color: '#6a9955', marginBottom: '10px' }}>
                                            # AUTONOMOUSLY GENERATED FIX<br />
                                            # Status: SAFE (Verified by Guardrails)
                                        </div>
                                        <pre style={{ margin: 0, fontFamily: 'monospace', color: '#d4d4d4' }}>
                                            {plan.python_script}
                                        </pre>
                                    </>
                                ) : (
                                    // Fallback for legacy plans
                                    <>
                                        <div><span className="python-keyword">def</span> <span className="python-function">remediate_issue</span>():</div>
                                        <div style={{ paddingLeft: '20px' }}>
                                            <span className="python-string">"""</span><br />
                                            <span className="python-string">Reason: {plan.reason}</span><br />
                                            <span className="python-string">"""</span>
                                        </div>
                                        <div style={{ paddingLeft: '20px', marginTop: '10px' }}>
                                            <span className="python-keyword">return</span> system.execute("{plan.target}", "{plan.action}")
                                        </div>
                                    </>
                                )}

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

            {/* Notification Toast */}
            {notification && (
                <div className={`notification-toast ${notification.type}`}>
                    <div className="notification-icon">
                        {notification.type === 'success' && '✓'}
                        {notification.type === 'error' && '✕'}
                        {notification.type === 'info' && 'ℹ'}
                    </div>
                    <div className="notification-message">{notification.message}</div>
                </div>
            )}
        </div>
    )
}
