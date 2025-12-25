
import { NextResponse } from 'next/server'
import fs from 'fs'
import path from 'path'

// Log file path inside the container
const LOG_FILE_PATH = '/logs/service.log'

export async function GET() {
    try {
        // specific check for development environment on windows
        const logPath = process.env.NODE_ENV === 'development' && process.platform === 'win32'
            ? 'd:\\codeweaver\\logs\\service.log' // fallback for local dev if needed, though we run in docker
            : LOG_FILE_PATH

        if (!fs.existsSync(logPath)) {
            return NextResponse.json({ logs: [] })
        }

        const fileContent = fs.readFileSync(logPath, 'utf-8')
        const lines = fileContent.split('\n').filter(line => line.trim() !== '')

        // Get last 50 lines
        const recentLines = lines.slice(-50)

        const parsedLogs = recentLines.map(line => {
            // Try to parse: 2025-12-25 11:52:08 - INFO - Message
            // Or agent: 2025-12-25 11:52:08 - [AGENT] INFO - Message

            try {
                const parts = line.split(' - ')
                if (parts.length >= 3) {
                    const timestamp = parts[0].split(' ')[1] // Get time part
                    let service = 'System'
                    let level = parts[1]
                    let message = parts.slice(2).join(' - ')

                    // improved parsing for agent logs which look like:
                    // ... - [AGENT] INFO - ...
                    if (level.includes('[')) {
                        const match = level.match(/\[(.*?)\]\s*(\w+)/)
                        if (match) {
                            service = match[1]
                            level = match[2]
                        }
                    } else {
                        // Infer service from message content or default
                        if (message.includes('Payment')) service = 'PaymentService'
                        else if (message.includes('Auth')) service = 'AuthService'
                        else if (message.includes('Chaos')) service = 'ChaosEngine'
                        else service = 'ChaosApp'
                    }

                    return {
                        timestamp,
                        service,
                        message,
                        logLevel: level
                    }
                }
            } catch (e) {
                // formatting failed, return raw
            }

            return {
                timestamp: new Date().toISOString().split('T')[1].split('.')[0],
                service: 'System',
                message: line
            }
        })

        return NextResponse.json({ logs: parsedLogs.reverse() }) // Newest first
    } catch (error) {
        console.error('Error reading logs:', error)
        return NextResponse.json({ logs: [] }, { status: 500 })
    }
}
