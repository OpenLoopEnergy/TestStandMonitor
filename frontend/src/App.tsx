import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import PastTests from './pages/PastTests'
import Debug from './pages/Debug'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/past-tests" element={<PastTests />} />
        <Route path="/debug" element={<Debug />} />
      </Routes>
    </BrowserRouter>
  )
}
