import React from 'react';
import GlassCard from './GlassCard';

const EdoWidget = () => {
  const docs = [
    { id: 1, name: 'Счет-фактура №45', status: 'Ожидает', date: '14:20' },
    { id: 2, name: 'Акт сверки: ООО "Вектор"', status: 'Подписан', date: 'Вчера' }
  ];

  return (
    <GlassCard title="Документы ЭДО (СБИС)" className="w-full">
      <div className="space-y-4">
        {docs.map(doc => (
          <div key={doc.id} className="flex items-center justify-between group/item cursor-pointer">
            <div className="flex items-center space-x-4">
              <div className="w-8 h-8 rounded-lg bg-white/5 flex items-center justify-center group-hover/item:bg-vikki-accent/20 transition-colors">
                <span className="text-xs">📄</span>
              </div>
              <div>
                <p className="text-sm font-light text-white/80">{doc.name}</p>
                <p className="text-[10px] text-white/20 uppercase tracking-wider">{doc.date}</p>
              </div>
            </div>
            <span className={`text-[9px] px-2 py-1 rounded-full border ${
              doc.status === 'Подписан' ? 'border-vikki-success/20 text-vikki-success' : 'border-white/10 text-white/40'
            }`}>
              {doc.status}
            </span>
          </div>
        ))}
      </div>
    </GlassCard>
  );
};

export default EdoWidget;