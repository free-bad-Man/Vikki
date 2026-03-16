import React from 'react';

const GlassCard = ({ children, title, className = "" }) => {
  return (
    <div className={`glass-panel rounded-[2rem] p-8 transition-all duration-500 hover:border-white/20 group ${className}`}>
      {title && (
        <div className="flex justify-between items-center mb-6">
          <h3 className="text-[11px] font-semibold uppercase tracking-[0.25em] text-white/40 group-hover:text-vikki-accent/60 transition-colors">
            {title}
          </h3>
          <div className="w-1.5 h-1.5 rounded-full bg-vikki-accent/30 group-hover:bg-vikki-accent transition-all" />
        </div>
      )}
      <div className="relative overflow-hidden">
        {children}
      </div>
    </div>
  );
};

export default GlassCard;