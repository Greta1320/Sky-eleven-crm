import Link from 'next/link';
import { LayoutDashboard, MessageSquare, BarChart3, Database } from 'lucide-react';

export default function Home() {
    return (
        <main className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
            <div className="container mx-auto px-4 py-16">
                {/* Header */}
                <div className="text-center mb-16">
                    <h1 className="text-6xl font-bold text-white mb-4">
                        AI CRM
                    </h1>
                    <p className="text-xl text-slate-300">
                        Sistema de prospección inteligente multi-canal
                    </p>
                </div>

                {/* Cards Grid */}
                <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 max-w-6xl mx-auto">
                    {/* Pipeline Card */}
                    <Link href="/pipeline">
                        <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl p-6 hover:bg-slate-700/50 transition-all cursor-pointer group">
                            <div className="flex items-center justify-between mb-4">
                                <LayoutDashboard className="w-8 h-8 text-blue-400 group-hover:text-blue-300" />
                                <span className="text-sm text-slate-400">Vista Kanban</span>
                            </div>
                            <h3 className="text-xl font-semibold text-white mb-2">Pipeline</h3>
                            <p className="text-slate-400 text-sm">
                                Gestiona leads en tiempo real con drag & drop
                            </p>
                        </div>
                    </Link>

                    {/* Conversaciones Card */}
                    <Link href="/conversations">
                        <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl p-6 hover:bg-slate-700/50 transition-all cursor-pointer group">
                            <div className="flex items-center justify-between mb-4">
                                <MessageSquare className="w-8 h-8 text-green-400 group-hover:text-green-300" />
                                <span className="text-sm text-slate-400">Multi-canal</span>
                            </div>
                            <h3 className="text-xl font-semibold text-white mb-2">Conversaciones</h3>
                            <p className="text-slate-400 text-sm">
                                WhatsApp, Instagram y LinkedIn unificados
                            </p>
                        </div>
                    </Link>

                    {/* Campañas Card */}
                    <Link href="/campaigns">
                        <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl p-6 hover:bg-slate-700/50 transition-all cursor-pointer group">
                            <div className="flex items-center justify-between mb-4">
                                <BarChart3 className="w-8 h-8 text-purple-400 group-hover:text-purple-300" />
                                <span className="text-sm text-slate-400">Outreach IA</span>
                            </div>
                            <h3 className="text-xl font-semibold text-white mb-2">Campañas</h3>
                            <p className="text-slate-400 text-sm">
                                Prospección automatizada y gestión de leads extraídos
                            </p>
                        </div>
                    </Link>

                    {/* Bases Card */}
                    <Link href="/databases">
                        <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl p-6 hover:bg-slate-700/50 transition-all cursor-pointer group">
                            <div className="flex items-center justify-between mb-4">
                                <Database className="w-8 h-8 text-orange-400 group-hover:text-orange-300" />
                                <span className="text-sm text-slate-400">Importar</span>
                            </div>
                            <h3 className="text-xl font-semibold text-white mb-2">Bases de Datos</h3>
                            <p className="text-slate-400 text-sm">
                                Carga masiva de contactos y campañas
                            </p>
                        </div>
                    </Link>
                </div>

                {/* Status */}
                <div className="mt-16 text-center">
                    <div className="inline-flex items-center gap-2 bg-green-500/10 border border-green-500/20 rounded-full px-4 py-2">
                        <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                        <span className="text-green-400 text-sm font-medium">Sistema activo</span>
                    </div>
                </div>
            </div>
        </main>
    );
}
