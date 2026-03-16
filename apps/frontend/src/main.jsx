import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx' // Импорт из текущей папки src
import './index.css' // Подключение Tailwind стилей

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)