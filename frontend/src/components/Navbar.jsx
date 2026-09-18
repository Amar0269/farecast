import { NavLink } from 'react-router-dom';

const navItems = [
  { label: 'Dashboard', to: '/' },
  { label: 'Routes', to: '/routes' },
  { label: 'Live Data', to: '/live' },
  { label: 'Methodology', to: '/methodology' },
];

export default function Navbar() {
  return (
    <aside className="sidebar">
      <div className="brand-block">
        <div className="brand-mark">F</div>
        <div>
          <div className="brand-name">FareCast</div>
          <div className="brand-subtitle">Airfare index</div>
        </div>
      </div>

      <nav className="nav-links" aria-label="Primary navigation">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/'}
            className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
          >
            {item.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
