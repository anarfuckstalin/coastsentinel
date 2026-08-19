"""Réseau de stations de référence — positions portuaires.

Ces positions sont **indicatives** (précision de l'ordre du kilomètre) :
elles servent au repérage sur la carte et à amorcer une analyse, jamais au
calcul. Pour des positions officielles, importer la liste de l'IOC-UNESCO
(Sea Level Station Monitoring Facility), du réseau GLOSS ou du réseau
national concerné.
"""

from __future__ import annotations

from typing import Any, Final

STATIONS: Final[list[dict[str, Any]]] = [
    {
        "nom": "Tanger", "pays": "MA",
        "lat": 35.79, "lon": -5.81,
        "region": "Maroc", "src": "réseau intégré",
    },
    {
        "nom": "Al Hoceima", "pays": "MA",
        "lat": 35.25, "lon": -3.93,
        "region": "Maroc", "src": "réseau intégré",
    },
    {
        "nom": "Nador — Beni Ensar", "pays": "MA",
        "lat": 35.27, "lon": -2.93,
        "region": "Maroc", "src": "réseau intégré",
    },
    {
        "nom": "Kenitra — Mehdia", "pays": "MA",
        "lat": 34.26, "lon": -6.68,
        "region": "Maroc", "src": "réseau intégré",
    },
    {
        "nom": "Mohammedia", "pays": "MA",
        "lat": 33.72, "lon": -7.40,
        "region": "Maroc", "src": "réseau intégré",
    },
    {
        "nom": "Casablanca", "pays": "MA",
        "lat": 33.60, "lon": -7.62,
        "region": "Maroc", "src": "réseau intégré",
    },
    {
        "nom": "Jorf Lasfar", "pays": "MA",
        "lat": 33.13, "lon": -8.63,
        "region": "Maroc", "src": "réseau intégré",
    },
    {
        "nom": "Safi", "pays": "MA",
        "lat": 32.30, "lon": -9.24,
        "region": "Maroc", "src": "réseau intégré",
    },
    {
        "nom": "Essaouira", "pays": "MA",
        "lat": 31.51, "lon": -9.77,
        "region": "Maroc", "src": "réseau intégré",
    },
    {
        "nom": "Agadir", "pays": "MA",
        "lat": 30.42, "lon": -9.62,
        "region": "Maroc", "src": "réseau intégré",
    },
    {
        "nom": "Tan-Tan — El Ouatia", "pays": "MA",
        "lat": 28.50, "lon": -11.34,
        "region": "Maroc", "src": "réseau intégré",
    },
    {
        "nom": "Laayoune — Tarfaya", "pays": "MA",
        "lat": 27.94, "lon": -12.93,
        "region": "Maroc", "src": "réseau intégré",
    },
    {
        "nom": "Dakhla", "pays": "MA",
        "lat": 23.71, "lon": -15.94,
        "region": "Maroc", "src": "réseau intégré",
    },
    {
        "nom": "Nouadhibou", "pays": "MR",
        "lat": 20.90, "lon": -17.05,
        "region": "Afrique atlantique", "src": "réseau intégré",
    },
    {
        "nom": "Nouakchott", "pays": "MR",
        "lat": 18.03, "lon": -16.03,
        "region": "Afrique atlantique", "src": "réseau intégré",
    },
    {
        "nom": "Dakar", "pays": "SN",
        "lat": 14.67, "lon": -17.43,
        "region": "Afrique atlantique", "src": "réseau intégré",
    },
    {
        "nom": "Banjul", "pays": "GM",
        "lat": 13.45, "lon": -16.58,
        "region": "Afrique atlantique", "src": "réseau intégré",
    },
    {
        "nom": "Conakry", "pays": "GN",
        "lat": 9.51, "lon": -13.71,
        "region": "Afrique atlantique", "src": "réseau intégré",
    },
    {
        "nom": "Abidjan", "pays": "CI",
        "lat": 5.25, "lon": -4.00,
        "region": "Afrique atlantique", "src": "réseau intégré",
    },
    {
        "nom": "Takoradi", "pays": "GH",
        "lat": 4.88, "lon": -1.75,
        "region": "Afrique atlantique", "src": "réseau intégré",
    },
    {
        "nom": "Tema", "pays": "GH",
        "lat": 5.63, "lon": 0.00,
        "region": "Afrique atlantique", "src": "réseau intégré",
    },
    {
        "nom": "Lomé", "pays": "TG",
        "lat": 6.12, "lon": 1.28,
        "region": "Afrique atlantique", "src": "réseau intégré",
    },
    {
        "nom": "Cotonou", "pays": "BJ",
        "lat": 6.35, "lon": 2.43,
        "region": "Afrique atlantique", "src": "réseau intégré",
    },
    {
        "nom": "Lagos", "pays": "NG",
        "lat": 6.43, "lon": 3.40,
        "region": "Afrique atlantique", "src": "réseau intégré",
    },
    {
        "nom": "Douala", "pays": "CM",
        "lat": 4.02, "lon": 9.68,
        "region": "Afrique atlantique", "src": "réseau intégré",
    },
    {
        "nom": "Pointe-Noire", "pays": "CG",
        "lat": -4.79, "lon": 11.83,
        "region": "Afrique atlantique", "src": "réseau intégré",
    },
    {
        "nom": "Luanda", "pays": "AO",
        "lat": -8.78, "lon": 13.24,
        "region": "Afrique atlantique", "src": "réseau intégré",
    },
    {
        "nom": "Walvis Bay", "pays": "NA",
        "lat": -22.95, "lon": 14.50,
        "region": "Afrique atlantique", "src": "réseau intégré",
    },
    {
        "nom": "Le Cap", "pays": "ZA",
        "lat": -33.90, "lon": 18.43,
        "region": "Afrique atlantique", "src": "réseau intégré",
    },
    {
        "nom": "Gibraltar", "pays": "GI",
        "lat": 36.14, "lon": -5.35,
        "region": "Méditerranée", "src": "réseau intégré",
    },
    {
        "nom": "Málaga", "pays": "ES",
        "lat": 36.71, "lon": -4.42,
        "region": "Méditerranée", "src": "réseau intégré",
    },
    {
        "nom": "Alger", "pays": "DZ",
        "lat": 36.77, "lon": 3.07,
        "region": "Méditerranée", "src": "réseau intégré",
    },
    {
        "nom": "Tunis — La Goulette", "pays": "TN",
        "lat": 36.82, "lon": 10.30,
        "region": "Méditerranée", "src": "réseau intégré",
    },
    {
        "nom": "Tripoli", "pays": "LY",
        "lat": 32.90, "lon": 13.19,
        "region": "Méditerranée", "src": "réseau intégré",
    },
    {
        "nom": "Barcelone", "pays": "ES",
        "lat": 41.34, "lon": 2.16,
        "region": "Méditerranée", "src": "réseau intégré",
    },
    {
        "nom": "Marseille", "pays": "FR",
        "lat": 43.28, "lon": 5.35,
        "region": "Méditerranée", "src": "réseau intégré",
    },
    {
        "nom": "Gênes", "pays": "IT",
        "lat": 44.40, "lon": 8.92,
        "region": "Méditerranée", "src": "réseau intégré",
    },
    {
        "nom": "Venise", "pays": "IT",
        "lat": 45.42, "lon": 12.34,
        "region": "Méditerranée", "src": "réseau intégré",
    },
    {
        "nom": "Trieste", "pays": "IT",
        "lat": 45.65, "lon": 13.76,
        "region": "Méditerranée", "src": "réseau intégré",
    },
    {
        "nom": "Naples", "pays": "IT",
        "lat": 40.84, "lon": 14.26,
        "region": "Méditerranée", "src": "réseau intégré",
    },
    {
        "nom": "La Valette", "pays": "MT",
        "lat": 35.90, "lon": 14.51,
        "region": "Méditerranée", "src": "réseau intégré",
    },
    {
        "nom": "Thessalonique", "pays": "GR",
        "lat": 40.62, "lon": 22.93,
        "region": "Méditerranée", "src": "réseau intégré",
    },
    {
        "nom": "Antalya", "pays": "TR",
        "lat": 36.83, "lon": 30.60,
        "region": "Méditerranée", "src": "réseau intégré",
    },
    {
        "nom": "Alexandrie", "pays": "EG",
        "lat": 31.20, "lon": 29.87,
        "region": "Méditerranée", "src": "réseau intégré",
    },
    {
        "nom": "Haïfa", "pays": "IL",
        "lat": 32.82, "lon": 35.00,
        "region": "Méditerranée", "src": "réseau intégré",
    },
    {
        "nom": "Lisbonne — Cascais", "pays": "PT",
        "lat": 38.69, "lon": -9.42,
        "region": "Atlantique NE", "src": "réseau intégré",
    },
    {
        "nom": "Vigo", "pays": "ES",
        "lat": 42.24, "lon": -8.73,
        "region": "Atlantique NE", "src": "réseau intégré",
    },
    {
        "nom": "Brest", "pays": "FR",
        "lat": 48.38, "lon": -4.49,
        "region": "Atlantique NE", "src": "réseau intégré",
    },
    {
        "nom": "Newlyn", "pays": "GB",
        "lat": 50.10, "lon": -5.55,
        "region": "Atlantique NE", "src": "réseau intégré",
    },
    {
        "nom": "Cuxhaven", "pays": "DE",
        "lat": 53.87, "lon": 8.72,
        "region": "Atlantique NE", "src": "réseau intégré",
    },
    {
        "nom": "Bergen", "pays": "NO",
        "lat": 60.40, "lon": 5.31,
        "region": "Atlantique NE", "src": "réseau intégré",
    },
    {
        "nom": "Reykjavik", "pays": "IS",
        "lat": 64.15, "lon": -21.94,
        "region": "Atlantique NE", "src": "réseau intégré",
    },
    {
        "nom": "Halifax", "pays": "CA",
        "lat": 44.67, "lon": -63.58,
        "region": "Amériques", "src": "réseau intégré",
    },
    {
        "nom": "Boston", "pays": "US",
        "lat": 42.35, "lon": -71.05,
        "region": "Amériques", "src": "réseau intégré",
    },
    {
        "nom": "New York — The Battery", "pays": "US",
        "lat": 40.70, "lon": -74.01,
        "region": "Amériques", "src": "réseau intégré",
    },
    {
        "nom": "Charleston", "pays": "US",
        "lat": 32.78, "lon": -79.92,
        "region": "Amériques", "src": "réseau intégré",
    },
    {
        "nom": "Key West", "pays": "US",
        "lat": 24.55, "lon": -81.81,
        "region": "Amériques", "src": "réseau intégré",
    },
    {
        "nom": "Galveston", "pays": "US",
        "lat": 29.31, "lon": -94.79,
        "region": "Amériques", "src": "réseau intégré",
    },
    {
        "nom": "San Diego", "pays": "US",
        "lat": 32.71, "lon": -117.17,
        "region": "Amériques", "src": "réseau intégré",
    },
    {
        "nom": "San Francisco", "pays": "US",
        "lat": 37.81, "lon": -122.47,
        "region": "Amériques", "src": "réseau intégré",
    },
    {
        "nom": "Seattle", "pays": "US",
        "lat": 47.60, "lon": -122.34,
        "region": "Amériques", "src": "réseau intégré",
    },
    {
        "nom": "Balboa — Panamá", "pays": "PA",
        "lat": 8.97, "lon": -79.57,
        "region": "Amériques", "src": "réseau intégré",
    },
    {
        "nom": "Carthagène", "pays": "CO",
        "lat": 10.39, "lon": -75.53,
        "region": "Amériques", "src": "réseau intégré",
    },
    {
        "nom": "Recife", "pays": "BR",
        "lat": -8.05, "lon": -34.87,
        "region": "Amériques", "src": "réseau intégré",
    },
    {
        "nom": "Rio de Janeiro", "pays": "BR",
        "lat": -22.90, "lon": -43.17,
        "region": "Amériques", "src": "réseau intégré",
    },
    {
        "nom": "Buenos Aires", "pays": "AR",
        "lat": -34.60, "lon": -58.37,
        "region": "Amériques", "src": "réseau intégré",
    },
    {
        "nom": "Valparaíso", "pays": "CL",
        "lat": -33.03, "lon": -71.63,
        "region": "Amériques", "src": "réseau intégré",
    },
    {
        "nom": "Callao", "pays": "PE",
        "lat": -12.05, "lon": -77.15,
        "region": "Amériques", "src": "réseau intégré",
    },
    {
        "nom": "Maputo", "pays": "MZ",
        "lat": -25.97, "lon": 32.57,
        "region": "Océan Indien", "src": "réseau intégré",
    },
    {
        "nom": "Zanzibar", "pays": "TZ",
        "lat": -6.16, "lon": 39.19,
        "region": "Océan Indien", "src": "réseau intégré",
    },
    {
        "nom": "Port-Louis", "pays": "MU",
        "lat": -20.16, "lon": 57.50,
        "region": "Océan Indien", "src": "réseau intégré",
    },
    {
        "nom": "Malé", "pays": "MV",
        "lat": 4.18, "lon": 73.51,
        "region": "Océan Indien", "src": "réseau intégré",
    },
    {
        "nom": "Colombo", "pays": "LK",
        "lat": 6.94, "lon": 79.84,
        "region": "Océan Indien", "src": "réseau intégré",
    },
    {
        "nom": "Mumbai", "pays": "IN",
        "lat": 18.92, "lon": 72.83,
        "region": "Océan Indien", "src": "réseau intégré",
    },
    {
        "nom": "Chennai", "pays": "IN",
        "lat": 13.10, "lon": 80.29,
        "region": "Océan Indien", "src": "réseau intégré",
    },
    {
        "nom": "Fremantle", "pays": "AU",
        "lat": -32.06, "lon": 115.74,
        "region": "Océan Indien", "src": "réseau intégré",
    },
    {
        "nom": "Singapour", "pays": "SG",
        "lat": 1.26, "lon": 103.82,
        "region": "Pacifique / Asie", "src": "réseau intégré",
    },
    {
        "nom": "Jakarta", "pays": "ID",
        "lat": -6.10, "lon": 106.88,
        "region": "Pacifique / Asie", "src": "réseau intégré",
    },
    {
        "nom": "Manille", "pays": "PH",
        "lat": 14.58, "lon": 120.97,
        "region": "Pacifique / Asie", "src": "réseau intégré",
    },
    {
        "nom": "Hong Kong", "pays": "HK",
        "lat": 22.29, "lon": 114.16,
        "region": "Pacifique / Asie", "src": "réseau intégré",
    },
    {
        "nom": "Keelung", "pays": "TW",
        "lat": 25.15, "lon": 121.75,
        "region": "Pacifique / Asie", "src": "réseau intégré",
    },
    {
        "nom": "Busan", "pays": "KR",
        "lat": 35.10, "lon": 129.04,
        "region": "Pacifique / Asie", "src": "réseau intégré",
    },
    {
        "nom": "Yokohama", "pays": "JP",
        "lat": 35.45, "lon": 139.65,
        "region": "Pacifique / Asie", "src": "réseau intégré",
    },
    {
        "nom": "Vladivostok", "pays": "RU",
        "lat": 43.12, "lon": 131.89,
        "region": "Pacifique / Asie", "src": "réseau intégré",
    },
    {
        "nom": "Honolulu", "pays": "US",
        "lat": 21.31, "lon": -157.87,
        "region": "Pacifique / Asie", "src": "réseau intégré",
    },
    {
        "nom": "Suva", "pays": "FJ",
        "lat": -18.13, "lon": 178.42,
        "region": "Pacifique / Asie", "src": "réseau intégré",
    },
    {
        "nom": "Funafuti", "pays": "TV",
        "lat": -8.52, "lon": 179.20,
        "region": "Pacifique / Asie", "src": "réseau intégré",
    },
    {
        "nom": "Honiara", "pays": "SB",
        "lat": -9.43, "lon": 159.95,
        "region": "Pacifique / Asie", "src": "réseau intégré",
    },
    {
        "nom": "Sydney", "pays": "AU",
        "lat": -33.85, "lon": 151.23,
        "region": "Pacifique / Asie", "src": "réseau intégré",
    },
    {
        "nom": "Auckland", "pays": "NZ",
        "lat": -36.84, "lon": 174.77,
        "region": "Pacifique / Asie", "src": "réseau intégré",
    },
]
