#!/usr/bin/env python3
# coding: utf-8

import random

from collections import Counter

from card_type import *


class Card:
    def __init__(self, suit, num):
        if suit not in range(4):
            raise ValueError("Suit must be int from 0 to 3")

        if num not in range(3, 16):
            raise ValueError("Num must be int from 3 to 15")

        # 0: ♦, 1: ♣, 2: ♥, 3: ♠
        self.suit = int(suit)
        self.num = int(num)

        if self.suit == 0:
            self.show_suit = "♦"
        elif self.suit == 1:
            self.show_suit = "♣"
        elif self.suit == 2:
            self.show_suit = "♥"
        else:
            self.show_suit = "♠"

        if self.num == 11:
            self.show_num = "J"
        elif self.num == 12:
            self.show_num = "Q"
        elif self.num == 13:
            self.show_num = "K"
        elif self.num == 14:
            self.show_num = "A"
        elif self.num == 15:
            self.show_num = "2"
        else:
            self.show_num = self.num

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        elif self.suit == other.suit and self.num == other.num:
            return True
        else:
            return False

    def __lt__(self, other):
        if self.num == other.num:
            if self.suit < other.suit:
                return True
            else:
                return False
        elif self.num < other.num:
            return True
        else:
            return False


class Deck:
    def __init__(self):
        self.cards = []

        for i in range(0, 4):
            for j in range(3, 16):
                self.cards.append(Card(i, j))

        random.shuffle(self.cards)


class Player:
    def __init__(self, cards):
        self.cards = cards

    def show_cards(self):
        i = 0
        for card in self.cards:
            print("%d:\t%s %s\n" % (i, card.show_suit, card.show_num))
            i += 1


# Checks if game is finished
def is_game_over(players):
    for player in players:
        if len(player.cards) == 0:
            return True

    return False


# Returns the type of the given cards
def get_cards_type(cards):
    cards.sort()
    cards_type = -1
    suits = set()
    nums = []

    for card in cards:
        suits.add(card.suit)
        nums.append(card.num)

    if len(cards) == 13:
        # Checks for dragon
        if sorted(nums) == list(range(min(nums), max(nums) + 1)):
            if len(suits) == 1:
                cards_type = SAME_SUIT_DRAGON
            else:
                cards_type = DRAGON

    elif len(cards) == 5:
        # Checks for same suit
        if len(suits) == 1:
            # Checks for A 2 3 4 5
            if cards[0].num == 3 and cards[1].num == 4 and cards[2].num == 5 and cards[3].num == 14 and \
                    cards[4].num == 15:
                cards_type = STRAIGHT_FLUSH

            # Checks for 2 3 4 5 6
            elif cards[0].num == 3 and cards[1].num == 4 and cards[2].num == 5 and cards[3].num == 6 and \
                    cards[4].num == 15:
                cards_type = STRAIGHT_FLUSH

            elif sorted(nums) == list(range(min(nums), max(nums) + 1)):
                cards_type = STRAIGHT_FLUSH
            else:
                cards_type = FLUSH
        else:
            num_counter = Counter(nums)

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
                if cards[0].num == 3 and cards[1].num == 4 and cards[2].num == 5 and cards[3].num == 14 and \
                        cards[4].num == 15:
                    cards_type = STRAIGHT

                # Checks for 2 3 4 5 6
                elif cards[0].num == 3 and cards[1].num == 4 and cards[2].num == 5 and cards[3].num == 6 and \
                        cards[4].num == 15:
                    cards_type = STRAIGHT

                elif sorted(nums) == list(range(min(nums), max(nums) + 1)):
                        cards_type = STRAIGHT

    elif len(cards) == 3:
        if cards[0].num == cards[1].num and cards[1].num == cards[2].num:
            cards_type = THREE_OF_A_KIND

    elif len(cards) == 2:
        if cards[0].num == cards[1].num:
            cards_type = PAIR

    elif len(cards) == 1:
        cards_type = SINGLE

    return cards_type


# Returns if currCards is greater than prevCards
# Also checks if currCards have the same num of cards with prevCards
def is_bigger(prev_cards, curr_cards):
    prev_cards.sort()
    curr_cards.sort()
    bigger = False

    if len(prev_cards) == 0:
        bigger = True
    elif len(prev_cards) == len(curr_cards):
        prev_cards_type = get_cards_type(prev_cards)
        curr_cards_type = get_cards_type(curr_cards)

        # Checks for 5 cards
        if prev_cards_type in range(4, 9) and curr_cards_type in range(4, 9):
            if curr_cards_type > prev_cards_type:
                bigger = True

            # Checks for bigger straight flush
            elif prev_cards_type == 8 and curr_cards_type == 8:
                # Bigger suit, ie bigger straight flush
                if curr_cards[0].suit > prev_cards[0].suit:
                    bigger = True

                # Same suit, checks for bigger num
                elif curr_cards[4].num > prev_cards[4].num:
                    bigger = True

            # Checks for bigger four of a kind
            elif prev_cards_type == 7 and curr_cards_type == 7:
                prev_num = -1
                curr_num = -1
                nums = []

                for card in prev_cards:
                    if card.num in nums:
                        prev_num = card.num
                        break

                    nums.append(card.num)

                del nums[:]
                for card in curr_cards:
                    if card.num in nums:
                        curr_num = card.num
                        break

                    nums.append(card.num)

                if curr_num > prev_num:
                    bigger = True

            # Checks for bigger full house
            elif prev_cards_type == 6 and curr_cards_type == 6:
                prev_nums = []
                curr_nums = []
                prev_num = 0
                curr_num = 0

                for card in prev_cards:
                    prev_nums.append(card.num)

                for card in curr_cards:
                    curr_nums.append(card.num)

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
                    bigger = True

            # Checks for bigger flush
            elif prev_cards_type == 5 and curr_cards_type == 5:
                if curr_cards[0].suit > prev_cards[0].suit:
                    bigger = True
                else:
                    for i in range(4, -1, -1):
                        if curr_cards[i].num > prev_cards[i].num:
                            bigger = True
                            break

            # Checks for bigger straight
            elif prev_cards_type == 4 and curr_cards_type == 4:
                all_same = True

                for i in range(4, -1, -1):
                    if curr_cards[i].num > prev_cards[i].num:
                        bigger = True
                        break
                    if curr_cards[i].num != prev_cards[i].num:
                        all_same = False

                if not bigger and all_same:
                    if curr_cards[4].suit > prev_cards[4].suit:
                        bigger = True

        # Checks for bigger three of a kind
        elif prev_cards_type == 3 and curr_cards_type == 3:
            if curr_cards[0].num > prev_cards[0].num:
                bigger = True

        # Checks for bigger pair
        elif prev_cards_type == 2 and curr_cards_type == 2:
            if curr_cards[0].num > prev_cards[0].num:
                bigger = True
            else:
                if prev_cards[0].suit > prev_cards[1].suit:
                    prev_suit = prev_cards[0].suit
                else:
                    prev_suit = prev_cards[1].suit

                if curr_cards[0].suit > curr_cards[1].suit:
                    curr_suit = curr_cards[0].suit
                else:
                    curr_suit = curr_cards[1].suit

                if curr_suit > prev_suit:
                    bigger = True

        # Checks for bigger single
        elif prev_cards_type == 1 and curr_cards_type == 1:
            if curr_cards[0].num > prev_cards[0].num:
                bigger = True
            elif curr_cards[0].num == prev_cards[0].num:
                if curr_cards[0].suit > prev_cards[0].suit:
                    bigger = True

    return bigger


def main():
    deck = Deck()

    # Sets up players
    curr_player = -1
    players = []
    for i in range(0, 4):
        player_deck = []

        for j in range(0, 13):
            card = deck.cards.pop()
            player_deck.append(card)

            # Player with ♦3 starts first
            if card.suit == 0 and card.num == 3:
                curr_player = i

        player_deck.sort()
        players.append(Player(player_deck))

    game_round = 1
    player_in_control = -1
    prev_cards = []

    while not is_game_over(players):
        print("----------------------------------------")
        print("Round %d" % game_round)
        print("Player %d's Turn" % curr_player)
        print("----------------------------------------")

        valid = True
        first = True
        bigger = True
        passed = False
        use_cards = []

        while not valid or first or not bigger:
            if not bigger:
                print("----------------------------------------")
                print("Your cards are not bigger than prev")
                print("----------------------------------------")
            elif not first:
                print("----------------------------------------")
                print("Invalid Input. Please Try again.")
                print("----------------------------------------")

            if game_round > 1:
                print("Last player's cards")
                for card in prev_cards:
                    print("%s %s" % (card.show_suit, card.show_num))
                print("----------------------------------------")

            use_cards = []
            valid = True
            first = False

            print("Your deck of cards:")
            players[curr_player].show_cards()
            print()

            print("Please enter the id of the cards that you would like to use")
            print("Example input: 0,1,2")
            print("Enter the word 'pass' if you would like to pass")
            command = input("What cards would you like to use?")

            command = command.lower()
            if command == "pass":
                passed = True
                break

            nums = command.split(",")
            for num in nums:
                num = int(num)

                if num not in range(0, len(players[curr_player].cards)):
                    print(num)
                    valid = False
                    break
                else:
                    card = players[curr_player].cards[num]
                    use_cards.append(card)

            use_cards.sort()
            if valid and get_cards_type(use_cards) == -1:
                valid = False

            if (valid and curr_player != player_in_control and
                    not is_bigger(prev_cards, use_cards)):
                bigger = False
            else:
                bigger = True

        if not passed:
            prev_cards = []

        for card in use_cards:
            player_in_control = curr_player
            players[curr_player].cards.remove(card)
            prev_cards.append(card)

        game_round += 1
        curr_player = (curr_player + 1) % 4


if __name__ == '__main__':
    main()
