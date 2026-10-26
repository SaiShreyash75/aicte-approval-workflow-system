import React from 'react';
import { AlertCircle } from 'lucide-react';

export default function StatutoryBanner() {
  return (
    <div className="bg-amber-500/10 border-b border-amber-300/40 text-amber-900 px-4 py-2 text-xs md:text-sm font-medium flex items-center justify-center gap-2 shadow-xs">
      <AlertCircle className="w-4 h-4 text-amber-600 shrink-0" />
      <span>
        <strong className="font-semibold uppercase tracking-wider text-amber-950">Statutory Mandate:</strong>{" "}
        Automated alerts support, but do not replace, statutory scrutiny and decisions of the competent authority.
      </span>
    </div>
  );
}
