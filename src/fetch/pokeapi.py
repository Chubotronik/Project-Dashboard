import requests

BASE_URL = "https://pokeapi.co/api/v2"

def get_pokemon(species: str | int) -> dict:
    """
    Fetch Pokémon data from the PokeAPI for a given species name.
    
    Args:
        species (str | int): The name or ID of the Pokémon species (e.g., "pikachu" or 25).
    
    Returns:
        dict: A dictionary containing the Pokémon data, or None if not found.
    """
    if isinstance(species, int):
        species = str(species).lower()
    else:
        species = species.lower()
    
    url = f"{BASE_URL}/pokemon/{species}"
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for bad status codes
        return response.json()
    
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
    except Exception as err:
        print(f"An error occurred: {err}")
    return None


if __name__ == "__main__":
    data = get_pokemon("garchomp")
    types = [t["type"]["name"] for t in data["types"]]
    stats = {s["stat"]["name"]: s["base_stat"] for s in data["stats"]}
    print(f"{data['name']} — types: {types}")
    print("Base stats:", stats)
    print('All available info', data.keys())