# server/user_profile.py

from collections import Counter
from typing import List, Dict


class UserProfile:
    def __init__(
        self,
        dietary_required: List[str] = None,
        preferred_cuisines: List[str] = None,
        disliked_cuisines: List[str] = None,
        price_preference: int = 2,
    ):
        self.dietary_required = dietary_required or []
        self.preferred_cuisines = preferred_cuisines or []
        self.disliked_cuisines = disliked_cuisines or []
        self.price_preference = price_preference

        # store restaurant_ids user clicked
        self.click_history: List[str] = []

    def record_click(self, restaurant_id: str):
        self.click_history.append(restaurant_id)

    def cuisine_click_counts(self, restaurant_lookup: Dict[str, dict]) -> Counter:
        """
        Count how many times each cuisine was clicked.
        """
        counter = Counter()

        for rid in self.click_history:
            if rid in restaurant_lookup:
                cuisines = restaurant_lookup[rid].get("cuisines", [])
                for c in cuisines:
                    counter[c.lower()] += 1

        return counter