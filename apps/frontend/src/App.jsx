import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence, useMotionValue, useTransform, animate } from 'framer-motion';
import Layout from './components/Layout';
import VikkiInput from './components/VikkiInput';
import EdoWidget from './components/EdoWidget';
import { Scene } from './components/ui/hero-section';
import { 
  Receipt, Eye, EyeOff, Activity, Clock, TrendingUp, Sparkles, Box
} from 'lucide-react';

// Компонент анимированного счетчика баланса
const Counter = ({ value, isPrivacy }) => {
  const count = useMotionValue(0);
  const rounded = useTransform(count, (latest) => 
    new Intl.NumberFormat('ru-RU', { minimumFractionDigits: 2 }).format(latest)
  );

  useEffect(() => {
    const controls = animate(count, value, { duration: 2.5, ease: [0.16, 1, 0.3, 1] });
    return controls.stop;
  }, [value]);

  return (
    <motion.span className={isPrivacy ? 'blur-2xl opacity-10 transition-all duration-500' : 'transition-all duration-500'}>
      <motion.span>{rounded}</motion.span>
    </motion.span>
  );
};

function App() {
  const [uptime, setUptime] = useState('00:00:00');
  const [isPrivacy, setIsPrivacy] = useState(false);
  const [isInputFocused, setIsInputFocused] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [hoveredBar, setHoveredBar] = useState(null);

  const financialData = [
    { day: 'ПН', in: 45000, out: 15000, forecast: false }, 
    { day: 'ВТ', in: 25000, out: 35000, forecast: false },
    { day: 'СР', in: 70000, out: 20000, forecast: false }, 
    { day: 'ЧТ', in: 40000, out: 30000, forecast: false },
    { day: 'ПТ', in: 85000, out: 50000, forecast: false }, 
    { day: 'СБ', in: 50000, out: 25000, forecast: true },
    { day: 'ВС', in: 65000, out: 20000, forecast: true }
  ];

  const maxVal = Math.max(...financialData.flatMap(d => [d.in, d.out]));

  const transactions = [
    { id: 1, name: "ООО 'Альфа-Маркет'", amount: "+142,000.00", type: "in" },
    { id: 2, name: "Оплата аренды (БЦ)", amount: "-65,000.00", type: "out" },
    { id: 3, name: "Яндекс.Директ", amount: "-12,400.00", type: "out" },
    { id: 4, name: "Выплата заработной платы", amount: "-180,000.00", type: "out" },
    { id: 5, name: "Пополнение счета (Эквайринг)", amount: "+42,300.00", type: "in" },
    { id: 6, name: "Налоги (НДФЛ)", amount: "-32,100.00", type: "out" },
    { id: 7, name: "Лизинг оборудования", amount: "-85,000.00", type: "out" },
    { id: 8, name: "Возврат от поставщика", amount: "+12,500.00", type: "in" },
    { id: 9, name: "Услуги связи", amount: "-3,200.00", type: "out" },
    { id: 10, name: "Продажа ПО", amount: "+450,000.00", type: "in" },
  ];

  const handleVikkiAction = () => {
    setIsProcessing(true);
    setTimeout(() => setIsProcessing(false), 2000);
  };

  useEffect(() => {
    const timer = setInterval(() => setUptime(new Date().toLocaleTimeString('ru-RU')), 1000);
    return () => clearInterval(timer);
  }, []);

  const formatCurrency = (val) => new Intl.NumberFormat('ru-RU', { 
    style: 'currency', 
    currency: 'RUB', 
    maximumFractionDigits: 0 
  }).format(val);

  return (
    <Layout>
      {/* ФОНОВЫЙ СЛОЙ */}
      <div className="fixed inset-0 z-0 pointer-events-none">
        <Scene />
      </div>
      
      {/* ВЕРХНЯЯ ПАНЕЛЬ */}
      <div className="fixed top-0 left-0 right-0 h-12 border-b border-white/10 bg-black/60 backdrop-blur-3xl z-[100] flex items-center justify-between px-10 text-[10px] uppercase tracking-widest font-mono">
        <div className="flex gap-6 items-center ml-16">
          <span className="flex items-center gap-2 text-white/70">
            <motion.div 
              animate={isProcessing ? { opacity: [0.5, 1, 0.5], scale: [1, 1.3, 1] } : {}}
              transition={{ repeat: Infinity, duration: 1.5 }}
              className="w-1.5 h-1.5 rounded-full bg-vikki-accent shadow-[0_0_10px_#00d2ff]" 
            />
            СТАТУС: <span className="font-bold text-vikki-accent uppercase">{isProcessing ? 'АНАЛИЗ...' : 'АКТИВЕН'}</span>
          </span>
        </div>
        <div className="flex items-center gap-8 text-white/60">
          <button onClick={() => setIsPrivacy(!isPrivacy)} className="hover:text-vikki-accent transition-all flex items-center gap-2 cursor-pointer">
            {isPrivacy ? <EyeOff size={15} /> : <Eye size={15} />}
            <span>ПРИВАТНОСТЬ</span>
          </button>
          <span className="text-white/40 font-bold tracking-[0.2em]">{uptime}</span>
        </div>
      </div>

      <main className="relative z-10 w-full min-h-screen pl-24 pt-28 pr-12 pb-20 flex flex-col items-center">
        <div className="w-full max-w-[1550px]">
          
          {/* HEADER SECTION */}
          <header className="flex items-end justify-between mb-16 px-4 relative z-[60]">
            <div>
              <motion.h1 
                initial={{ opacity: 0, x: -20 }} 
                animate={{ opacity: 1, x: 0 }}
                className="text-8xl font-extralight tracking-tighter text-white leading-none"
              >
                Виктор<span className="text-vikki-accent drop-shadow-[0_0_20px_rgba(0,210,255,0.6)]">.</span>
              </motion.h1>
              <p className="text-white/40 mt-4 text-[11px] uppercase tracking-[0.7em] font-semibold">ИНТЕЛЛЕКТУАЛЬНАЯ ПАНЕЛЬ УПРАВЛЕНИЯ</p>
            </div>
            <div className="text-right">
              <div className="text-7xl font-light tracking-tighter text-white drop-shadow-2xl">
                <Counter value={248500.00} isPrivacy={isPrivacy} />
                <span className="text-base text-white/40 ml-3 uppercase font-mono tracking-widest">₽</span>
              </div>
              <div className="flex items-center justify-end gap-2 mt-3">
                <TrendingUp size={14} className="text-vikki-up" />
                <div className="text-[11px] text-vikki-up font-black tracking-widest bg-vikki-up/10 py-1.5 px-3 rounded-lg border border-vikki-up/20 shadow-lg uppercase">
                  +2.4% сегодня
                </div>
              </div>
            </div>
          </header>

          {/* VIKKI INPUT SECTION */}
          <div className="max-w-5xl mx-auto mb-20 px-4 relative z-[70]">
            <div className={`bg-white/[0.05] backdrop-blur-[40px] rounded-3xl border border-white/10 transition-all duration-500 shadow-[0_0_50px_rgba(0,0,0,0.3)] ${isProcessing ? 'border-amber-500/50 ring-1 ring-amber-500/20' : ''}`}>
              <div className="relative flex items-center">
                <div className="pl-6">
                  <motion.div
                    animate={isProcessing ? { opacity: [0.5, 1, 0.5], scale: [1, 1.2, 1] } : {}}
                    transition={{ repeat: Infinity, duration: 2 }}
                    className="p-2 rounded-xl bg-vikki-accent/10 border border-vikki-accent/30"
                  >
                    <Sparkles size={22} className={isProcessing ? "text-amber-400" : "text-vikki-accent"} />
                  </motion.div>
                </div>
                <div className="flex-1">
                  <VikkiInput onSendMessage={handleVikkiAction} onFocusChange={(f) => setIsInputFocused(f)} />
                </div>
              </div>
            </div>
          </div>

          {/* ГРИД СИСТЕМА */}
          <div className={`grid grid-cols-12 gap-10 transition-all duration-700 ${isInputFocused ? 'blur-xl opacity-30 scale-[0.98]' : ''}`}>
            
            {/* ЛЕВАЯ КОЛОНКА */}
            <div className="col-span-3 flex flex-col gap-10">
              {/* СБИС (ВЫСОТА / 2) */}
              <div className="bg-white/[0.03] backdrop-blur-2xl rounded-[40px] p-8 h-[340px] border border-white/5 flex flex-col shadow-2xl relative overflow-hidden">
                <div className="flex items-center gap-3 opacity-60 mb-6 text-[10px] uppercase tracking-[0.2em] font-black text-white">
                  <Receipt size={18} className="text-vikki-accent" /> ДОКУМЕНТЫ (СБИС)
                </div>
                <div className="flex-1 overflow-y-auto custom-scrollbar">
                  <EdoWidget hideHeader={true} />
                </div>
              </div>
              {/* НОВЫЙ БЛОК СЛЕВА */}
              <div className="bg-white/[0.03] backdrop-blur-2xl rounded-[40px] p-8 h-[340px] border border-white/5 flex flex-col shadow-2xl relative overflow-hidden">
                 <div className="flex items-center gap-3 opacity-60 mb-6 text-[10px] uppercase tracking-[0.2em] font-black text-white">
                    <Box size={18} className="text-vikki-accent" /> ДОПОЛНИТЕЛЬНЫЙ МОДУЛЬ
                 </div>
                 <div className="flex-1 flex items-center justify-center border border-dashed border-white/10 rounded-3xl">
                    <span className="text-[10px] text-white/20 uppercase font-bold tracking-[0.3em]">Ожидание данных...</span>
                 </div>
              </div>
            </div>

            {/* ЦЕНТРАЛЬНАЯ КОЛОНКА */}
            <div className="col-span-6 flex flex-col gap-10">
              {/* ГРАФИК */}
              <div className="bg-white/[0.03] backdrop-blur-2xl rounded-[40px] p-10 h-[420px] border border-white/5 flex flex-col shadow-2xl relative overflow-visible">
                <div className="flex justify-between items-center mb-8 text-[10px] opacity-60 uppercase tracking-[0.3em] font-black text-white relative z-20">
                  <span>АНАЛИЗ ДЕНЕЖНЫХ ПОТОКОВ</span>
                  <div className="flex gap-6">
                     <span className="flex items-center gap-2 font-mono"><div className="w-2 h-2 bg-vikki-accent rounded-full shadow-[0_0_10px_#00d2ff]" /> ПРИХОД</span>
                     <span className="flex items-center gap-2 font-mono"><div className="w-2 h-2 bg-red-500 rounded-full shadow-[0_0_10px_#ef4444]" /> РАСХОД</span>
                  </div>
                </div>
                
                <div className="flex-1 flex items-end justify-between gap-6 px-4 relative z-10">
                  {financialData.map((d, i) => (
                    <div key={i} className="flex-1 flex flex-col items-center h-full justify-end group/item">
                      <div className="flex items-end gap-2 w-full h-[220px] justify-center relative">
                        <div className="relative flex flex-col items-center h-full justify-end">
                          <motion.span className="text-[10px] font-mono font-bold text-vikki-accent mb-2 group-hover/item:scale-125 transition-transform">
                            {Math.round(d.in/1000)}k
                          </motion.span>
                          <motion.div 
                            initial={{ height: 0 }} 
                            animate={{ height: `${(d.in / maxVal) * 100}%` }}
                            onHoverStart={() => setHoveredBar({ day: d.day, type: 'Приход', value: d.in })}
                            onHoverEnd={() => setHoveredBar(null)}
                            className={`w-7 rounded-t-xl transition-all duration-500 cursor-pointer hover:brightness-150 
                              ${d.forecast ? 'border border-dashed border-vikki-accent/40 bg-vikki-accent/5' : 'bg-gradient-to-t from-vikki-accent/20 to-vikki-accent'}`}
                          />
                        </div>
                        <div className="relative flex flex-col items-center h-full justify-end">
                          <motion.span className="text-[10px] font-mono font-bold text-red-500 mb-2 group-hover/item:scale-125 transition-transform">
                            {Math.round(d.out/1000)}k
                          </motion.span>
                          <motion.div 
                            initial={{ height: 0 }} 
                            animate={{ height: `${(d.out / maxVal) * 100}%` }}
                            onHoverStart={() => setHoveredBar({ day: d.day, type: 'Расход', value: d.out })}
                            onHoverEnd={() => setHoveredBar(null)}
                            className={`w-7 rounded-t-xl transition-all duration-500 cursor-pointer hover:brightness-150 
                              ${d.forecast ? 'border border-dashed border-red-500/40 bg-red-500/5' : 'bg-gradient-to-t from-red-500/20 to-red-500'}`}
                          />
                        </div>
                      </div>
                      <span className="text-[10px] opacity-40 mt-6 font-black tracking-widest text-white">{d.day}</span>
                    </div>
                  ))}

                  <AnimatePresence>
                    {hoveredBar && (
                      <motion.div 
                        initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 10 }}
                        className="absolute -top-10 left-1/2 -translate-x-1/2 bg-black/90 backdrop-blur-3xl border border-white/10 p-5 rounded-2xl z-[100] shadow-2xl min-w-[180px]"
                      >
                        <div className="text-[9px] text-white/30 uppercase font-black mb-1 tracking-widest">{hoveredBar.day} • {hoveredBar.type}</div>
                        <div className={`text-xl font-mono font-bold ${hoveredBar.type === 'Приход' ? 'text-vikki-accent' : 'text-red-500'}`}>
                          {formatCurrency(hoveredBar.value)}
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              </div>

              {/* БАНК (ВЫСОТА X 3) */}
              <div className="bg-white/[0.03] backdrop-blur-2xl rounded-[40px] p-8 h-[810px] border border-white/5 flex flex-col shadow-2xl">
                <div className="flex justify-between items-center mb-6 text-[10px] opacity-60 uppercase tracking-[0.2em] font-black text-white">
                  <span>ЖУРНАЛ БАНКОВСКИХ ОПЕРАЦИЙ</span>
                  <Activity size={18} className="text-vikki-accent" />
                </div>
                <div className="space-y-3 overflow-y-auto flex-1 custom-scrollbar pr-2">
                  {transactions.map(t => (
                    <div key={t.id} className="flex items-center justify-between p-5 bg-white/[0.04] border border-white/5 rounded-3xl hover:bg-white/[0.08] transition-all">
                      <div className="text-[14px] font-semibold text-white/80">{t.name}</div>
                      <div className={`text-base font-mono font-black ${isPrivacy ? 'blur-md' : ''} ${t.type === 'in' ? 'text-vikki-up' : 'text-white/60'}`}>
                        {t.amount}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* ПРАВАЯ КОЛОНКА */}
            <div className="col-span-3 flex flex-col gap-10">
              {/* СОБЫТИЯ (ВЫСОТА / 2) */}
              <div className="bg-white/[0.03] backdrop-blur-2xl rounded-[40px] p-8 h-[340px] border border-white/5 flex flex-col shadow-2xl relative overflow-hidden">
                <div className="flex items-center gap-3 opacity-60 mb-6 text-[10px] uppercase tracking-[0.2em] font-black text-white">
                  <Clock size={18} className="text-vikki-accent" /> ЖУРНАЛ СОБЫТИЙ
                </div>
                <div className="space-y-4">
                  <div className="p-5 bg-white/[0.05] rounded-3xl border border-white/5 border-l-4 border-l-vikki-accent">
                     <p className="text-[12px] text-white/60 leading-relaxed font-semibold">
                      Синхронизация завершена. Подозрительных операций не выявлено.
                     </p>
                  </div>
                </div>
              </div>
              {/* НОВЫЙ БЛОК СПРАВА */}
              <div className="bg-white/[0.03] backdrop-blur-2xl rounded-[40px] p-8 h-[340px] border border-white/5 flex flex-col shadow-2xl relative overflow-hidden">
                 <div className="flex items-center gap-3 opacity-60 mb-6 text-[10px] uppercase tracking-[0.2em] font-black text-white">
                    <Box size={18} className="text-vikki-accent" /> БОКОВОЙ ВИДЖЕТ
                 </div>
                 <div className="flex-1 flex items-center justify-center border border-dashed border-white/10 rounded-3xl">
                    <span className="text-[10px] text-white/20 uppercase font-bold tracking-[0.3em]">Ожидание данных...</span>
                 </div>
              </div>
            </div>

          </div>
        </div>
      </main>
    </Layout>
  );
}

export default App;
