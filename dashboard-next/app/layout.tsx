import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
    title: 'CodeWeaver SRE Console',
    description: 'Professional SRE monitoring and incident response',
}

export default function RootLayout({
    children,
}: {
    children: React.ReactNode
}) {
    return (
        <html lang="en">
            <body>{children}</body>
        </html>
    )
}
