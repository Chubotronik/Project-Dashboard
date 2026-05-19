import requests

BASE_URL = "https://pokeapi.co/api/v2"

def get_pokemon(species: str | int) -> dict:
    """
    Fetch pokemon data from pokeapi url

    Args: species (str | int): the name of the pokemon

    Returns: the json dictionary with the pokemon info
    """

    if isinstance(species, int):
        species = str(species)

    species = species.lower()

    try:
        pokemon = requests.get(f'{BASE_URL}/pokemon/{species}')
        return pokemon.json()

    except Exception as err:
        print(f'An error occurred: {err}')



if __name__ == "__main__":
    data = get_pokemon("garchomp")
    types = [t["type"]["name"] for t in data["types"]]
    stats = {s["stat"]["name"]: s["base_stat"] for s in data["stats"]}
    print(f"{data['name']} — types: {types}")
    print("Base stats:", stats)
    print('All available info', data.keys())