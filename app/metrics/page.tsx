'use client';

import { useState, useEffect } from 'react';
import { ArrowLeft, TrendingUp, Users, MessageCircle, Target } from 'lucide-react';
import Link from 'next/link';

interface Stats {
    totalLeads: number;
    activeConversations: number;
    conversionRate: number;
    avgScore: number;
    bySource: {
        instagram: number;
        linkedin: number;
        whatsapp: number;
    };
}

export default function MetricsPage() {
    const [stats, setStats] = useState<Stats>({
        totalLeads: 0,
        activeConversations: 0,
        conversionRate: 0,
        avgScore: 0,
        bySource: {
            instagram: 0,
            linkedin: 0,
            whatsapp: 0,
        },
    });
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchStats();
    }, []);

    const fetchStats = async () => {
        try {
            const response = await fetch('/api/leads?limit=1000');
            const data = await response.json();

            if (data.success) {
                const leads = data.data;
                const bySource = {
                    instagram: leads.filter((l: any) => l.source === 'instagram').length,
                    linkedin: leads.filter((l: any) => l.source === 'linkedin').length,
                    whatsapp: leads.filter((l: any) => l.source === 'whatsapp').length,
                };

                const totalScore = leads.reduce((sum: number, l: any) => sum + l.score, 0);
                const closed = leads.filter((l: any) => l.stage === 'closed').length;

                setStats({
                    totalLeads: leads.length,
                    activeConversations: leads.filter((l: any) => l.stage !== 'closed' && l.stage !== 'lost').length,
                    conversionRate: leads.length > 0 ? (closed / leads.length) * 100 : 0,
                    avgScore: leads.length > 0 ? totalScore / leads.length : 0,
                    bySource,
                });
            }
        } catch (error) {
            console.error('Error fetching stats:', error);
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return (
            <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center">
                <div className="text-white text-xl">Cargando métricas...</div>
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
                <h1 className="text-4xl font-bold text-white">Métricas</h1>
                <p className="text-slate-400 mt-2">Análisis de performance del CRM</p>
            </div>

            {/* KPIs Grid */}
            <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
                {/* Total Leads */}
                <div className="bg-slate-800/30 backdrop-blur-sm border border-slate-700 rounded-xl p-6">
                    <div className="flex items-center justify-between mb-4">
                        <Users className="w-8 h-8 text-blue-400" />
                        <TrendingUp className="w-5 h-5 text-green-400" />
                    </div>
                    <p className="text-slate-400 text-sm mb-1">Total Leads</p>
                    <p className="text-4xl font-bold text-white">{stats.totalLeads}</p>
                </div>

                {/* Active Conversations */}
                <div className="bg-slate-800/30 backdrop-blur-sm border border-slate-700 rounded-xl p-6">
                    <div className="flex items-center justify-between mb-4">
                        <MessageCircle className="w-8 h-8 text-green-400" />
                    </div>
                    <p className="text-slate-400 text-sm mb-1">Conversaciones Activas</p>
                    <p className="text-4xl font-bold text-white">{stats.activeConversations}</p>
                </div>

                {/* Conversion Rate */}
                <div className="bg-slate-800/30 backdrop-blur-sm border border-slate-700 rounded-xl p-6">
                    <div className="flex items-center justify-between mb-4">
                        <Target className="w-8 h-8 text-purple-400" />
                    </div>
                    <p className="text-slate-400 text-sm mb-1">Tasa de Conversión</p>
                    <p className="text-4xl font-bold text-white">{stats.conversionRate.toFixed(1)}%</p>
                </div>

                {/* Avg Score */}
                <div className="bg-slate-800/30 backdrop-blur-sm border border-slate-700 rounded-xl p-6">
                    <div className="flex items-center justify-between mb-4">
                        <TrendingUp className="w-8 h-8 text-orange-400" />
                    </div>
                    <p className="text-slate-400 text-sm mb-1">Score Promedio</p>
                    <p className="text-4xl font-bold text-white">{stats.avgScore.toFixed(1)}</p>
                </div>
            </div>

            {/* Leads por Canal */}
            <div className="bg-slate-800/30 backdrop-blur-sm border border-slate-700 rounded-xl p-6">
                <h3 className="text-xl font-semibold text-white mb-6">Leads por Canal</h3>
                <div className="space-y-4">
                    {/* Instagram */}
                    <div>
                        <div className="flex items-center justify-between mb-2">
                            <span className="text-slate-300">📸 Instagram</span>
                            <span className="text-white font-semibold">{stats.bySource.instagram}</span>
                        </div>
                        <div className="w-full bg-slate-700 rounded-full h-2">
                            <div
                                className="bg-pink-500 h-2 rounded-full"
                                style={{ width: `${(stats.bySource.instagram / stats.totalLeads) * 100}%` }}
                            ></div>
                        </div>
                    </div>

                    {/* LinkedIn */}
                    <div>
                        <div className="flex items-center justify-between mb-2">
                            <span className="text-slate-300">💼 LinkedIn</span>
                            <span className="text-white font-semibold">{stats.bySource.linkedin}</span>
                        </div>
                        <div className="w-full bg-slate-700 rounded-full h-2">
                            <div
                                className="bg-blue-500 h-2 rounded-full"
                                style={{ width: `${(stats.bySource.linkedin / stats.totalLeads) * 100}%` }}
                            ></div>
                        </div>
                    </div>

                    {/* WhatsApp */}
                    <div>
                        <div className="flex items-center justify-between mb-2">
                            <span className="text-slate-300">💬 WhatsApp</span>
                            <span className="text-white font-semibold">{stats.bySource.whatsapp}</span>
                        </div>
                        <div className="w-full bg-slate-700 rounded-full h-2">
                            <div
                                className="bg-green-500 h-2 rounded-full"
                                style={{ width: `${(stats.bySource.whatsapp / stats.totalLeads) * 100}%` }}
                            ></div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
