import type { ReactNode } from 'react'

export function Panel({ title, area, children, className = '' }: { title: string; area: string; children: ReactNode; className?: string }) {
  return (
    <section className={`panel ${className}`} style={{ gridArea: area }} aria-label={title}>
      <h2 className="panel-title">{title}</h2>
      {children}
    </section>
  )
}
//theory enginge not done placeholder
export function Pending({ fn }: { fn: string }) {
  return <p className="pending">Needs <code>{fn}()</code> in the theory engine</p>
}
