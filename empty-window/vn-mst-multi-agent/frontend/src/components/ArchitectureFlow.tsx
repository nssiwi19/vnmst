export function ArchitectureFlow() {
  return (
    <div className="card animate-fade-in" style={{padding: '2.5rem', background: 'rgba(13, 17, 23, 0.4)'}}>
      <h3 style={{marginBottom: '2rem', textAlign: 'center', fontSize: '1.5rem', fontWeight: 800, background: 'linear-gradient(to right, #fff, #3b82f6)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent'}}>
        Hệ thống Multi-Agent Elite-DA
      </h3>
      <svg
        className="flow-svg"
        viewBox="0 0 1000 400"
        xmlns="http://www.w3.org/2000/svg"
        style={{width: '100%', height: 'auto'}}
      >
        <defs>
          <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="0" refY="3.5" orient="auto">
            <polygon points="0 0, 10 3.5, 0 7" fill="#475569" />
          </marker>
          <linearGradient id="blueGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" style={{stopColor: '#3b82f6', stopOpacity: 1}} />
            <stop offset="100%" style={{stopColor: '#1d4ed8', stopOpacity: 1}} />
          </linearGradient>
          <linearGradient id="purpleGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" style={{stopColor: '#8b5cf6', stopOpacity: 1}} />
            <stop offset="100%" style={{stopColor: '#6d28d9', stopOpacity: 1}} />
          </linearGradient>
        </defs>

        {/* User Input */}
        <rect x="20" y="160" width="140" height="80" rx="12" fill="rgba(255,255,255,0.05)" stroke="#3b82f6" strokeWidth="2" />
        <text x="90" y="195" textAnchor="middle" fontSize="14" fill="#fff" fontWeight="700">User Input</text>
        <text x="90" y="215" textAnchor="middle" fontSize="10" fill="#94a3b8">MST / Email / Yêu cầu</text>

        <path d="M 160 200 L 210 200" fill="none" stroke="#475569" strokeWidth="2" markerEnd="url(#arrowhead)" />

        {/* Backend API */}
        <rect x="220" y="140" width="160" height="120" rx="12" fill="url(#blueGrad)" />
        <text x="300" y="185" textAnchor="middle" fontSize="14" fill="#fff" fontWeight="700">FastAPI Backend</text>
        <text x="300" y="205" textAnchor="middle" fontSize="10" fill="rgba(255,255,255,0.8)">Orchestrator</text>
        <text x="300" y="225" textAnchor="middle" fontSize="10" fill="rgba(255,255,255,0.8)">JWT Auth & Routing</text>

        {/* Agent Pipeline */}
        <path d="M 380 200 L 430 200" fill="none" stroke="#475569" strokeWidth="2" markerEnd="url(#arrowhead)" />
        
        <rect x="440" y="40" width="200" height="320" rx="16" fill="rgba(139, 92, 246, 0.1)" stroke="#8b5cf6" strokeWidth="2" strokeDasharray="8 4" />
        <text x="540" y="70" textAnchor="middle" fontSize="12" fill="#8b5cf6" fontWeight="800">CREW AI PIPELINE</text>

        {/* Agents inside Crew */}
        <rect x="460" y="90" width="160" height="60" rx="8" fill="rgba(255,255,255,0.05)" stroke="rgba(139, 92, 246, 0.4)" />
        <text x="540" y="120" textAnchor="middle" fontSize="11" fill="#fff" fontWeight="600">Classifier Agent</text>
        <text x="540" y="135" textAnchor="middle" fontSize="8" fill="#94a3b8">Intent & Entity extraction</text>

        <rect x="460" y="170" width="160" height="60" rx="8" fill="rgba(255,255,255,0.05)" stroke="rgba(139, 92, 246, 0.4)" />
        <text x="540" y="200" textAnchor="middle" fontSize="11" fill="#fff" fontWeight="600">DataAnalyst Agent</text>
        <text x="540" y="215" textAnchor="middle" fontSize="8" fill="#94a3b8">Supabase Tool Calling</text>

        <rect x="460" y="250" width="160" height="60" rx="8" fill="rgba(255,255,255,0.05)" stroke="rgba(139, 92, 246, 0.4)" />
        <text x="540" y="280" textAnchor="middle" fontSize="11" fill="#fff" fontWeight="600">Writer Agent</text>
        <text x="540" y="295" textAnchor="middle" fontSize="8" fill="#94a3b8">Response Generation</text>

        {/* Database */}
        <path d="M 640 200 L 690 200" fill="none" stroke="#475569" strokeWidth="2" markerEnd="url(#arrowhead)" />
        
        <rect x="700" y="140" width="160" height="120" rx="12" fill="rgba(16, 185, 129, 0.1)" stroke="#10b981" strokeWidth="2" />
        <text x="780" y="185" textAnchor="middle" fontSize="14" fill="#fff" fontWeight="700">Supabase DB</text>
        <text x="780" y="205" textAnchor="middle" fontSize="10" fill="#94a3b8">PostgreSQL / RLS</text>
        <text x="780" y="225" textAnchor="middle" fontSize="10" fill="#94a3b8">Corporate Data (MST)</text>

        {/* External */}
        <path d="M 540 360 L 540 380 L 300 380 L 300 260" fill="none" stroke="#475569" strokeWidth="2" strokeDasharray="4 4" />
        <text x="420" y="395" textAnchor="middle" fontSize="9" fill="#64748b">Self-Correction & Memory Flow</text>
      </svg>
    </div>
  );
}
