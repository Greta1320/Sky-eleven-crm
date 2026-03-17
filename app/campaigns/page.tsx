'use client';

import { useState, useEffect } from 'react';
import Papa from 'papaparse';
import { Upload, Plus, Play, Pause, AlertCircle, Search, ExternalLink } from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';

interface Campaign {
    id: number;
    name: string;
    niche: string;
    location: string;
    status: string;
}

export default function CampaignsPage() {
    const [campaigns, setCampaigns] = useState<Campaign[]>([]);
    const [loading, setLoading] = useState(true);
    const [isCreating, setIsCreating] = useState(false);
    const router = useRouter();

    const [newName, setNewName] = useState('');
    const [newNiche, setNewNiche] = useState('');
    const [newLocation, setNewLocation] = useState('');
    const [newScrapeQuery, setNewScrapeQuery] = useState('');

    useEffect(() => {
        fetchCampaigns();
    }, []);

    const fetchCampaigns = async () => {
        try {
            const res = await fetch('/api/campaigns');
            const data = await res.json();
            if (data.success) {
                setCampaigns(data.data);
            }
        } catch (error) {
            console.error('Failed to fetch campaigns', error);
        } finally {
            setLoading(false);
        }
    };

    const handleCreate = async () => {
        if (!newName) return;
        setIsCreating(true);
        try {
            const res = await fetch('/api/campaigns', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: newName, niche: newNiche, location: newLocation, scrape_query: newScrapeQuery })
            });
            const data = await res.json();
            if (res.ok && data.success) {
                setNewName('');
                setNewNiche('');
                setNewLocation('');
                setNewScrapeQuery('');
                fetchCampaigns();
                // If they set a scrape query, go straight to the campaign detail to run it
                if (newScrapeQuery.trim()) {
                    router.push(`/campaigns/${data.data.id}`);
                }
            }
        } finally {
            setIsCreating(false);
        }
    };

    const handleFileUpload = (campaignId: number, event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (!file) return;

        Papa.parse(file, {
            header: true,
            skipEmptyLines: true,
            complete: async (results) => {
                try {
                    const res = await fetch(`/api/campaigns/${campaignId}/upload`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(results.data)
                    });
                    const resData = await res.json();
                    if (resData.success) {
                        alert(`Subida completada: ${resData.inserted} leads nuevos.`);
                        fetchCampaigns();
                    } else {
                        alert(`Error: ${resData.error}`);
                    }
                } catch (e) {
                    alert('Error subiendo datos');
                }
            }
        });
    };

    return (
        <div className="p-8 max-w-6xl mx-auto space-y-8">
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-3xl font-bold text-white mb-2">Campañas de Prospección</h1>
                    <p className="text-slate-400">Gestiona tus búsquedas e importa leads extraídos.</p>
                </div>
            </div>

            {/* Crear Nueva Campaña */}
            <div className="bg-slate-800 rounded-xl p-6 border border-slate-700">
                <h2 className="text-xl font-semibold text-white mb-4">Nueva Campaña</h2>
                <div className="grid grid-cols-2 gap-4 mb-4">
                    <div>
                        <label className="block text-sm font-medium text-slate-400 mb-1">Nombre (ej: Agencias CABA)</label>
                        <input
                            type="text"
                            className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-blue-500"
                            value={newName} onChange={e => setNewName(e.target.value)}
                            placeholder="Nombre de la campaña"
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-slate-400 mb-1">Nicho</label>
                        <input
                            type="text"
                            className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-blue-500"
                            value={newNiche} onChange={e => setNewNiche(e.target.value)}
                            placeholder="ej: marketing, inmobiliaria"
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-slate-400 mb-1">Ubicación</label>
                        <input
                            type="text"
                            className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-blue-500"
                            value={newLocation} onChange={e => setNewLocation(e.target.value)}
                            placeholder="ej: Buenos Aires"
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-slate-400 mb-1">Query de scraping <span className="text-slate-600">(opcional, abre scraper directo)</span></label>
                        <input
                            type="text"
                            className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-blue-500"
                            value={newScrapeQuery} onChange={e => setNewScrapeQuery(e.target.value)}
                            placeholder='ej: "agencias de marketing Buenos Aires"'
                        />
                    </div>
                </div>
                <div className="flex justify-end">
                    <button
                        onClick={handleCreate}
                        disabled={isCreating || !newName}
                        className="bg-blue-600 hover:bg-blue-500 text-white px-6 py-2.5 rounded-lg font-medium flex items-center gap-2 transition-colors disabled:opacity-50"
                    >
                        <Plus className="w-5 h-5" />
                        {isCreating ? 'Creando...' : 'Crear Campaña'}
                    </button>
                </div>
            </div>

            {/* Lista de Campañas */}
            <div className="space-y-4">
                {loading ? (
                    <p className="text-slate-400">Cargando campañas...</p>
                ) : campaigns.length === 0 ? (
                    <div className="text-center p-12 bg-slate-800/50 rounded-xl border border-slate-700/50">
                        <AlertCircle className="w-12 h-12 text-slate-500 mx-auto mb-4" />
                        <h3 className="text-lg font-medium text-slate-300">No hay campañas</h3>
                        <p className="text-slate-500">Crea tu primera campaña arriba.</p>
                    </div>
                ) : (
                    campaigns.map(campaign => (
                        <div key={campaign.id} className="bg-slate-800 rounded-xl p-6 border border-slate-700 flex items-center justify-between group">
                            <div>
                                <h3 className="text-xl font-bold text-white flex items-center gap-3">
                                    {campaign.name}
                                    <span className={`text-xs px-2 py-1 rounded-full font-medium ${campaign.status === 'active' ? 'bg-green-500/10 text-green-400 border border-green-500/20' : 'bg-slate-700 text-slate-300'}`}>
                                        {campaign.status}
                                    </span>
                                </h3>
                                <div className="flex gap-4 mt-2 text-sm text-slate-400">
                                    <span>🎯 <strong>Nicho:</strong> {campaign.niche || 'N/A'}</span>
                                    <span>📍 <strong>Ubicación:</strong> {campaign.location || 'N/A'}</span>
                                </div>
                            </div>

                            <div className="flex items-center gap-3">
                                <label className="cursor-pointer bg-slate-700 hover:bg-slate-600 text-white px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 transition-colors">
                                    <Upload className="w-4 h-4" />
                                    CSV
                                    <input
                                        type="file"
                                        accept=".csv"
                                        className="hidden"
                                        onChange={(e) => handleFileUpload(campaign.id, e)}
                                    />
                                </label>

                                <Link
                                    href={`/campaigns/${campaign.id}`}
                                    className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg text-sm font-semibold transition-colors"
                                >
                                    <Search className="w-4 h-4" /> Scrape & Ver
                                </Link>

                                <Link
                                    href={`/campaigns/${campaign.id}`}
                                    className="p-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-slate-300 transition-colors"
                                    title="Ver detalles"
                                >
                                    <ExternalLink className="w-4 h-4" />
                                </Link>
                            </div>
                        </div>
                    ))
                )}
            </div>
        </div >
    );
}
