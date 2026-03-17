'use client';

import { useState, useEffect } from 'react';
import { ArrowLeft } from 'lucide-react';
import Link from 'next/link';

interface Lead {
    id: string;
    phone: string;
    name?: string;
    email?: string;
    source: string;
    intent?: string;
    score: number;
    stage: string;
    created_at: string;
}

interface Column {
    id: string;
    title: string;
    leads: Lead[];
}

export default function PipelinePage() {
    const [columns, setColumns] = useState<Column[]>([
        { id: 'new', title: 'Nuevo', leads: [] },
        { id: 'contacted', title: 'Contactado', leads: [] },
        { id: 'qualified', title: 'Calificado', leads: [] },
        { id: 'call', title: 'Llamada', leads: [] },
        { id: 'closed', title: 'Cerrado', leads: [] },
    ]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchLeads();
    }, []);

    const fetchLeads = async () => {
        try {
            const response = await fetch('/api/leads?limit=100');
            const data = await response.json();

            if (data.success) {
                // Agrupar leads por stage
                const groupedLeads = columns.map(column => ({
                    ...column,
                    leads: data.data.filter((lead: Lead) => lead.stage === column.id)
                }));
                setColumns(groupedLeads);
            }
        } catch (error) {
            console.error('Error fetching leads:', error);
        } finally {
            setLoading(false);
        }
    };

    const getSourceColor = (source: string) => {
        switch (source) {
            case 'instagram': return 'bg-pink-500/20 text-pink-400 border-pink-500/30';
            case 'linkedin': return 'bg-blue-500/20 text-blue-400 border-blue-500/30';
            case 'whatsapp': return 'bg-green-500/20 text-green-400 border-green-500/30';
            default: return 'bg-gray-500/20 text-gray-400 border-gray-500/30';
        }
    };

    const getScoreColor = (score: number) => {
        if (score >= 6) return 'text-green-400';
        if (score >= 3) return 'text-yellow-400';
        return 'text-red-400';
    };

    if (loading) {
        return (
            <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center">
                <div className="text-white text-xl">Cargando pipeline...</div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-6">
            {/* Header */}
            <div className="mb-8">
                <Link href="/" className="inline-flex items-center gap-2 text-slate-400 hover:text-white transition-colors mb-4">
                    <ArrowLeft className="w-4 h-4" />
                    Volver
                </Link>
                <h1 className="text-4xl font-bold text-white">Pipeline de Leads</h1>
                <p className="text-slate-400 mt-2">Gestiona tus leads con drag & drop</p>
            </div>

            {/* Kanban Board */}
            <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
                {columns.map((column) => (
                    <div key={column.id} className="bg-slate-800/30 backdrop-blur-sm border border-slate-700 rounded-xl p-4">
                        {/* Column Header */}
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-lg font-semibold text-white">{column.title}</h3>
                            <span className="bg-slate-700 text-slate-300 text-sm px-2 py-1 rounded-full">
                                {column.leads.length}
                            </span>
                        </div>

                        {/* Leads */}
                        <div className="space-y-3">
                            {column.leads.map((lead) => (
                                <div
                                    key={lead.id}
                                    className="bg-slate-800/50 border border-slate-700 rounded-lg p-3 hover:bg-slate-700/50 transition-all cursor-pointer"
                                >
                                    <div className="flex items-start justify-between mb-2">
                                        <div>
                                            <p className="text-white font-medium">{lead.name || lead.phone}</p>
                                            {lead.name && <p className="text-slate-400 text-sm">{lead.phone}</p>}
                                        </div>
                                        <span className={`text-lg font-bold ${getScoreColor(lead.score)}`}>
                                            {lead.score}
                                        </span>
                                    </div>

                                    <div className="flex items-center gap-2">
                                        <span className={`text-xs px-2 py-1 rounded-full border ${getSourceColor(lead.source)}`}>
                                            {lead.source}
                                        </span>
                                        {lead.intent && (
                                            <span className="text-xs text-slate-400 truncate">
                                                {lead.intent.replace('_', ' ')}
                                            </span>
                                        )}
                                    </div>
                                </div>
                            ))}

                            {column.leads.length === 0 && (
                                <div className="text-center text-slate-500 text-sm py-8">
                                    Sin leads
                                </div>
                            )}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}
