import requests
import yaml
import json


BASE_URL = 'https://api.jawg.io/elevations/locations'
CONFIG_FILE = 'config.yaml'

def get_api_token():
    with open(CONFIG_FILE, 'r') as f:
        config = yaml.safe_load(f)
    
    return config['JAWG_API_TOKEN']


def get_elevation_from_coordinates(coordinates: list[tuple]) -> dict:
    token = get_api_token()
    params = {"access-token": token}
    headers = {"Content-Type": "application/json"}
    locations = '|'.join([f"{coordinate[0]},{coordinate[1]}" for coordinate in coordinates])
    data = {"locations": locations}
    r = requests.post(BASE_URL, params=params, headers=headers, data=json.dumps(data))
    r.raise_for_status()
    return r.json() 