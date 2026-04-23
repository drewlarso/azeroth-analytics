import asyncio
from httpx import AsyncClient
import time
from api.models import AuctionData, RealmData, ItemData, ItemClassData, ItemSubclassData


class BlizzardClient:
    def __init__(
        self, client_id: str, client_secret: str, region: str, locale: str
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.region = region
        self.locale = locale
        self.token = ""
        self.expires_at = 0
        self.semaphore = asyncio.Semaphore(20)

    async def get_token(self, client: AsyncClient) -> str:
        if self.token and self.expires_at >= time.time():
            return self.token

        url = f"https://{self.region}.battle.net/oauth/token"
        response = await client.post(
            url,
            auth=(self.client_id, self.client_secret),
            data={"grant_type": "client_credentials"},
        )
        response.raise_for_status()

        data = response.json()
        self.token = data["access_token"]
        self.expires_at = time.time() + data["expires_in"] - 60

        return self.token

    async def _request_with_retry(
        self, http_client: AsyncClient, url: str, params: dict
    ) -> dict:
        token = await self.get_token(http_client)
        headers = {"Authorization": f"Bearer {token}"}

        async with self.semaphore:
            for attempt in range(3):
                response = await http_client.get(url, headers=headers, params=params)

                if response.status_code == 429:
                    wait_time = (attempt + 1) * 2
                    print(f"Rate limited. Waiting {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue

                response.raise_for_status()
                return response.json()

        return {}

    async def get_realms(self, http_client: AsyncClient) -> list[RealmData]:
        url = f"https://{self.region}.api.blizzard.com/data/wow/search/connected-realm"
        params = {"namespace": f"dynamic-{self.region}"}

        data = await self._request_with_retry(http_client, url, params)
        realms: list[RealmData] = []

        for result in data["results"]:
            for realm in result["data"]["realms"]:
                realms.append(
                    RealmData(name=realm["name"].get("en_US"), id=result["data"]["id"])
                )
        return realms

    async def get_auctions(
        self, http_client: AsyncClient, realm_id: int
    ) -> list[AuctionData]:
        url = f"https://{self.region}.api.blizzard.com/data/wow/connected-realm/{realm_id}/auctions"
        params = {"namespace": f"dynamic-{self.region}"}

        auction_data = await self._request_with_retry(http_client, url, params)
        auctions: list[AuctionData] = []

        for auction in auction_data.get("auctions", []):
            auction_id = auction.get("id")
            item_id = auction.get("item", {}).get("id")
            unit_price = auction.get("buyout") or auction.get("unit_price")
            quantity = auction.get("quantity")
            duration = auction.get("time_left")

            if not all([auction_id, item_id, unit_price, quantity, duration]):
                continue

            auctions.append(
                AuctionData(
                    auction_id=int(auction_id),
                    item_id=int(item_id),
                    unit_price=int(unit_price),
                    quantity=int(quantity),
                    duration=duration,
                )
            )

        return auctions

    async def get_commodities(self, http_client: AsyncClient) -> list[AuctionData]:
        url = f"https://{self.region}.api.blizzard.com/data/wow/auctions/commodities"
        params = {"namespace": f"dynamic-{self.region}", "locale": self.locale}

        auction_data = await self._request_with_retry(http_client, url, params)
        auctions: list[AuctionData] = []

        for auction in auction_data.get("auctions", []):
            auction_id = auction.get("id")
            item_id = auction.get("item", {}).get("id")
            unit_price = auction.get("unit_price")
            quantity = auction.get("quantity")
            duration = auction.get("time_left")

            if not all([auction_id, item_id, unit_price, quantity, duration]):
                continue

            auctions.append(
                AuctionData(
                    auction_id=int(auction_id),
                    item_id=int(item_id),
                    unit_price=int(unit_price),
                    quantity=int(quantity),
                    duration=duration,
                )
            )

        return auctions

    async def get_items(self, http_client: AsyncClient) -> list[ItemData]:
        url = f"https://{self.region}.api.blizzard.com/data/wow/search/item"
        items = []
        last_id = 0

        while True:
            params = {
                "namespace": f"static-{self.region}",
                "locale": self.locale,
                "orderby": "id",
                "_pageSize": 1000,
                "_page": 1,
                "id": f"[{last_id},]",
            }

            data = await self._request_with_retry(http_client, url, params)
            results = data.get("results", [])
            if not results:
                break

            ids = []
            for result in results:
                item_data = result.get("data", {})
                item_id = item_data.get("id")
                if not item_id:
                    continue

                try:
                    items.append(
                        ItemData(
                            id=int(item_id),
                            name=item_data.get("name", {}).get(self.locale),
                            quality=item_data.get("quality", {})
                            .get("name", {})
                            .get(self.locale),
                            item_class_id=int(item_data["item_class"]["id"]),
                            item_subclass_id=int(item_data["item_subclass"]["id"]),
                            purchase_price=item_data.get("purchase_price"),
                            sell_price=item_data.get("sell_price"),
                            stackable=item_data.get("is_stackable"),
                            media=int(m["id"])
                            if (m := item_data.get("media"))
                            else None,
                        )
                    )
                    ids.append(int(item_id))
                except Exception as e:
                    print(f"Skipping item {item_id}: {e}")

            last_id = max(ids) + 1
            if len(results) < 1000:
                break

        return items

    async def get_item_classes(
        self, http_client: AsyncClient
    ) -> tuple[list[ItemClassData], list[ItemSubclassData]]:
        url = f"https://{self.region}.api.blizzard.com/data/wow/item-class/index"
        params = {"namespace": f"static-{self.region}", "locale": self.locale}

        data = await self._request_with_retry(http_client, url, params)

        classes = []
        subclasses = []

        for item_class in data.get("item_classes", []):
            class_id = item_class["id"]
            class_name = item_class["name"]
            classes.append(ItemClassData(id=class_id, name=class_name))

            sub_url = (
                f"https://{self.region}.api.blizzard.com/data/wow/item-class/{class_id}"
            )
            sub_data = await self._request_with_retry(http_client, sub_url, params)

            for subclass in sub_data.get("item_subclasses", []):
                subclasses.append(
                    ItemSubclassData(
                        id=subclass["id"],
                        class_id=class_id,
                        name=subclass["name"],
                    )
                )

        return classes, subclasses
