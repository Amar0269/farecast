import { MapContainer, Marker, Popup, TileLayer, Polyline } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

const AIRPORT_COORDINATES = {
  DEL: { name: 'Delhi', coordinates: [28.5562, 77.1] },
  BOM: { name: 'Mumbai', coordinates: [19.0896, 72.8656] },
  BLR: { name: 'Bengaluru', coordinates: [13.1986, 77.7066] },
  HYD: { name: 'Hyderabad', coordinates: [17.2403, 78.4294] },
  MAA: { name: 'Chennai', coordinates: [12.9941, 80.1709] },
};

const markerIcon = L.icon({
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

export default function RouteMap({ routes = [] }) {
  const validRoutes = (routes || []).filter((route) => {
    const originCode = route?.originCode || route?.origin?.code;
    const destinationCode = route?.destinationCode || route?.destination?.code;

    if (!originCode || !destinationCode) return false;

    const origin = AIRPORT_COORDINATES[originCode];
    const destination = AIRPORT_COORDINATES[destinationCode];

    return Boolean(origin && destination);
  });

  const allAirportCodes = new Set();
  validRoutes.forEach((route) => {
    const originCode = route?.originCode || route?.origin?.code;
    const destinationCode = route?.destinationCode || route?.destination?.code;
    allAirportCodes.add(originCode);
    allAirportCodes.add(destinationCode);
  });

  return (
    <div className="panel panel-map">
      <div className="panel-header-row">
        <h3>Supported route map</h3>
      </div>
      <div className="map-wrap">
        <MapContainer center={[22.5, 78.96]} zoom={5} scrollWheelZoom={false} className="leaflet-map">
          <TileLayer
            attribution='&copy; OpenStreetMap contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />

          {[...allAirportCodes].map((code) => {
            const airport = AIRPORT_COORDINATES[code];
            if (!airport) return null;

            return (
              <Marker key={code} position={airport.coordinates} icon={markerIcon}>
                <Popup>
                  {airport.name} ({code})
                </Popup>
              </Marker>
            );
          })}

          {validRoutes.map((route, index) => {
            const originCode = route?.originCode || route?.origin?.code;
            const destinationCode = route?.destinationCode || route?.destination?.code;
            const origin = AIRPORT_COORDINATES[originCode];
            const destination = AIRPORT_COORDINATES[destinationCode];

            if (!origin || !destination) {
              return null;
            }

            return (
              <Polyline
                key={`${originCode}-${destinationCode}-${index}`}
                positions={[origin.coordinates, destination.coordinates]}
                pathOptions={{ color: '#1f5f8f', weight: 3, opacity: 0.8 }}
              />
            );
          })}
        </MapContainer>
      </div>
    </div>
  );
}
