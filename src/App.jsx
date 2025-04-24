import { useState } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import reactLogo from './assets/react.svg'
import viteLogo from '/vite.svg'
import './App.css'
import AuthSystem from './components/AuthSystem.jsx'
import OrderManagement from './components/OrderManagement.jsx'

function App() {
  const [count, setCount] = useState(0)

  return (

        <BrowserRouter>
      <Routes>
        <Route path="/" element={<AuthSystem />} />
        <Route path="/dashboard" element={<OrderManagement />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
