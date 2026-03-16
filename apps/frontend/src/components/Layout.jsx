import React from 'react';

const Layout = ({ children }) => {
  return (
    <div className="flex h-screen w-full overflow-hidden bg-[#0b0c10] text-white font-sans">
      {/* 1. Стеклянный Sidebar (Левая панель) */}
      <aside className="w-20 flex flex-col items-center py-8 bg-white/5 border-r border-white/5 backdrop-blur-2xl z-20">
        <div className="w-10 h-10 bg-vikki-accent rounded-xl mb-12 flex items-center justify-center shadow-glow-blue cursor-pointer hover:scale-110 transition-transform">
          <span className="font-bold text-black text-xl">V</span>
        </div>
        
        <nav className="flex flex-col space-y-8">
          {['📊', '💸', '📄', '⚙️'].map((icon, idx) => (
            <div key={idx} className="w-10 h-10 rounded-lg bg-white/5 hover:bg-white/10 flex items-center justify-center transition-all cursor-pointer group">
              <span className="opacity-40 group-hover:opacity-100 transition-opacity">{icon}</span>
            </div>
          ))}
        </nav>
      </aside>

      {/* 2. Основная рабочая область */}
      <main className="flex-1 relative flex flex-col">
        {/* Декоративное пятно света на фоне (тот самый Glow) */}
        <div className="absolute top-[-20%] right-[-10%] w-[600px] h-[600px] bg-vikki-accent/10 rounded-full blur-[120px] pointer-events-none" />
        <div className="absolute bottom-[-10%] left-[10%] w-[400px] h-[400px] bg-purple-500/5 rounded-full blur-[100px] pointer-events-none" />
        
        {/* Контент, который мы передаем внутрь */}
        <div className="z-10 flex-1 flex flex-col relative overflow-y-auto">
          {children}
        </div>
      </main>
    </div>
  );
};

export default Layout;