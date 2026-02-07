import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Navbar from './components/Navbar';
import ProfessionalsList from './pages/ProfessionalsList';
import AddProfessional from './pages/AddProfessional';

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50">
        <Navbar />
        <main className="max-w-5xl mx-auto px-6 py-8">
          <Routes>
            <Route path="/" element={<Navigate to="/professionals" replace />} />
            <Route path="/professionals" element={<ProfessionalsList />} />
            <Route path="/professionals/new" element={<AddProfessional />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
