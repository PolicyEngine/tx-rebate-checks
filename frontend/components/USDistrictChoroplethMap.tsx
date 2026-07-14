'use client';

import { useEffect, useMemo, useState } from 'react';

export interface TXDistrictData {
  district: string;
  district_number: string;
  representative: string;
  party?: 'R' | 'D';
  region: string;
  average_household_income_change: number;
  relative_household_income_change: number;
  winners_share?: number;
  losers_share?: number;
  winners_share_residents?: number;
  losers_share_residents?: number;
  poverty_pct_change?: number;
  child_poverty_pct_change?: number;
  state?: string;
}

interface Props {
  data: TXDistrictData[];
  selectedDistrict: string | null;
  onSelect: (districtNumber: string) => void;
}

const DIVERGING_COLORS = [
  'var(--diverging-gray-teal-1)',
  'var(--diverging-gray-teal-2)',
  'var(--diverging-gray-teal-3)',
  'var(--diverging-gray-teal-4)',
  'var(--diverging-gray-teal-5)',
];

const VB_W = 800;
const VB_H = 700;
const VB_PAD = 16;

const TX_STATE_FIPS = '48';
const GEOJSON_PATH = 'data/geojson/congressional_districts.geojson';

type Ring = [number, number][];
interface GeoFeature {
  type: 'Feature';
  properties: {
    STATEFP: string;
    CD119FP: string;
    DISTRICT_ID: string;
    NAMELSAD?: string;
  };
  geometry:
    | { type: 'Polygon'; coordinates: Ring[] }
    | { type: 'MultiPolygon'; coordinates: Ring[][] };
}
interface GeoCollection {
  type: 'FeatureCollection';
  features: GeoFeature[];
}
interface DistrictGeometry {
  districtNumber: string;
  path: string;
  cx: number;
  cy: number;
}

function interpolateColor(value: number, min: number, max: number): string {
  if (min >= max) return DIVERGING_COLORS[2];
  const t = Math.max(0, Math.min(1, (value - min) / (max - min)));
  const segments = DIVERGING_COLORS.length - 1;
  const segPos = t * segments;
  const segIndex = Math.min(Math.floor(segPos), segments - 1);
  const segT = segPos - segIndex;
  const startWeight = ((1 - segT) * 100).toFixed(4);
  const endWeight = (segT * 100).toFixed(4);
  return `color-mix(in srgb, ${DIVERGING_COLORS[segIndex]} ${startWeight}%, ${DIVERGING_COLORS[segIndex + 1]} ${endWeight}%)`;
}

const formatCurrency = (value: number) => {
  if (Math.abs(value) >= 1000) return `$${(value / 1000).toFixed(1)}k`;
  return `$${value.toFixed(0)}`;
};
const formatSignedCurrency = (value: number) => {
  const base = formatCurrency(Math.abs(value));
  if (value > 0) return `+${base}`;
  if (value < 0) return `-${base}`;
  return base;
};

function iterateRings(geom: GeoFeature['geometry']): Ring[] {
  if (geom.type === 'Polygon') return geom.coordinates;
  return geom.coordinates.flat();
}

function computeBBox(features: GeoFeature[]) {
  let minLon = Infinity;
  let maxLon = -Infinity;
  let minLat = Infinity;
  let maxLat = -Infinity;
  for (const f of features) {
    for (const ring of iterateRings(f.geometry)) {
      for (const [lon, lat] of ring) {
        if (lon < minLon) minLon = lon;
        if (lon > maxLon) maxLon = lon;
        if (lat < minLat) minLat = lat;
        if (lat > maxLat) maxLat = lat;
      }
    }
  }
  return { minLon, maxLon, minLat, maxLat };
}

function makeProjector(bbox: ReturnType<typeof computeBBox>) {
  const meanLat = (bbox.minLat + bbox.maxLat) / 2;
  const lonScale = Math.cos((meanLat * Math.PI) / 180);
  const geoW = (bbox.maxLon - bbox.minLon) * lonScale;
  const geoH = bbox.maxLat - bbox.minLat;
  const availW = VB_W - 2 * VB_PAD;
  const availH = VB_H - 2 * VB_PAD;
  const scale = Math.min(availW / geoW, availH / geoH);
  const drawnW = geoW * scale;
  const drawnH = geoH * scale;
  const offsetX = VB_PAD + (availW - drawnW) / 2;
  const offsetY = VB_PAD + (availH - drawnH) / 2;
  return (lon: number, lat: number): [number, number] => {
    const x = offsetX + (lon - bbox.minLon) * lonScale * scale;
    const y = offsetY + (bbox.maxLat - lat) * scale;
    return [x, y];
  };
}

function ringToPath(ring: Ring, project: (lon: number, lat: number) => [number, number]): string {
  const out: string[] = [];
  for (let i = 0; i < ring.length; i++) {
    const [lon, lat] = ring[i];
    const [x, y] = project(lon, lat);
    out.push(`${i === 0 ? 'M' : 'L'}${x.toFixed(2)},${y.toFixed(2)}`);
  }
  out.push('Z');
  return out.join(' ');
}

function featureToPath(
  feature: GeoFeature,
  project: (lon: number, lat: number) => [number, number],
) {
  const rings = iterateRings(feature.geometry);
  const path = rings.map((r) => ringToPath(r, project)).join(' ');
  let sx = 0;
  let sy = 0;
  let n = 0;
  for (const ring of rings) {
    for (const [lon, lat] of ring) {
      const [x, y] = project(lon, lat);
      sx += x;
      sy += y;
      n += 1;
    }
  }
  return {
    path,
    cx: n > 0 ? sx / n : VB_W / 2,
    cy: n > 0 ? sy / n : VB_H / 2,
  };
}

export default function TXDistrictChoroplethMap({
  data,
  selectedDistrict,
  onSelect,
}: Props) {
  const [geometries, setGeometries] = useState<DistrictGeometry[] | null>(null);
  const [geoError, setGeoError] = useState<string | null>(null);
  const [tooltip, setTooltip] = useState<{
    x: number;
    y: number;
    districtNumber: string;
  } | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const basePath =
          process.env.NEXT_PUBLIC_BASE_PATH !== undefined
            ? process.env.NEXT_PUBLIC_BASE_PATH
            : '/us/tx-rebate-checks';
        const res = await fetch(`${basePath}/${GEOJSON_PATH}`);
        if (!res.ok) throw new Error(`Failed to load geojson (${res.status})`);
        const json = (await res.json()) as GeoCollection;
        const txFeatures = json.features.filter(
          (f) => f.properties.STATEFP === TX_STATE_FIPS,
        );
        if (txFeatures.length === 0) {
          throw new Error('No Texas features in the geojson');
        }
        const bbox = computeBBox(txFeatures);
        const project = makeProjector(bbox);
        const geom: DistrictGeometry[] = txFeatures.map((f) => {
          const districtNumber = String(parseInt(f.properties.CD119FP, 10));
          const { path, cx, cy } = featureToPath(f, project);
          return { districtNumber, path, cx, cy };
        });
        geom.sort(
          (a, b) => Number(a.districtNumber) - Number(b.districtNumber),
        );
        if (!cancelled) setGeometries(geom);
      } catch (e) {
        if (!cancelled) {
          setGeoError(e instanceof Error ? e.message : String(e));
        }
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  const dataByDistrict = useMemo(() => {
    const map = new Map<string, TXDistrictData>();
    data.forEach((d) =>
      map.set(String(parseInt(d.district_number, 10)), d),
    );
    return map;
  }, [data]);

  const colorRange = useMemo(() => {
    if (data.length === 0) return { min: 0, max: 0 };
    const values = data.map((d) => d.average_household_income_change);
    const maxAbs = Math.max(...values.map(Math.abs));
    return { min: -maxAbs, max: maxAbs };
  }, [data]);

  const tooltipData = tooltip
    ? dataByDistrict.get(tooltip.districtNumber)
    : null;

  return (
    <div className="relative">
      {geoError && (
        <div className="mb-3 rounded-md border border-yellow-200 bg-yellow-50 px-3 py-2 text-sm text-yellow-800">
          Could not load the TX geography ({geoError}).
        </div>
      )}
      <svg
        viewBox={`0 0 ${VB_W} ${VB_H}`}
        style={{ width: '100%', height: 'auto', maxHeight: 600 }}
        role="img"
        aria-label="Choropleth of Texas's 38 congressional districts"
      >
        {geometries &&
          geometries.map((g) => {
            const districtData = dataByDistrict.get(g.districtNumber);
            const value = districtData?.average_household_income_change ?? 0;
            const fill = districtData
              ? interpolateColor(value, colorRange.min, colorRange.max)
              : 'var(--gray-200)';
            const isSelected = selectedDistrict === g.districtNumber;

            return (
              <g
                key={g.districtNumber}
                style={{ cursor: 'pointer' }}
                onClick={() => onSelect(g.districtNumber)}
                onMouseEnter={(evt) =>
                  setTooltip({
                    x: evt.clientX,
                    y: evt.clientY,
                    districtNumber: g.districtNumber,
                  })
                }
                onMouseMove={(evt) =>
                  setTooltip({
                    x: evt.clientX,
                    y: evt.clientY,
                    districtNumber: g.districtNumber,
                  })
                }
                onMouseLeave={() => setTooltip(null)}
              >
                <path
                  d={g.path}
                  fill={fill}
                  stroke={isSelected ? '#0f766e' : 'var(--text-inverse)'}
                  strokeWidth={isSelected ? 2.5 : 1}
                  strokeLinejoin="round"
                  style={{
                    transition: 'opacity 0.15s',
                    opacity:
                      tooltip && tooltip.districtNumber !== g.districtNumber
                        ? 0.7
                        : 1,
                  }}
                />
                <text
                  x={g.cx}
                  y={g.cy}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fontSize="14"
                  fontWeight="700"
                  fill="var(--text-inverse)"
                  stroke="var(--gray-800)"
                  strokeWidth="0.4"
                  paintOrder="stroke"
                  style={{ pointerEvents: 'none', userSelect: 'none' }}
                >
                  {g.districtNumber}
                </text>
              </g>
            );
          })}
      </svg>

      {tooltip && tooltipData && (
        <div
          className="fixed z-50 bg-white border border-gray-200 rounded-lg shadow-lg px-3 py-2 pointer-events-none"
          style={{ left: tooltip.x + 10, top: tooltip.y + 10 }}
        >
          <p className="font-semibold text-gray-900">
            TX-{String(tooltipData.district_number).padStart(2, '0')}
          </p>
          {tooltipData.representative && (
            <p className="text-sm text-gray-700">{tooltipData.representative}</p>
          )}
          <p className="text-sm text-gray-600">
            Avg impact:{' '}
            {formatSignedCurrency(tooltipData.average_household_income_change)}
          </p>
          <p className="text-sm text-gray-600">
            ({(tooltipData.relative_household_income_change * 100).toFixed(2)}%
            of income)
          </p>
        </div>
      )}

      <p className="text-xs text-gray-500 text-center mt-4">
        Average household impact of the proposed $1,500 rebate check vs. current
        law, by Texas congressional district (119th Congress)
      </p>
    </div>
  );
}
