import { BrowserRouter, Route, Routes } from 'react-router-dom';
import './App.css';
import Navbar from './components/Navbar';
import Dashboard from './pages/Dashboard';
import LiveData from './pages/LiveData';
import Methodology from './pages/Methodology';
import RouteDetail from './pages/RouteDetail';
import RoutesPage from './pages/Routes';

function App() {
  return (
    <BrowserRouter>
      <div className="app-shell">
        <Navbar />
        <main className="content-shell">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/routes" element={<RoutesPage />} />
            <Route path="/routes/:id" element={<RouteDetail />} />
            <Route path="/live" element={<LiveData />} />
            <Route path="/methodology" element={<Methodology />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
