import React from 'react';
import { motion } from 'framer-motion';
import { 
  Terminal, 
  BarChart3, 
  LayoutGrid, 
  Bell, 
  Settings, 
  LogOut,
  Zap
} from 'lucide-react';

const SidebarItem = ({ icon: Icon, label, active, onClick, alert }) => (
  <motion.button
    onClick={onClick}
    whileHover={{ scale: 1.1 }}
    whileTap={{ scale: 0.95 }}
    className={`relative group flex items-center justify-center w-12 h-12 my-2 rounded-xl transition-all duration-300 outline-none
      ${active 
        ? 'bg-vikki-accent/20 text-vikki-accent shadow-[0_0_20px_rgba(0,210,255,0.2)]' 
        : 'text-white/40 hover:text-white hover:bg-white/5'}`}
  >
    {/* Активный индикатор */}
    {active && (
      <motion.div 
        layoutId="activeSide"
        className="absolute -left-4 w-1 h-8 bg-vikki-accent rounded-r-full shadow-[0_0_15px_#00d2ff]"
      />
    )}

    <Icon size={22} strokeWidth={active ? 2.5 : 1.5} />

    {/* Точка уведомления */}
    {alert && (
      <span className="absolute top-2 right-2 w-2 h-2 bg-red-500 rounded-full border-2 border-black animate-pulse shadow-[0_0_10px_#ef4444]" />
    )}

    {/* Тултип (выезжающая подсказка) */}
    <div className="absolute left-16 px-3 py-1.5 bg-black/90 backdrop-blur-xl border border-white/10 rounded-lg opacity-0 group-hover:opacity-100 translate-x-[-10px] group-hover:translate-x-0 transition-all pointer-events-none z-[200]">
      <span className="text-[10px] text-white font-black uppercase tracking-[0.2em] whitespace-nowrap">
        {label}
      </span>
    </div>
  </motion.button>
);

const Sidebar = ({ activeTab = 'dashboard', onTabChange }) => {
  return (
    <aside className="fixed left-0 top-0 bottom-0 w-20 bg-black/40 backdrop-blur-3xl border-r border-white/5 z-[150] flex flex-col items-center py-6 shadow-2xl">
      
      {/* LOGO / VIKKI LOGO */}
      <div className="mb-12 relative">
        <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-vikki-accent to-blue-600 flex items-center justify-center shadow-[0_0_30px_rgba(0,210,255,0.3)]">
          <Zap size={24} className="text-white fill-white" />
        </div>
        <div className="absolute -bottom-1 -right-1 w-3 h-3 bg-vikki-up rounded-full border-2 border-black" />
      </div>

      {/* PRIMARY NAVIGATION */}
      <div className="flex-1 flex flex-col items-center">
        <SidebarItem 
          icon={Terminal} 
          label="Командный центр" 
          active={activeTab === 'dashboard'} 
          onClick={() => onTabChange?.('dashboard')}
        />
        <SidebarItem 
          icon={BarChart3} 
          label="Архив Аналитики" 
          active={activeTab === 'analytics'} 
          onClick={() => onTabChange?.('analytics')}
        />
        <SidebarItem 
          icon={LayoutGrid} 
          label="Конструктор блоков" 
          active={activeTab === 'widgets'} 
          onClick={() => onTabChange?.('widgets')}
        />
        <SidebarItem 
          icon={Bell} 
          label="Уведомления" 
          alert={true}
          active={activeTab === 'alerts'} 
          onClick={() => onTabChange?.('alerts')}
        />
      </div>

      {/* BOTTOM ACTIONS */}
      <div className="flex flex-col items-center border-t border-white/5 pt-6">
        <SidebarItem 
          icon={Settings} 
          label="Настройки ядра" 
          onClick={() => onTabChange?.('settings')}
        />
        <SidebarItem 
          icon={LogOut} 
          label="Завершить сессию" 
          onClick={() => console.log('Exit')}
        />
      </div>

    </aside>
  );
};

export default Sidebar;