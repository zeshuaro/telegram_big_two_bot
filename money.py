from itertools import combinations
from pydealer import Stack

from card import get_cards_type
from card_type import STRAIGHT_FLUSH, FOUR_OF_A_KIND


def max_money_lost(money):
    return money * 13 * pow(2, 5)


def get_money_lost(cards, card_money, num_cards_left):
    money_lost = card_money * cards.size

    if cards.size >= 10:
        money_lost *= 2

    money_lost *= pow(2, len(cards.find("2")))

    if cards.size == 13:
        money_lost *= 2

    if num_cards_left == 39:
        money_lost *= 2

    if has_good_cards(cards):
        money_lost *= 2

    return money_lost


# Checks if cards contain straight flush or flour of a kind
def has_good_cards(cards):
    if cards.size > 4:
        cards_combinations = combinations(cards, 5)

        for card_subset in cards_combinations:
            if get_cards_type(Stack(cards=card_subset)) in (STRAIGHT_FLUSH, FOUR_OF_A_KIND):
                return True

    return False
