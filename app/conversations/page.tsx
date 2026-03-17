'use client';

import { useState, useEffect } from 'react';
import { ArrowLeft, MessageSquare, Phone } from 'lucide-react';
import Link from 'next/link';

interface Conversation {
    id: string;
    lead: {
        id: string;
        phone: string;
        name?: string;
        source: string;
    };
    channel: string;
    last_message_at: string;
    unread_count: number;
}

export default function ConversationsPage() {
    const [conversations, setConversations] = useState<Conversation[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchConversations();
    }, []);

    const fetchConversations = async () => {
        try {
            // TODO: Crear endpoint /api/conversations
            setLoading(false);
        } catch (error) {
            console.error('Error fetching conversations:', error);
            setLoading(false);
        }
    };

    const getChannelIcon = (channel: string) => {
        switch (channel) {
            case 'whatsapp': return '💬';
            case 'instagram': return '📸';
            case 'linkedin': return '💼';
            default: return '📱';
        }
    };

    if (loading) {
        return (
            <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center">
                <div className="text-white text-xl">Cargando conversaciones...</div>
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
                <h1 className="text-4xl font-bold text-white">Conversaciones</h1>
                <p className="text-slate-400 mt-2">Gestiona todas tus conversaciones en un solo lugar</p>
            </div>

            {/* Conversations List */}
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                {conversations.length === 0 ? (
                    <div className="col-span-full bg-slate-800/30 backdrop-blur-sm border border-slate-700 rounded-xl p-12 text-center">
                        <MessageSquare className="w-16 h-16 text-slate-600 mx-auto mb-4" />
                        <h3 className="text-xl font-semibold text-white mb-2">No hay conversaciones activas</h3>
                        <p className="text-slate-400">
                            Las conversaciones aparecerán aquí cuando los leads comiencen a interactuar
                        </p>
                    </div>
                ) : (
                    conversations.map((conv) => (
                        <div
                            key={conv.id}
                            className="bg-slate-800/30 backdrop-blur-sm border border-slate-700 rounded-xl p-4 hover:bg-slate-700/30 transition-all cursor-pointer"
                        >
                            <div className="flex items-start justify-between mb-3">
                                <div className="flex items-center gap-3">
                                    <div className="text-3xl">{getChannelIcon(conv.channel)}</div>
                                    <div>
                                        <p className="text-white font-medium">{conv.lead.name || conv.lead.phone}</p>
                                        <p className="text-slate-400 text-sm">{conv.channel}</p>
                                    </div>
                                </div>
                                {conv.unread_count > 0 && (
                                    <span className="bg-blue-500 text-white text-xs px-2 py-1 rounded-full">
                                        {conv.unread_count}
                                    </span>
                                )}
                            </div>

                            <div className="flex items-center gap-2 text-slate-400 text-sm">
                                <Phone className="w-4 h-4" />
                                <span>{conv.lead.phone}</span>
                            </div>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
}
