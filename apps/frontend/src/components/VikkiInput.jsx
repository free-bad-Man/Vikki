import React, { useState, useEffect } from 'react';
import { Search, Send } from 'lucide-react';

const placeholders = [
  "Виктор, сколько НДС нам платить в этом месяце?",
  "Проверь, пришла ли оплата от ООО 'Вектор'",
  "Какой остаток на крипто-кошельке?",
  "Сделай прогноз кассового разрыва на неделю"
];

export default function VikkiInput({ onSendMessage, onFocusChange }) {
  const [index, setIndex] = useState(0);
  const [inputValue, setInputValue] = useState("");
  const [isFocused, setIsFocused] = useState(false);

  // Ротация плейсхолдеров
  useEffect(() => {
    const interval = setInterval(() => {
      if (!isFocused && inputValue === "") {
        setIndex((prev) => (prev + 1) % placeholders.length);
      }
    }, 4000);
    return () => clearInterval(interval);
  }, [isFocused, inputValue]);

  // Функция отправки (вызывается и по кнопке, и по Enter)
  const submitAction = (e) => {
    if (e) e.preventDefault(); // Останавливаем перезагрузку страницы
    if (inputValue.trim()) {
      onSendMessage(inputValue); // Вызываем функцию из App.jsx
      setInputValue(""); // Очищаем поле
    }
  };

  return (
    <form 
      onSubmit={submitAction}
      className="relative group flex items-center px-6 py-4 bg-black/40 border-t border-white/5"
    >
      <Search 
        className={`transition-colors duration-500 ${isFocused ? 'text-vikki-accent' : 'text-white/20'}`} 
        size={20} 
      />
      
      <input 
        type="text"
        value={inputValue}
        onChange={(e) => setInputValue(e.target.value)}
        onFocus={() => {
          setIsFocused(true);
          if (onFocusChange) onFocusChange(true);
        }}
        onBlur={() => {
          setIsFocused(false);
          if (onFocusChange) onFocusChange(false);
        }}
        placeholder={placeholders[index]}
        className="flex-1 bg-transparent border-none outline-none px-4 text-sm text-white placeholder:text-white/20"
      />

      {/* Анимация волны */}
      <div className={`flex items-center gap-1 h-4 px-4 transition-opacity ${isFocused || inputValue ? 'opacity-100' : 'opacity-0'}`}>
        {[0.4, 0.8, 1.2, 0.6, 1.0].map((delay, i) => (
          <div 
            key={i} 
            className="w-0.5 h-full bg-vikki-accent/60 rounded-full animate-pulse"
            style={{ animationDelay: `${delay}s` }}
          />
        ))}
      </div>

      <button 
        type="submit"
        disabled={!inputValue.trim()}
        className={`p-2 rounded-xl transition-all ${
          inputValue.trim() 
            ? 'text-vikki-accent bg-vikki-accent/10 cursor-pointer scale-110 shadow-[0_0_15px_rgba(0,210,255,0.3)]' 
            : 'text-white/10'
        }`}
      >
        <Send size={18} />
      </button>
    </form>
  );
}