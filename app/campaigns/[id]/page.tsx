'use client';

import { useState, useEffect, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { ArrowLeft, Send, CheckCircle, Clock, Search, MessageCircle, Globe, MapPin, Tag, Flame, Snowflake, Minus, ChevronDown, ChevronUp } from 'lucide-react';

interface Lead {
    id: number;
    name: string;
    phone: string;
    stage: string;
    metadata: any;
    computed_score?: number;
}

type ScoreFilter = 'all' | 'hot' | 'warm' | 'cold';

function ScoreBadge({ score }: { score: number }) {
    if (score >= 70) return (
        <span className="flex items-center gap-1 text-xs font-bold px-2 py-1 rounded-full bg-red-500/15 text-red-400 border border-red-500/20">
            <Flame className="w-3 h-3" /> {score}
        </span>
    );
    if (score >= 40) return (
        <span className="flex items-center gap-1 text-xs font-bold px-2 py-1 rounded-full bg-yellow-500/15 text-yellow-400 border border-yellow-500/20">
            <Minus className="w-3 h-3" /> {score}
        </span>
    );
    return (
        <span className="flex items-center gap-1 text-xs font-bold px-2 py-1 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20">
            <Snowflake className="w-3 h-3" /> {score}
        </span>
    );
}

export default function CampaignDetailsPage() {
    const params = useParams();
    const router = useRouter();
    const [leads, setLeads] = useState<Lead[]>([]);
    const [loading, setLoading] = useState(true);
    const [scoreFilter, setScoreFilter] = useState<ScoreFilter>('all');
    const [searchTerm, setSearchTerm] = useState('');

    // Scrape modal state
    const [showScrapeModal, setShowScrapeModal] = useState(false);
    const [scrapeQuery, setScrapeQuery] = useState('');
    const [scrapeMax, setScrapeMax] = useState(20);
    const [scraping, setScraping] = useState(false);
    const [scrapeResult, setScrapeResult] = useState<{ inserted: number; skipped: number; hot_leads: number; total: number } | null>(null);
    const [scrapeError, setScrapeError] = useState('');

    // Expand row state
    const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set());

    useEffect(() => {
        if (params.id) fetchLeads();
    }, [params.id]);

    const fetchLeads = async () => {
        try {
            const res = await fetch(`/api/campaigns/${params.id}/leads`);
            const data = await res.json();
            if (data.success) setLeads(data.data);
        } catch (error) {
            console.error('Failed to fetch leads', error);
        } finally {
            setLoading(false);
        }
    };

    const handleScrape = async () => {
        if (!scrapeQuery.trim()) return;
        setScraping(true);
        setScrapeResult(null);
        setScrapeError('');

        try {
            const res = await fetch(`/api/campaigns/${params.id}/scrape`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: scrapeQuery, maxResults: scrapeMax })
            });
            const data = await res.json();
            if (data.success) {
                setScrapeResult(data);
                fetchLeads();
            } else {
                setScrapeError(data.error || 'Error desconocido');
            }
        } catch (e) {
            setScrapeError('Error de conexión');
        } finally {
            setScraping(false);
        }
    };

    const handleSendWebhook = async () => {
        try {
            const res = await fetch(`/api/campaigns/${params.id}/webhook`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({})
            });
            const data = await res.json();
            if (data.success) {
                alert('✅ Webhook enviado a n8n. Lead ID: ' + data.lead_sent);
                fetchLeads();
            } else {
                alert('❌ Error: ' + data.error);
            }
        } catch (e) {
            alert('Error enviando webhook');
        }
    };

    const toggleRow = (id: number) => {
        setExpandedRows(prev => {
            const s = new Set(prev);
            s.has(id) ? s.delete(id) : s.add(id);
            return s;
        });
    };

    const getMeta = (lead: Lead) => {
        try {
            return typeof lead.metadata === 'string' ? JSON.parse(lead.metadata) : (lead.metadata || {});
        } catch { return {}; }
    };

    const filteredLeads = leads.filter(lead => {
        const score = lead.computed_score ?? getMeta(lead).opportunity_score ?? 0;
        const matchesScore =
            scoreFilter === 'all' ? true :
                scoreFilter === 'hot' ? score >= 70 :
                    scoreFilter === 'warm' ? (score >= 40 && score < 70) :
                        score < 40;
        const matchesSearch = !searchTerm || lead.name?.toLowerCase().includes(searchTerm.toLowerCase()) || lead.phone?.includes(searchTerm);
        return matchesScore && matchesSearch;
    });

    const hotCount = leads.filter(l => (l.computed_score ?? getMeta(l).opportunity_score ?? 0) >= 70).length;
    const warmCount = leads.filter(l => { const s = l.computed_score ?? getMeta(l).opportunity_score ?? 0; return s >= 40 && s < 70; }).length;
    const coldCount = leads.filter(l => (l.computed_score ?? getMeta(l).opportunity_score ?? 0) < 40).length;

    return (
        <div className="p-8 max-w-7xl mx-auto space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                    <button onClick={() => router.back()} className="p-2 bg-slate-800 rounded-lg hover:bg-slate-700 text-slate-300 transition-colors">
                        <ArrowLeft className="w-5 h-5" />
                    </button>
                    <div>
                        <h1 className="text-3xl font-bold text-white">Detalle de Campaña</h1>
                        <p className="text-slate-400">{leads.length} leads encontrados</p>
                    </div>
                </div>
                <button
                    onClick={() => { setShowScrapeModal(true); setScrapeResult(null); setScrapeError(''); }}
                    className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white px-5 py-2.5 rounded-xl font-semibold transition-colors shadow-lg shadow-blue-600/20"
                >
                    <Search className="w-5 h-5" />
                    🔍 Scrape en Vivo
                </button>
            </div>

            {/* Stats row */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <div className="bg-slate-800 p-5 rounded-xl border border-slate-700">
                    <div className="text-slate-400 text-sm mb-1">Total Leads</div>
                    <div className="text-3xl font-bold text-white">{leads.length}</div>
                </div>
                <div
                    className={`bg-slate-800 p-5 rounded-xl border cursor-pointer transition-all ${scoreFilter === 'hot' ? 'border-red-500/60 ring-1 ring-red-500/30' : 'border-slate-700 hover:border-red-500/40'}`}
                    onClick={() => setScoreFilter(prev => prev === 'hot' ? 'all' : 'hot')}
                >
                    <div className="text-red-400 text-sm mb-1 flex items-center gap-1"><Flame className="w-4 h-4" /> Calientes</div>
                    <div className="text-3xl font-bold text-white">{hotCount}</div>
                </div>
                <div
                    className={`bg-slate-800 p-5 rounded-xl border cursor-pointer transition-all ${scoreFilter === 'warm' ? 'border-yellow-500/60 ring-1 ring-yellow-500/30' : 'border-slate-700 hover:border-yellow-500/40'}`}
                    onClick={() => setScoreFilter(prev => prev === 'warm' ? 'all' : 'warm')}
                >
                    <div className="text-yellow-400 text-sm mb-1 flex items-center gap-1"><Minus className="w-4 h-4" /> Tibios</div>
                    <div className="text-3xl font-bold text-white">{warmCount}</div>
                </div>
                <div
                    className={`bg-slate-800 p-5 rounded-xl border cursor-pointer transition-all ${scoreFilter === 'cold' ? 'border-blue-500/60 ring-1 ring-blue-500/30' : 'border-slate-700 hover:border-blue-500/40'}`}
                    onClick={() => setScoreFilter(prev => prev === 'cold' ? 'all' : 'cold')}
                >
                    <div className="text-blue-400 text-sm mb-1 flex items-center gap-1"><Snowflake className="w-4 h-4" /> Fríos</div>
                    <div className="text-3xl font-bold text-white">{coldCount}</div>
                </div>
            </div>

            {/* Search + Webhook bar */}
            <div className="flex gap-3 items-center">
                <div className="flex-1 relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                    <input
                        type="text"
                        placeholder="Buscar por nombre o teléfono..."
                        value={searchTerm}
                        onChange={e => setSearchTerm(e.target.value)}
                        className="w-full pl-10 pr-4 py-2.5 bg-slate-800 border border-slate-700 rounded-xl text-white text-sm focus:outline-none focus:border-blue-500 placeholder-slate-500"
                    />
                </div>
                <button
                    onClick={handleSendWebhook}
                    className="flex items-center gap-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 px-4 py-2.5 rounded-xl text-sm font-medium transition-colors"
                >
                    <Send className="w-4 h-4" /> Test n8n
                </button>
            </div>

            {/* Leads Table */}
            <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
                <div className="p-4 border-b border-slate-700 flex justify-between items-center">
                    <h2 className="text-lg font-semibold text-white">
                        Pipeline de Leads
                        {scoreFilter !== 'all' && (
                            <span className="ml-2 text-sm font-normal text-slate-400">
                                — filtrando: {scoreFilter === 'hot' ? '🔥 Calientes' : scoreFilter === 'warm' ? '🟡 Tibios' : '❄️ Fríos'}
                                <button onClick={() => setScoreFilter('all')} className="ml-2 text-blue-400 hover:text-blue-300">
                                    (limpiar)
                                </button>
                            </span>
                        )}
                    </h2>
                    <span className="text-slate-500 text-sm">{filteredLeads.length} resultados</span>
                </div>

                <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm">
                        <thead className="bg-slate-900/50 text-xs uppercase text-slate-400">
                            <tr>
                                <th className="px-5 py-3 font-medium">Score</th>
                                <th className="px-5 py-3 font-medium">Nombre / Categoría</th>
                                <th className="px-5 py-3 font-medium">Teléfono</th>
                                <th className="px-5 py-3 font-medium">Web</th>
                                <th className="px-5 py-3 font-medium">Estado</th>
                                <th className="px-5 py-3 font-medium text-right">Acciones</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-700/50">
                            {loading ? (
                                <tr><td colSpan={6} className="px-5 py-8 text-center text-slate-500">Cargando leads...</td></tr>
                            ) : filteredLeads.length === 0 ? (
                                <tr><td colSpan={6} className="px-5 py-12 text-center text-slate-500">
                                    {leads.length === 0 ? 'No hay leads. Usá el botón "🔍 Scrape en Vivo" para empezar.' : 'Sin resultados para este filtro.'}
                                </td></tr>
                            ) : filteredLeads.map(lead => {
                                const meta = getMeta(lead);
                                const score = lead.computed_score ?? meta.opportunity_score ?? 0;
                                const isExpanded = expandedRows.has(lead.id);

                                return (
                                    <>
                                        <tr
                                            key={lead.id}
                                            className="hover:bg-slate-700/30 transition-colors cursor-pointer"
                                            onClick={() => toggleRow(lead.id)}
                                        >
                                            <td className="px-5 py-4">
                                                <ScoreBadge score={score} />
                                            </td>
                                            <td className="px-5 py-4">
                                                <div className="font-medium text-white">{lead.name}</div>
                                                {meta.category && (
                                                    <div className="flex items-center gap-1 text-xs text-slate-500 mt-0.5">
                                                        <Tag className="w-3 h-3" /> {meta.category}
                                                    </div>
                                                )}
                                            </td>
                                            <td className="px-5 py-4 font-mono text-slate-300 text-xs">{lead.phone || '—'}</td>
                                            <td className="px-5 py-4">
                                                {meta.website ? (
                                                    <a
                                                        href={meta.website} target="_blank" rel="noopener noreferrer"
                                                        className="flex items-center gap-1 text-blue-400 hover:underline text-xs truncate max-w-[160px]"
                                                        onClick={e => e.stopPropagation()}
                                                    >
                                                        <Globe className="w-3 h-3 flex-shrink-0" />
                                                        {meta.website.replace(/^https?:\/\/(www\.)?/, '').substring(0, 25)}
                                                    </a>
                                                ) : (
                                                    <span className="text-xs px-2 py-1 bg-red-500/10 text-red-400 border border-red-500/20 rounded-full font-medium">Sin Web</span>
                                                )}
                                            </td>
                                            <td className="px-5 py-4">
                                                <span className={`text-xs px-2 py-1 rounded-full font-medium ${lead.stage === 'new' ? 'bg-slate-700 text-slate-300' :
                                                        lead.stage === 'contacted' ? 'bg-blue-500/10 text-blue-400 border border-blue-500/20' :
                                                            lead.stage === 'responded' ? 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/20' :
                                                                'bg-green-500/10 text-green-400 border border-green-500/20'
                                                    }`}>
                                                    {lead.stage === 'new' ? 'Nuevo' : lead.stage === 'contacted' ? 'Contactado' : lead.stage === 'responded' ? 'Respondió' : lead.stage}
                                                </span>
                                            </td>
                                            <td className="px-5 py-4">
                                                <div className="flex items-center justify-end gap-2" onClick={e => e.stopPropagation()}>
                                                    {meta.whatsapp_link && (
                                                        <a
                                                            href={meta.whatsapp_link}
                                                            target="_blank"
                                                            rel="noopener noreferrer"
                                                            className="flex items-center gap-1.5 bg-green-600 hover:bg-green-500 text-white px-3 py-1.5 rounded-lg text-xs font-medium transition-colors"
                                                        >
                                                            <MessageCircle className="w-3.5 h-3.5" /> WhatsApp
                                                        </a>
                                                    )}
                                                    <button onClick={() => toggleRow(lead.id)} className="p-1.5 text-slate-400 hover:text-white">
                                                        {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                                                    </button>
                                                </div>
                                            </td>
                                        </tr>

                                        {/* Expanded row with address + maps link */}
                                        {isExpanded && (
                                            <tr key={`${lead.id}-expanded`} className="bg-slate-900/40">
                                                <td colSpan={6} className="px-6 py-4">
                                                    <div className="grid grid-cols-2 gap-4 text-sm">
                                                        {meta.address && (
                                                            <div className="flex items-start gap-2 text-slate-400">
                                                                <MapPin className="w-4 h-4 mt-0.5 text-slate-500 flex-shrink-0" />
                                                                <span>{meta.address}</span>
                                                            </div>
                                                        )}
                                                        <div className="flex items-center gap-4 text-xs text-slate-500">
                                                            {meta.rating && <span>⭐ {meta.rating} estrellas</span>}
                                                            {meta.reviews && <span>💬 {meta.reviews} reseñas</span>}
                                                            {meta.maps_url && (
                                                                <a href={meta.maps_url} target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:underline">
                                                                    Ver en Google Maps →
                                                                </a>
                                                            )}
                                                        </div>
                                                    </div>
                                                </td>
                                            </tr>
                                        )}
                                    </>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Scrape Modal */}
            {showScrapeModal && (
                <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4">
                    <div className="bg-slate-800 border border-slate-700 rounded-2xl p-6 w-full max-w-md shadow-2xl">
                        <h3 className="text-xl font-bold text-white mb-1">🔍 Scrape en Vivo</h3>
                        <p className="text-slate-400 text-sm mb-6">Buscá negocios en Google Maps y los leads se importan automáticamente.</p>

                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-slate-300 mb-1.5">Query de búsqueda</label>
                                <input
                                    type="text"
                                    value={scrapeQuery}
                                    onChange={e => setScrapeQuery(e.target.value)}
                                    placeholder='ej: "agencias de marketing Buenos Aires"'
                                    className="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 text-white text-sm focus:outline-none focus:border-blue-500 placeholder-slate-600"
                                    disabled={scraping}
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-slate-300 mb-1.5">Máximo de resultados</label>
                                <select
                                    value={scrapeMax}
                                    onChange={e => setScrapeMax(Number(e.target.value))}
                                    className="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 text-white text-sm focus:outline-none focus:border-blue-500"
                                    disabled={scraping}
                                >
                                    <option value={10}>10 negocios (~2 min)</option>
                                    <option value={20}>20 negocios (~4 min)</option>
                                    <option value={40}>40 negocios (~8 min)</option>
                                    <option value={60}>60 negocios (~12 min)</option>
                                </select>
                            </div>
                        </div>

                        {/* Progress indicator */}
                        {scraping && (
                            <div className="mt-5 bg-slate-900/60 rounded-xl p-4 border border-slate-700">
                                <div className="flex items-center gap-3 text-blue-400">
                                    <div className="w-4 h-4 border-2 border-blue-400 border-t-transparent rounded-full animate-spin flex-shrink-0" />
                                    <div>
                                        <div className="font-medium text-sm">Scrapeando Google Maps...</div>
                                        <div className="text-xs text-slate-500 mt-0.5">Esto puede tardar varios minutos según los resultados solicitados.</div>
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* Success result */}
                        {scrapeResult && (
                            <div className="mt-5 bg-green-500/10 border border-green-500/30 rounded-xl p-4">
                                <div className="font-semibold text-green-400 mb-2">✅ Scrape completado</div>
                                <div className="grid grid-cols-3 gap-3 text-center">
                                    <div className="bg-slate-800 rounded-lg p-2">
                                        <div className="text-xl font-bold text-white">{scrapeResult.inserted}</div>
                                        <div className="text-xs text-slate-400">Nuevos</div>
                                    </div>
                                    <div className="bg-slate-800 rounded-lg p-2">
                                        <div className="text-xl font-bold text-white">{scrapeResult.skipped}</div>
                                        <div className="text-xs text-slate-400">Duplicados</div>
                                    </div>
                                    <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-2">
                                        <div className="text-xl font-bold text-red-400">{scrapeResult.hot_leads}</div>
                                        <div className="text-xs text-red-400/70">🔥 Calientes</div>
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* Error */}
                        {scrapeError && (
                            <div className="mt-5 bg-red-500/10 border border-red-500/30 rounded-xl p-3 text-red-400 text-sm">
                                ❌ {scrapeError}
                            </div>
                        )}

                        <div className="flex gap-3 mt-6">
                            <button
                                onClick={() => { setShowScrapeModal(false); setScraping(false); }}
                                className="flex-1 bg-slate-700 hover:bg-slate-600 text-slate-300 px-4 py-2.5 rounded-xl font-medium transition-colors"
                                disabled={scraping}
                            >
                                {scrapeResult ? 'Cerrar' : 'Cancelar'}
                            </button>
                            {!scrapeResult && (
                                <button
                                    onClick={handleScrape}
                                    disabled={scraping || !scrapeQuery.trim()}
                                    className="flex-1 bg-blue-600 hover:bg-blue-500 text-white px-4 py-2.5 rounded-xl font-semibold transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
                                >
                                    {scraping ? (
                                        <>
                                            <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                                            Scrapeando...
                                        </>
                                    ) : (
                                        <>
                                            <Search className="w-4 h-4" /> Iniciar Scraping
                                        </>
                                    )}
                                </button>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
