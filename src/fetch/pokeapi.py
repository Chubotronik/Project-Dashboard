import requests
import json

from pathlib import Path
from src.config import DATA_RAW_DIR

BASE_URL = "https://pokeapi.co/api/v2"

def get_pokemon(species: str | int) -> dict:
    """
    Fetch a single Pokémon's full data payload from PokéAPI.

    Args:
        species (str | int): Pokémon name (e.g. "garchomp") or National Dex number.

    Returns:
        dict: Raw JSON response from /pokemon/{species}.
    """

    if isinstance(species, int):
        species = str(species)

    species = species.lower()

    response = requests.get(f'{BASE_URL}/pokemon/{species}')
    response.raise_for_status()
    return response.json()


def fetch_http(limit: int, offset: int = 0, timeout: int = 10) -> dict:
    """
    Hit the PokéAPI paginated list endpoint and return the raw JSON.

    Args:
        limit (int): Number of Pokémon to return per page.
        offset (int): Starting index in the National Dex order.

    Returns:
        dict: Raw JSON with keys: count, next, previous, results (list of {name, url}).
    """
    response = requests.get(f'{BASE_URL}/pokemon?limit={limit}&offset={offset}', timeout=timeout)
    response.raise_for_status()

    return response.json()

def list_all_pkmn() -> list:
    """
    Fetch the full Pokémon list from PokéAPI in two requests.

    Returns:
        list: [{name: str, url: str}, ...] for every Pokémon in PokéAPI.
    """
    count = fetch_http(1)['count']
    all_pkmn = fetch_http(count, timeout=30)['results']
    return all_pkmn

def save_pokemon_index(path: Path = DATA_RAW_DIR / "pokemon_index.json") -> Path:
    """
    Save the full Pokémon list to disk as JSON.

    Args:
        path (Path): Destination file. Defaults to data/raw/pokemon_index.json.

    Returns:
        Path: The file that was written, so callers can chain into the next step.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    pokemon = list_all_pkmn()
    path.write_text(json.dumps(pokemon, indent=2), encoding="utf-8")
    return path


def fetch_N(limit: int, offset: int = 0, timeout: int = 10) -> dict:
    """
    Fetch full data for N Pokémon starting at offset, batching individual requests.

    Args:
        limit (int): How many Pokémon to fetch.
        offset (int): Starting index in National Dex order.

    Returns:
        dict: {"name": [str, ...], "data": [dict, ...]} parallel lists.
    """
    results = fetch_http(limit, offset, timeout)['results']
    payload = {'name': [], 'data': []}

    for i in range(limit):
        payload['name'].append(results[i]['name'])
        pkmn = requests.get(results[i]['url'])
        pkmn.raise_for_status()
        payload['data'].append(pkmn.json())

    print(f'Fetched {limit} pokemons successfully')
    print(f'Pokemons fetched: \n{payload["name"]}')
    return payload




if __name__ == "__main__":
    path = save_pokemon_index()
    print("Saved to:", path)