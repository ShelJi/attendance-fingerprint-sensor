export function googleMapsUrl(latitude: number, longitude: number) {
  if (!Number.isFinite(latitude) || !Number.isFinite(longitude) || Math.abs(latitude) > 90 || Math.abs(longitude) > 180) throw new Error('Location unavailable.');
  return `https://www.google.com/maps/search/?api=1&query=${latitude},${longitude}`;
}
