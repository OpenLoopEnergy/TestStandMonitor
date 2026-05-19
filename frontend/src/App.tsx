import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import PastTests from './pages/PastTests'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/past-tests" element={<PastTests />} />
      </Routes>
    </BrowserRouter>
  )
}
