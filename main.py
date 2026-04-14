from src.database.blizzard_client import BlizzardClient
from dotenv import load_dotenv
import os


def main():
    load_dotenv()

    BNET_CLIENT_ID = os.getenv("BNET_CLIENT_ID") or ""
    BNET_CLIENT_SECRET = os.getenv("BNET_CLIENT_SECRET") or ""
    BNET_REGION = os.getenv("BNET_REGION") or ""
    BNET_LOCALE = os.getenv("BNET_LOCALE") or ""

    client = BlizzardClient(
        BNET_CLIENT_ID, BNET_CLIENT_SECRET, BNET_REGION, BNET_LOCALE
    )

    realms = client.get_realms()
    test_realm = realms[0]

    auctions = client.get_auctions(test_realm.id)
    print(auctions[0])

    commodities = client.get_commodities()
    highest = 0
    row = None
    for commodity in commodities:
        if commodity.item_id == 238197:
            print("Found it!", commodity)
        if commodity.quantity > highest:
            highest = commodity.quantity
            row = commodity

    print(row)

    # for name, id in realms:
    #     print(f"{name}: {id}")


if __name__ == "__main__":
    main()
