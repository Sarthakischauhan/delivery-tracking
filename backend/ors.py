import json
from typing import List, Dict, Tuple
from config import ORS_API_KEY
import httpx

Coordinate = Tuple[float, float]  # lat, lon


DRIVER_ROUTES: Dict[str, List[Coordinate]] = {
    "driver-001": (
        [37.445447764268636, -122.16130465474146],  # start
        [37.427077109887456, -122.14351025428107],  # destination
    ),
    "driver-002": [
        [37.445447764268636, -122.16130465474146],  # start
        [37.427077109887456, -122.14351025428107],  # destination
    ],
    "driver-003": [
        [37.445447764268636, -122.16130465474146],  # start
        [37.427077109887456, -122.14351025428107],  # destination
    ],
    "driver-004": [
        [37.445447764268636, -122.16130465474146],  # start
        [37.427077109887456, -122.14351025428107],  # destination
    ],
    "driver-005": [
        [37.445447764268636, -122.16130465474146],  # start
        [37.427077109887456, -122.14351025428107],  # destination
    ],
}


def get_ors_route(start: Coordinate, end: Coordinate, profile: str = "driving-car") -> List[List[float]]:
    """
    Returns ORS route geometry as [lon, lat] pairs.
    Input coordinates are passed as (lat, lon).
    """
    start_lat, start_lon = start
    end_lat, end_lon = end

    url = f"https://api.openrouteservice.org/v2/directions/{profile}/geojson"

    payload = {
        "coordinates": [
            [start_lon, start_lat],
            [end_lon, end_lat],
        ],
        "instructions": False,
    }

    headers = {
        "Authorization": ORS_API_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json, application/geo+json",
    }

    response = httpx.post(url, json=payload, headers=headers, timeout=30)

    if not response:
        print("ORS request failed:")
        print(response.status_code)
        print(response.text)
        response.raise_for_status()

    data = response.json()
    return data["features"][0]["geometry"]["coordinates"]


def downsample(points: List[List[float]], max_points: int = 40) -> List[List[float]]:
    """
    ORS can return many route points. ShadowTraffic does not need every point.
    This keeps the route shape while avoiding a huge JSON config.
    """
    if len(points) <= max_points:
        return points

    step = max(1, len(points) // max_points)
    sampled = points[::step]

    if sampled[-1] != points[-1]:
        sampled.append(points[-1])

    return sampled


def ors_to_shadowtraffic_waypoints(
    ors_points: List[List[float]],
    max_points: int = 40,
) -> List[Dict[str, List[float]]]:
    """
    Converts ORS [lon, lat] into ShadowTraffic-style [lat, lon].
    """
    sampled_points = downsample(ors_points, max_points=max_points)

    waypoints = []

    for lon, lat in sampled_points:
        waypoints.append({
            "coordinates": [lat, lon]
        })

    return waypoints


def build_shadowtraffic_config() -> Dict:
    generators = []

    for driver_id, route_points in DRIVER_ROUTES.items():
        start = route_points[0]
        end = route_points[-1]

        ors_geometry = get_ors_route(start, end, profile="driving-car")
        waypoints = ors_to_shadowtraffic_waypoints(ors_geometry, max_points=50)

        generators.append({
            "topic": "driver-locations",
            "key": driver_id,
            "value": {
                "driverId": driver_id,
                "location": {
                    "_gen": "waypoints",
                    "waypoints": waypoints,
                    "speed": 10,
                    "scale": 0.001,
                    "unit": "degrees",
                    "loop": False
                },
                "timestamp": {
                    "_gen": "now"
                }
            }
        })

    return {
        "generators": generators,
        "globalConfigs": {
            "throughput": 1000
        },
        "connections": {
            "localKafka": {
                "kind": "kafka",
                "producerConfigs": {
                    "bootstrap.servers": "host.docker.internal:29092",
                    "key.serializer": "io.shadowtraffic.kafka.serdes.JsonSerializer",
                    "value.serializer": "io.shadowtraffic.kafka.serdes.JsonSerializer"
                }
            }
        }
    }


if __name__ == "__main__":
    config = build_shadowtraffic_config()

    with open("shadowtraffic-routes.json", "w") as f:
        json.dump(config, f, indent=2)

    print("Wrote shadowtraffic-routes.json")