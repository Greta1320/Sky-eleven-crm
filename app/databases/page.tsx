'use client';

import { useState } from 'react';
import { ArrowLeft, Upload, Database } from 'lucide-react';
import Link from 'next/link';

export default function DatabasesPage() {
    const [file, setFile] = useState<File | null>(null);
    const [uploading, setUploading] = useState(false);

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            setFile(e.target.files[0]);
        }
    };

    const handleUpload = async () => {
        if (!file) return;

        setUploading(true);
        try {
            // TODO: Implementar upload de CSV
            console.log('Uploading file:', file.name);
            alert('Funcionalidad de upload en desarrollo');
        } catch (error) {
            console.error('Error uploading file:', error);
        } finally {
            setUploading(false);
        }
    };

    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-6">
            {/* Header */}
            <div className="mb-8">
                <Link href="/" className="inline-flex items-center gap-2 text-slate-400 hover:text-white transition-colors mb-4">
                    <ArrowLeft className="w-4 h-4" />
                    Volver
                </Link>
                <h1 className="text-4xl font-bold text-white">Bases de Datos</h1>
                <p className="text-slate-400 mt-2">Importa contactos masivamente</p>
            </div>

            {/* Upload Section */}
            <div className="max-w-2xl mx-auto">
                <div className="bg-slate-800/30 backdrop-blur-sm border border-slate-700 rounded-xl p-8">
                    <div className="text-center mb-8">
                        <Database className="w-16 h-16 text-blue-400 mx-auto mb-4" />
                        <h3 className="text-2xl font-semibold text-white mb-2">Importar Contactos</h3>
                        <p className="text-slate-400">
                            Sube un archivo CSV con tus contactos para iniciar campañas de prospección
                        </p>
                    </div>

                    {/* File Input */}
                    <div className="mb-6">
                        <label className="block text-slate-300 mb-2">Seleccionar archivo CSV</label>
                        <input
                            type="file"
                            accept=".csv"
                            onChange={handleFileChange}
                            className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-blue-500"
                        />
                        {file && (
                            <p className="text-slate-400 text-sm mt-2">
                                Archivo seleccionado: {file.name}
                            </p>
                        )}
                    </div>

                    {/* Upload Button */}
                    <button
                        onClick={handleUpload}
                        disabled={!file || uploading}
                        className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-slate-700 disabled:cursor-not-allowed text-white font-semibold py-3 px-6 rounded-lg transition-colors flex items-center justify-center gap-2"
                    >
                        <Upload className="w-5 h-5" />
                        {uploading ? 'Subiendo...' : 'Importar Contactos'}
                    </button>

                    {/* Instructions */}
                    <div className="mt-8 bg-slate-700/30 border border-slate-600 rounded-lg p-4">
                        <h4 className="text-white font-semibold mb-2">Formato del CSV</h4>
                        <p className="text-slate-400 text-sm mb-2">El archivo debe tener las siguientes columnas:</p>
                        <ul className="text-slate-400 text-sm space-y-1">
                            <li>• <strong>phone</strong> (requerido): Número de teléfono con código de país</li>
                            <li>• <strong>name</strong> (opcional): Nombre del contacto</li>
                            <li>• <strong>email</strong> (opcional): Email del contacto</li>
                            <li>• <strong>source</strong> (requerido): instagram, linkedin, whatsapp, o manual</li>
                        </ul>
                    </div>
                </div>
            </div>
        </div>
    );
}
