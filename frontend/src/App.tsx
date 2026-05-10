import { BrowserRouter, Routes, Route } from 'react-router-dom'
import HomePage from './components/HomePage'
import ReaderPage from './components/ReaderPage'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/reader/:id" element={<ReaderPage />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
