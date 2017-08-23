#!/usr/bin/env python3

import pydealer

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, PickleType
from sqlalchemy.ext.hybrid import hybrid_property

from cards import suit_unicode, get_cards_type, are_cards_bigger
from player import Player


Base = declarative_base()

class Game:
    __tablename__ = "game"

    group_tele_id = Column(Integer, primary_key=True)
    game_round = Column(Integer)
    curr_player = Column(Integer)
    biggest_player = Column(Integer)
    count_pass = Column(Integer)
    prev_cards = Column(PickleType)

    def __init__(self):
        self.game_round = 0
        self.count_pass = 0
        self.prev_cards = pydealer.Stack()
        self.players = []

        deck = pydealer.Deck(ranks=pydealer.BIG2_RANKS)
        deck.shuffle()

        for i in range(4):
            player = Player(i)

            cards = deck.deal(13)
            player.cards.insert_list(cards)
            self.players.append(player)

            if cards.find("3D"):
                self.curr_player = i
                self.biggest_player = i

    @hybrid_property
    def is_game_over(self):
        for player in self.players:
            if player.cards.size == 0:
                return True
        return False


def main():
    game = Game()

    while not game.is_game_over:
        print("----------------------------------------")
        print("Round %d" % game.game_round)
        print("Player %d's Turn" % game.curr_player)
        print("----------------------------------------")

        valid = True
        first = True
        bigger = True
        passed = False
        use_cards = pydealer.Stack()

        while not valid or first or not bigger:
            if use_cards:
                for card in use_cards:
                    game.players[game.curr_player].cards.add(card)

            if not bigger:
                print("----------------------------------------")
                print("Your cards are not bigger than prev")
                print("----------------------------------------")
            elif not first:
                print("----------------------------------------")
                print("Invalid Input. Please Try again.")
                print("----------------------------------------")

            if game.game_round >= 1:
                print("Last player's cards")
                for card in game.prev_cards:
                    print("%s %s" % (suit_unicode(card.suit), card.value))
                print("----------------------------------------")

            use_cards = pydealer.Stack()
            valid = True
            first = False

            print("Your deck of cards:")
            game.players[game.curr_player].cards.sort(ranks=pydealer.BIG2_RANKS)
            for i, card in enumerate(game.players[game.curr_player].cards):
                print("%d: %s %s" % (i, suit_unicode(card.suit), card.value))
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

                if num not in range(0, game.players[game.curr_player].cards.size):
                    print(num)
                    valid = False
                    break
                else:
                    card = game.players[game.curr_player].cards.get(num)
                    use_cards.add(card)

            # use_cards.sort()
            if valid and get_cards_type(use_cards) == -1:
                valid = False

            if (valid and game.curr_player != game.biggest_player and
                    not are_cards_bigger(game.prev_cards, use_cards)):
                bigger = False
            else:
                bigger = True

        if not passed:
            game.prev_cards = pydealer.Stack()

        for card in use_cards:
            game.biggest_player = game.curr_player
            game.prev_cards.add(card)

        game.game_round += 1
        game.curr_player = (game.curr_player + 1) % 4


if __name__ == '__main__':
    main()
