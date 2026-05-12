import { useEffect, useState } from 'react';
import { api } from '../lib/api';
import { Search, Clock, ChevronRight, Building2, Trash2, Calendar } from 'lucide-react';

interface HistoryRecord {
  id: string;
  tax_code: string;
  company_name: string;
  created_at: string;
  research_data: any;
  report_content: string;
  crm_insights: any;
}

export function History({ onSelect }: { onSelect: (record: HistoryRecord) => void }) {
  const [records, setRecords] = useState<HistoryRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = async () => {
    try {
      const data = await api.get('/history');
      setRecords(data || []);
    } catch (err) {
      console.error("Failed to load history:", err);
    } finally {
      setLoading(false);
    }
  };

  const filteredRecords = records.filter(r => 
    r.company_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    r.tax_code.includes(searchTerm)
  );

  const formatDateTime = (dateStr: string) => {
    const d = new Date(dateStr);
    return d.toLocaleString('vi-VN', {
      hour: '2-digit',
      minute: '2-digit',
      day: '2-digit',
      month: '2-digit',
      year: 'numeric'
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-20">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <div className="history-view animate-fade-in" style={{padding: '1rem'}}>
      <div className="history-header glass" style={{padding: '1.5rem', borderRadius: '1.5rem', marginBottom: '1.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
        <div>
          <h2 style={{fontSize: '1.5rem', fontWeight: 800, background: 'linear-gradient(to right, #fff, #94a3b8)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent'}}>Lịch sử phân tích</h2>
          <p style={{color: '#94a3b8', fontSize: '0.875rem'}}>Quản lý các bản ghi nghiên cứu thị trường của bạn</p>
        </div>
        <div className="search-box" style={{position: 'relative', width: '300px'}}>
          <Search size={18} style={{position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: '#94a3b8'}} />
          <input 
            type="text" 
            placeholder="Tìm kiếm MST hoặc tên..." 
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{width: '100%', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', padding: '10px 10px 10px 40px', borderRadius: '12px', color: '#fff'}}
          />
        </div>
      </div>

      <div className="history-grid" style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(350px, 1fr))', gap: '1rem'}}>
        {filteredRecords.map((record) => (
          <div 
            key={record.id} 
            className="history-card glass" 
            onClick={() => onSelect(record)}
            style={{padding: '1.5rem', borderRadius: '1.25rem', cursor: 'pointer', transition: 'all 0.2s', position: 'relative', overflow: 'hidden'}}
          >
            <div className="card-decor" style={{position: 'absolute', top: 0, left: 0, width: '4px', height: '100%', background: 'var(--primary-blue)'}}></div>
            <div style={{display: 'flex', justifyContent: 'space-between', marginBottom: '1rem'}}>
              <div style={{background: 'rgba(59, 130, 246, 0.1)', color: '#3b82f6', padding: '4px 8px', borderRadius: '6px', fontSize: '0.7rem', fontWeight: 700}}>
                {record.tax_code}
              </div>
              <div style={{display: 'flex', alignItems: 'center', gap: '4px', color: '#94a3b8', fontSize: '0.75rem'}}>
                <Clock size={12} /> {formatDateTime(record.created_at)}
              </div>
            </div>
            
            <h3 style={{fontSize: '1rem', fontWeight: 700, marginBottom: '0.5rem', color: '#fff'}}>{record.company_name}</h3>
            
            <div style={{display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '1.5rem'}}>
              <div style={{fontSize: '0.8rem', color: '#94a3b8', display: 'flex', alignItems: 'center', gap: '6px'}}>
                <Calendar size={14} /> Xem chi tiết báo cáo
              </div>
              <div className="arrow-icon" style={{color: '#3b82f6'}}>
                <ChevronRight size={18} />
              </div>
            </div>
          </div>
        ))}
      </div>

      {filteredRecords.length === 0 && (
        <div style={{textAlign: 'center', padding: '4rem', color: '#94a3b8'}}>
          <div style={{marginBottom: '1rem', opacity: 0.2}}><Search size={48} style={{margin: '0 auto'}} /></div>
          <p>Không tìm thấy bản ghi nào trong lịch sử.</p>
        </div>
      )}
    </div>
  );
}
