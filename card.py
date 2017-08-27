from collections import Counter
from pydealer.const import BIG2_RANKS

from card_type import *


def suit_unicode(suit):
    if suit == "Diamonds":
        return "♦"
    elif suit == "Clubs":
        return "♣"
    elif suit == "Hearts":
        return "♥"
    else:
        return "♠"


def suit_rank(suit):
    return BIG2_RANKS["suits"][suit]


def value_rank(value):
    return BIG2_RANKS["values"][value]


def get_cards_type(cards):
    cards.sort(ranks=BIG2_RANKS)
    cards_type = -1
    suits = set()
    values = []

    for card in cards:
        suits.add(card.suit)
        values.append(value_rank(card.value))

    if cards.size == 13:
        # Checks for dragon
        if sorted(values) == list(range(min(values), max(values) + 1)):
            if len(suits) == 1:
                cards_type = SAME_SUIT_DRAGON
            else:
                cards_type = DRAGON

    elif cards.size == 5:
        # Checks for same suit
        if len(suits) == 1:
            # Checks for A 2 3 4 5
            if cards[0].value == "3" and cards[1].value == "4" and cards[2].value == "5" and \
                    cards[3].value == "Ace" and cards[4].value == "2":
                cards_type = STRAIGHT_FLUSH

            # Checks for 2 3 4 5 6
            elif cards[0].value == "3" and cards[1].value == "4" and cards[2].value == "5" and \
                    cards[3].value == "6" and cards[4].value == "2":
                cards_type = STRAIGHT_FLUSH

            elif sorted(values) == list(range(min(values), max(values) + 1)):
                cards_type = STRAIGHT_FLUSH
            else:
                cards_type = FLUSH
        else:
            num_counter = Counter(values)

            if len(num_counter) == 2:
                for num in num_counter.keys():
                    if num_counter[num] == 4:
                        cards_type = FOUR_OF_A_KIND
                        break
                    elif num_counter[num] == 3:
                        cards_type = FULL_HOUSE
                        break

            # Checks for straight
            else:
                # Checks for A 2 3 4 5
                if cards[0].value == "3" and cards[1].value == "4" and cards[2].value == "5" and \
                        cards[3].value == "Ace" and cards[4].value == "2":
                    cards_type = STRAIGHT

                # Checks for 2 3 4 5 6
                elif cards[0].value == "3" and cards[1].value == "4" and cards[2].value == "5" and \
                        cards[3].value == "6" and cards[4].value == "2":
                    cards_type = STRAIGHT

                elif sorted(values) == list(range(min(values), max(values) + 1)):
                        cards_type = STRAIGHT

    elif cards.size == 3:
        if cards[0].value == cards[1].value and cards[1].value == cards[2].value:
            cards_type = THREE_OF_A_KIND

    elif cards.size == 2:
        if cards[0].value == cards[1].value:
            cards_type = PAIR

    elif cards.size == 1:
        cards_type = SINGLE

    return cards_type


# Returns if currCards is greater than prevCards
# Also checks if currCards have the same num of cards with prevCards
def are_cards_bigger(prev_cards, curr_cards):
    prev_cards.sort(ranks=BIG2_RANKS)
    curr_cards.sort(ranks=BIG2_RANKS)
    is_bigger = False

    if len(prev_cards) == 0:
        is_bigger = True
    elif len(prev_cards) == len(curr_cards):
        prev_cards_type = get_cards_type(prev_cards)
        curr_cards_type = get_cards_type(curr_cards)

        # Checks for 5 cards
        if prev_cards_type in range(4, 9) and curr_cards_type in range(4, 9):
            if curr_cards_type > prev_cards_type:
                is_bigger = True

            # Checks for bigger straight flush
            elif prev_cards_type == 8 and curr_cards_type == 8:
                # Bigger suit, ie bigger straight flush
                if suit_rank(curr_cards[0].suit) > suit_rank(prev_cards[0].suit):
                    is_bigger = True

                # Same suit, checks for bigger num
                elif curr_cards[4].value > prev_cards[4].value:
                    is_bigger = True

            # Checks for bigger four of a kind
            elif prev_cards_type == 7 and curr_cards_type == 7:
                prev_num = -1
                curr_num = -1
                nums = []

                for card in prev_cards:
                    if card.value in nums:
                        prev_num = value_rank(card.value)
                        break

                    nums.append(card.value)

                del nums[:]
                for card in curr_cards:
                    if card.value in nums:
                        curr_num = value_rank(card.value)
                        break

                    nums.append(card.value)

                if curr_num > prev_num:
                    is_bigger = True

            # Checks for bigger full house
            elif prev_cards_type == 6 and curr_cards_type == 6:
                prev_nums = []
                curr_nums = []
                prev_num = 0
                curr_num = 0

                for card in prev_cards:
                    prev_nums.append(value_rank(card.value))

                for card in curr_cards:
                    curr_nums.append(value_rank(card.value))

                prev_nums = Counter(prev_nums)
                curr_nums = Counter(curr_nums)

                for num in prev_nums.keys():
                    if prev_nums[num] == 3:
                        prev_num = num
                        break

                for num in curr_nums.keys():
                    if curr_nums[num] == 3:
                        curr_num = num
                        break

                if curr_num > prev_num:
                    is_bigger = True

            # Checks for bigger flush
            elif prev_cards_type == 5 and curr_cards_type == 5:
                if suit_rank(curr_cards[0].suit) > suit_rank(prev_cards[0].suit):
                    is_bigger = True
                else:
                    for i in range(4, -1, -1):
                        if value_rank(curr_cards[i].value) > value_rank(prev_cards[i].value):
                            is_bigger = True
                            break

            # Checks for bigger straight
            elif prev_cards_type == 4 and curr_cards_type == 4:
                all_same = True

                for i in range(4, -1, -1):
                    if value_rank(curr_cards[i].value) > value_rank(prev_cards[i].value):
                        is_bigger = True
                        break
                    if curr_cards[i].value != prev_cards[i].value:
                        all_same = False

                if not is_bigger and all_same:
                    if suit_rank(curr_cards[4].suit) > suit_rank(prev_cards[4].suit):
                        is_bigger = True

        # Checks for bigger three of a kind
        elif prev_cards_type == 3 and curr_cards_type == 3:
            if value_rank(curr_cards[0].value) > value_rank(prev_cards[0].value):
                is_bigger = True

        # Checks for bigger pair
        elif prev_cards_type == 2 and curr_cards_type == 2:
            if value_rank(curr_cards[0].value) > value_rank(prev_cards[0].value):
                is_bigger = True
            else:
                if suit_rank(prev_cards[0].suit) > suit_rank(prev_cards[1].suit):
                    prev_suit = suit_rank(prev_cards[0].suit)
                else:
                    prev_suit = suit_rank(prev_cards[1].suit)

                if suit_rank(curr_cards[0].suit) > suit_rank(curr_cards[1].suit):
                    curr_suit = suit_rank(curr_cards[0].suit)
                else:
                    curr_suit = suit_rank(curr_cards[1].suit)

                if curr_suit > prev_suit:
                    is_bigger = True

        # Checks for bigger single
        elif prev_cards_type == 1 and curr_cards_type == 1:
            if value_rank(curr_cards[0].value) > value_rank(prev_cards[0].value):
                is_bigger = True
            elif value_rank(curr_cards[0].value) == value_rank(prev_cards[0].value):
                if suit_rank(curr_cards[0].suit) > suit_rank(prev_cards[0].suit):
                    is_bigger = True

    return is_bigger
