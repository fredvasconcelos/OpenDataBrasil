// O GeoJSON da API segue a RFC 7946 (anel externo anti-horário). O d3-geo trabalha
// na esfera e espera o anel externo no sentido horário: sem inverter, cada polígono
// vira "o globo menos o território". Inverte-se cada anel e, por segurança, confere-se
// a área esférica (nenhum território ocupa mais que um hemisfério).
import { geoArea } from "d3-geo";

import type { GeoCollection, GeoFeature } from "./types";

type Ring = GeoJSON.Position[];

const reverse = (rings: Ring[]): Ring[] => rings.map((ring) => [...ring].reverse());

function polygonForD3(rings: Ring[]): Ring[] {
  const flipped = reverse(rings);
  const area = geoArea({ type: "Polygon", coordinates: flipped });
  return area > 2 * Math.PI ? rings : flipped;
}

export function rewindFeature(f: GeoFeature): GeoFeature {
  const g = f.geometry;
  if (g.type === "Polygon") return { ...f, geometry: { ...g, coordinates: polygonForD3(g.coordinates) } };
  if (g.type === "MultiPolygon") {
    return { ...f, geometry: { ...g, coordinates: g.coordinates.map(polygonForD3) } };
  }
  return f;
}

export function rewindForD3(collection: GeoCollection): GeoCollection {
  return { ...collection, features: collection.features.map(rewindFeature) };
}
