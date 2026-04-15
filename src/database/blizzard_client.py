from typing import Optional
from pydantic import BaseModel
import httpx
import time


class RealmData(BaseModel):
    name: str
    id: int


class AuctionData(BaseModel):
    auction_id: int
    item_id: int
    unit_price: Optional[int] = None
    quantity: int
    duration: str


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

    def get_token(self) -> str:
        if self.token and self.expires_at >= time.time():
            return self.token

        url = f"https://{self.region}.battle.net/oauth/token"

        response = httpx.post(
            url,
            auth=(self.client_id, self.client_secret),
            data={"grant_type": "client_credentials"},
        )
        response.raise_for_status()

        data = response.json()
        self.token = data["access_token"]
        self.expires_at = time.time() + data["expires_in"] - 60

        return self.token

    def get_realms(self) -> list[RealmData]:
        token = self.get_token()

        url = f"https://{self.region}.api.blizzard.com/data/wow/search/connected-realm"

        response = httpx.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
            params={"namespace": f"dynamic-{self.region}"},
        )
        response.raise_for_status()

        realm_data = response.json()
        realms: list[RealmData] = []

        for result in realm_data["results"]:
            for realm in result["data"]["realms"]:
                realms.append(
                    RealmData(name=realm["name"].get("en_US"), id=result["data"]["id"])
                )

        return realms

    def get_auctions(self, realm_id: int) -> list[AuctionData]:
        time.sleep(0.75)

        token = self.get_token()

        url = f"https://{self.region}.api.blizzard.com/data/wow/connected-realm/{realm_id}/auctions"

        response = httpx.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
            params={"namespace": f"dynamic-{self.region}"},
        )
        response.raise_for_status()

        auction_data = response.json()
        auctions: list[AuctionData] = []

        for auction in auction_data["auctions"]:
            auction_id = auction.get("id")
            item_id = auction.get("item").get("id")
            unit_price = auction.get("buyout")
            quantity = auction.get("quantity")
            duration = auction.get("time_left")

            # Skip bid-only and other invalid rows
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

    def get_commodities(self) -> list[AuctionData]:
        token = self.get_token()

        url = f"https://{self.region}.api.blizzard.com/data/wow/auctions/commodities"

        response = httpx.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
            params={"namespace": f"dynamic-{self.region}", "locale": self.locale},
        )
        response.raise_for_status()

        auction_data = response.json()
        auctions: list[AuctionData] = []

        for auction in auction_data["auctions"]:
            auction_id = auction.get("id")
            item_id = auction.get("item").get("id")
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
