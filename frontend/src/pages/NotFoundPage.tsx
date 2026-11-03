import React from 'react';
import { Link } from 'react-router-dom';
import { HelpCircle, ArrowLeft } from 'lucide-react';

export const NotFoundPage: React.FC = () => {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <div className="p-4 rounded-2xl bg-slate-900 border border-slate-800 text-slate-400 mb-4">
        <HelpCircle className="w-10 h-10" />
      </div>
      <h2 className="text-xl font-bold text-white">Resource Not Found</h2>
      <p className="text-xs text-slate-400 mt-1 max-w-sm">
        The requested view does not exist in Phase 1 foundation.
      </p>
      <Link
        to="/"
        className="mt-6 inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-500 transition"
      >
        <ArrowLeft className="w-3.5 h-3.5" />
        <span>Return to Infrastructure Shell</span>
      </Link>
    </div>
  );
};
