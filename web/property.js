// UI-only metadata. This is not the backend project/tour contract.
export const fields = {
  name: ['Property name', 'Tên căn hộ'], address: ['Address', 'Địa chỉ'], direction: ['Facing direction', 'Hướng căn hộ'],
  windows: ['Windows', 'Cửa sổ'], rooms: ['Total rooms', 'Tổng số phòng'], bedrooms: ['Bedrooms', 'Phòng ngủ'],
  bathrooms: ['Bathrooms', 'Phòng tắm'], area: ['Area (m²)', 'Diện tích (m²)'], notes: ['Other details', 'Ghi chú khác']
};
export const directions = {N:['North','Bắc'], NE:['Northeast','Đông Bắc'], E:['East','Đông'], SE:['Southeast','Đông Nam'], S:['South','Nam'], SW:['Southwest','Tây Nam'], W:['West','Tây'], NW:['Northwest','Tây Bắc']};
export const normalize = text => text.normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/đ/g, 'd').replace(/Đ/g, 'D').toLowerCase();
export function extract(text) {
  const n = normalize(text); const result = {};
  // Questions and uncertain statements are not treated as facts.
  if (/[?？]/.test(text) || /\b(maybe|perhaps|not sure|chua ro|khong chac|co the|how many|does it|is it|bao nhieu)\b/.test(n) || /\b(?:not|khong phai)\s+(?:\d|facing|huong|north|south|east|west)/.test(n)) return result;
  const patterns = { bedrooms: /(\d+)\s*(?:bedrooms?\b|phong ngu\b)/g, bathrooms: /(\d+)\s*(?:bathrooms?\b|phong tam\b|phong ve sinh\b)/g, rooms: /(\d+)\s*(?:rooms?\b|phong\b(?!\s+(?:ngu|tam|ve sinh)))/g, area: /(\d+(?:[.,]\d+)?)\s*(?:m²|m2\b|sqm\b|square meters?\b|met vuong\b)/g };
  for (const [field, regex] of Object.entries(patterns)) {
    const matches = [...n.matchAll(regex)];
    if (matches.length === 1) { const value = Number(matches[0][1].replace(',', '.')); if (value >= (field === 'rooms' || field === 'area' ? 1 : 0) && value <= (field === 'area' ? 100000 : 100)) result[field] = String(value); }
  }
  const facing = n.match(/(?:huong|facing|faces)\s*[:=-]?\s*(dong bac|dong nam|tay bac|tay nam|bac|nam|dong|tay|north\s*east|south\s*east|north\s*west|south\s*west|north|south|east|west)\b/) || n.match(/\b(northeast|southeast|northwest|southwest|north|south|east|west)[ -]facing\b/);
  const directionMap = {dongbac:'NE',dongnam:'SE',taybac:'NW',taynam:'SW',bac:'N',nam:'S',dong:'E',tay:'W',northeast:'NE',southeast:'SE',northwest:'NW',southwest:'SW',north:'N',south:'S',east:'E',west:'W'};
  if (facing) result.direction = directionMap[facing[1].replace(/\s/g,'')];
  if (/\b(?:khong co cua so|no windows?|without windows?)\b/.test(n)) result.windows = 'no';
  else if (/\b(?:co cua so|has windows?|with windows?)\b/.test(n)) result.windows = 'yes';
  // Address requires an explicit label and ends at a semicolon or newline.
  const address = text.match(/(?:address|địa chỉ)\s*:\s*([^;\n]+)/i);
  if (address) result.address = address[1].trim().slice(0,300);
  return result;
}
export function display(field, value, lang = 'en') {
  const i = lang === 'vi' ? 1 : 0;
  if (field === 'direction') return directions[value]?.[i] || value;
  if (field === 'windows') return value === 'yes' ? ['Yes','Có'][i] : ['No','Không'][i];
  return value;
}
export function describe(data, lang = 'en') {
  const vi = lang === 'vi'; const lines = [];
  for (const [key, labels] of Object.entries(fields)) if (data[key] !== undefined && data[key] !== '') lines.push(`${labels[vi ? 1 : 0]}: ${display(key,data[key],lang)}${key === 'area' ? ' m²' : ''}.`);
  return lines.join(' ');
}
export function validate(data) {
  for (const key of ['rooms','bedrooms','bathrooms','area']) {
    if (data[key] === '' || data[key] === undefined) continue;
    const value = Number(data[key]);
    if (!Number.isFinite(value) || value < (key === 'rooms' || key === 'area' ? 1 : 0) || value > (key === 'area' ? 100000 : 100) || (key !== 'area' && !Number.isInteger(value))) return false;
  }
  if (data.rooms && ['bedrooms','bathrooms'].some(k => data[k] && Number(data[k]) > Number(data.rooms))) return false;
  if (data.rooms && data.bedrooms && data.bathrooms && Number(data.bedrooms) + Number(data.bathrooms) > Number(data.rooms)) return false;
  return true;
}
