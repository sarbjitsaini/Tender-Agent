import { AlertTriangle, ArrowUpRight, Building2, CalendarClock, Filter, Globe, RefreshCcw, Search, ShieldCheck } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';

const API_BASE = 'http://localhost:8000';

const watchlist = [
  'hot oil circulation', 'hot oiling', 'HOC', 'chemical injection', 'chemical dosing',
  'corrosion inhibitor', 'scale inhibitor', 'wax removal', 'paraffin', 'flow assurance',
  'dosing pump', 'Mehsana', 'Cambay', 'Ahmedabad', 'Gujarat',
];

const statusClasses = {
  'High Priority': 'bg-emerald-500/20 text-emerald-300',
  Review: 'bg-amber-500/20 text-amber-300',
  'Low Priority': 'bg-slate-700 text-slate-200',
};

export default function App() {
  const [tenders, setTenders] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [sectorFilter, setSectorFilter] = useState('All');
  const [loading, setLoading] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [error, setError] = useState('');

  const loadTenders = async () => {
    setLoading(true);
    setError('');

    try {
      const res = await fetch(`${API_BASE}/tenders`);
      if (!res.ok) {
        throw new Error(`Failed to load tenders (${res.status})`);
      }
      const data = await res.json();
      setTenders(data);
      if (!selectedId && data.length > 0) {
        setSelectedId(data[0].id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error while fetching tenders');
    } finally {
      setLoading(false);
    }
  };

  const runScan = async () => {
    setScanning(true);
    setError('');

    try {
      const res = await fetch(`${API_BASE}/scan`, { method: 'POST' });
      if (!res.ok) {
        throw new Error(`Scan failed (${res.status})`);
      }
      await loadTenders();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error while scanning tenders');
    } finally {
      setScanning(false);
    }
  };

  useEffect(() => {
    loadTenders();
  }, []);

  const filteredTenders = useMemo(
    () => (sectorFilter === 'All' ? tenders : tenders.filter((t) => t.sector === sectorFilter)),
    [sectorFilter, tenders],
  );

  const selected = filteredTenders.find((t) => t.id === selectedId) ?? filteredTenders[0];

  const summaryCards = [
    { label: 'Total tenders found', value: filteredTenders.length, icon: Search },
    { label: 'High-priority tenders', value: filteredTenders.filter((t) => t.status === 'High Priority').length, icon: ShieldCheck },
    { label: 'Closing soon', value: filteredTenders.filter((t) => daysToClose(t.closing_date) <= 10).length, icon: CalendarClock },
    { label: 'Sources monitored', value: new Set(filteredTenders.map((t) => t.source_portal)).size, icon: Globe },
  ];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-slate-800 bg-slate-900/90">
        <div className="mx-auto max-w-7xl px-4 py-5 sm:px-6 lg:px-8">
          <h1 className="text-2xl font-semibold tracking-tight">Oil & Gas Tender Intelligence Agent</h1>
          <p className="mt-1 text-sm text-slate-400">Monitoring opportunities for AONE Exploration Pvt Ltd</p>
        </div>
      </header>

      <main className="mx-auto grid max-w-7xl grid-cols-1 gap-6 px-4 py-6 sm:px-6 lg:grid-cols-12 lg:px-8">
        <section className="space-y-6 lg:col-span-8">
          <div className="flex flex-wrap gap-3">
            <button onClick={runScan} disabled={scanning} className="rounded-md bg-brand-500 px-4 py-2 text-sm font-medium text-white hover:bg-brand-300 hover:text-slate-900 disabled:opacity-60">
              {scanning ? 'Running Scan...' : 'Run Scan'}
            </button>
            <button onClick={loadTenders} disabled={loading} className="inline-flex items-center gap-2 rounded-md border border-slate-700 px-4 py-2 text-sm hover:bg-slate-800 disabled:opacity-60">
              <RefreshCcw className="h-4 w-4" /> Refresh
            </button>
          </div>

          {error ? (
            <div className="rounded-md border border-rose-800 bg-rose-950/40 p-3 text-sm text-rose-200">{error}</div>
          ) : null}

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {summaryCards.map(({ label, value, icon: Icon }) => (
              <div key={label} className="rounded-xl border border-slate-800 bg-slate-900 p-4">
                <div className="flex items-center justify-between">
                  <p className="text-sm text-slate-400">{label}</p>
                  <Icon className="h-4 w-4 text-brand-300" />
                </div>
                <p className="mt-4 text-2xl font-semibold">{loading ? '...' : value}</p>
              </div>
            ))}
          </div>

          <div className="rounded-xl border border-slate-800 bg-slate-900">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 p-4">
              <h2 className="text-lg font-medium">Tender Pipeline</h2>
              <div className="inline-flex items-center gap-2 rounded-md border border-slate-700 px-3 py-2 text-sm text-slate-200">
                <Filter className="h-4 w-4" />
                <select value={sectorFilter} onChange={(e) => setSectorFilter(e.target.value)} className="bg-transparent outline-none">
                  <option className="bg-slate-900">All</option>
                  <option className="bg-slate-900">Public</option>
                  <option className="bg-slate-900">Private</option>
                </select>
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-slate-800 text-sm">
                <thead className="bg-slate-900/70 text-slate-400">
                  <tr>
                    {['Company', 'Tender title', 'Sector', 'Location', 'Closing date', 'Source portal', 'Matched keywords', 'Relevance', 'Status'].map((head) => (
                      <th key={head} className="px-4 py-3 text-left font-medium">{head}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800">
                  {loading ? (
                    <tr><td colSpan={9} className="px-4 py-6 text-center text-slate-400">Loading tenders...</td></tr>
                  ) : filteredTenders.length === 0 ? (
                    <tr><td colSpan={9} className="px-4 py-6 text-center text-slate-400">No tenders found. Run Scan to ingest data.</td></tr>
                  ) : filteredTenders.map((tender) => (
                    <tr key={tender.id} onClick={() => setSelectedId(tender.id)} className={`cursor-pointer hover:bg-slate-800/40 ${selected?.id === tender.id ? 'bg-slate-800/50' : ''}`}>
                      <td className="px-4 py-3">{tender.company}</td>
                      <td className="max-w-xs px-4 py-3">{tender.title}</td>
                      <td className="px-4 py-3">{tender.sector}</td>
                      <td className="px-4 py-3">{tender.location}</td>
                      <td className="px-4 py-3">{formatDate(tender.closing_date)}</td>
                      <td className="px-4 py-3">{tender.source_portal}</td>
                      <td className="px-4 py-3">{tender.matched_keywords.join(', ')}</td>
                      <td className="px-4 py-3">{tender.relevance_score}%</td>
                      <td className="px-4 py-3"><StatusChip status={tender.status} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
            <h3 className="mb-3 text-base font-medium">Keyword Watchlist</h3>
            <div className="flex flex-wrap gap-2">
              {watchlist.map((word) => (
                <span key={word} className="rounded-full border border-brand-700/60 bg-brand-900/40 px-3 py-1 text-xs text-brand-300">{word}</span>
              ))}
            </div>
          </div>
        </section>

        <aside className="lg:col-span-4">
          <div className="sticky top-6 rounded-xl border border-slate-800 bg-slate-900 p-5">
            <h2 className="text-lg font-semibold">Tender Detail Panel</h2>
            {!selected ? (
              <p className="mt-4 text-sm text-slate-400">Select a tender to view details.</p>
            ) : (
              <>
                <p className="mt-1 text-sm text-slate-400">{selected.company}</p>
                <h3 className="mt-4 text-base font-medium">{selected.title}</h3>
                <div className="mt-5 space-y-4 text-sm">
                  <DetailRow title="AI summary" value={selected.ai_summary || 'No summary yet.'} />
                  <DetailRow title="Business fit" value="Evaluate operational readiness, location fit, and manpower availability." />
                  <DetailRow title="Bid/no-bid suggestion" value={selected.bid_recommendation} />
                  <DetailRow title="Closing date" value={formatDate(selected.closing_date)} />
                </div>
                <div className="mt-6 flex flex-col gap-2">
                  <button className="rounded-md bg-brand-500 px-3 py-2 text-sm font-medium text-white hover:bg-brand-300 hover:text-slate-900">Mark for Bid Review</button>
                  <button className="rounded-md border border-slate-700 px-3 py-2 text-sm hover:bg-slate-800">Ignore</button>
                  <a href={selected.source_url} target="_blank" rel="noreferrer" className="inline-flex items-center justify-center gap-2 rounded-md border border-slate-700 px-3 py-2 text-sm hover:bg-slate-800">
                    <Building2 className="h-4 w-4" /> Open Source <ArrowUpRight className="h-4 w-4" />
                  </a>
                </div>
                <div className="mt-5 inline-flex items-center gap-2 rounded-md bg-amber-500/10 px-3 py-2 text-xs text-amber-300">
                  <AlertTriangle className="h-4 w-4" /> Closing soon: prioritize internal review.
                </div>
              </>
            )}
          </div>
        </aside>
      </main>
    </div>
  );
}

function formatDate(isoDate) {
  if (!isoDate) return '-';
  return new Date(isoDate).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
}

function daysToClose(isoDate) {
  if (!isoDate) return Number.POSITIVE_INFINITY;
  const now = new Date();
  const closeDate = new Date(isoDate);
  return Math.ceil((closeDate.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
}

function StatusChip({ status }) {
  return <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${statusClasses[status] || statusClasses.Review}`}>{status}</span>;
}

function DetailRow({ title, value }) {
  return (
    <div>
      <p className="text-xs uppercase tracking-wide text-slate-500">{title}</p>
      <p className="mt-1 text-slate-200">{value}</p>
    </div>
  );
}
