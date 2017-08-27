import random
import unittest

from pydealer import Stack, Card
from pydealer.const import SUITS, VALUES

from card import get_cards_type, are_cards_bigger
from card_type import *

num_tests = 100


class TestGetCardsType(unittest.TestCase):
    def test_same_suit_dragon(self):
        for i in range(num_tests):
            cards = Stack()
            suit = random.choice(SUITS)

            for value in VALUES:
                cards.add(Card(value, suit))

            self.assertEqual(get_cards_type(cards), SAME_SUIT_DRAGON)

    def test_diff_suit_dragon(self):
        for i in range(num_tests):
            cards = Stack(cards=[Card(VALUES[0], SUITS[0]), Card(VALUES[1], SUITS[1])])

            for value in VALUES[2:]:
                cards.add(Card(value, random.choice(SUITS)))
            self.assertEqual(get_cards_type(cards), DRAGON)

    def test_straight_flush(self):
        for i in range(num_tests):
            suit = random.choice(SUITS)

            cards = Stack(cards=[Card("Ace", suit), Card("2", suit), Card("3", suit), Card("4", suit), Card("5", suit)])
            self.assertEqual(get_cards_type(cards), STRAIGHT_FLUSH)

            cards = Stack(cards=[Card("2", suit), Card("3", suit), Card("4", suit), Card("5", suit), Card("6", suit)])
            self.assertEqual(get_cards_type(cards), STRAIGHT_FLUSH)

            cards = Stack(cards=[Card("Jack", suit), Card("Queen", suit), Card("King", suit), Card("Ace", suit),
                                 Card("2", suit)])
            self.assertEqual(get_cards_type(cards), STRAIGHT_FLUSH)

            cards = Stack()
            start_index = random.randint(1, 8)

            for index in range(start_index, start_index + 5):
                cards.add(Card(VALUES[index], suit))

            self.assertEqual(get_cards_type(cards), STRAIGHT_FLUSH)

    def test_four_of_a_kind(self):
        for i in range(num_tests):
            cards = Stack()
            values = list(VALUES)
            four_value = random.choice(values)
            values.remove(four_value)
            extra_value = random.choice(values)

            for suit in SUITS:
                cards.add(Card(four_value, suit))
            cards.add(Card(extra_value, random.choice(SUITS)))

            self.assertEqual(get_cards_type(cards), FOUR_OF_A_KIND)

    def test_full_house(self):
        for i in range(num_tests):
            cards = Stack()
            values = list(VALUES)
            three_value = random.choice(values)
            values.remove(three_value)
            two_value = random.choice(values)

            for suit in random.sample(SUITS, 3):
                cards.add(Card(three_value, suit))

            for suit in random.sample(SUITS, 2):
                cards.add(Card(two_value, suit, ))

            self.assertEqual(get_cards_type(cards), FULL_HOUSE)

    def test_flush(self):
        for i in range(num_tests):
            cards = Stack()
            suit = random.choice(SUITS)

            for value in random.sample(VALUES, 5):
                cards.add(Card(value, suit))

            if get_cards_type(cards) == STRAIGHT_FLUSH:
                continue

            self.assertEqual(get_cards_type(cards), FLUSH)

    def test_straight(self):
        for i in range(num_tests):
            cards = Stack(cards=[Card("Ace", SUITS[0]), Card("2", SUITS[1]), Card("3", random.choice(SUITS)),
                                 Card("4", random.choice(SUITS)), Card("5", random.choice(SUITS))])
            self.assertEqual(get_cards_type(cards), STRAIGHT)

            cards = Stack(cards=[Card("2", SUITS[0]), Card("3", SUITS[1]), Card("4", random.choice(SUITS)),
                                 Card("5", random.choice(SUITS)), Card("6", random.choice(SUITS))])
            self.assertEqual(get_cards_type(cards), STRAIGHT)

            cards = Stack(cards=[Card("Jack", SUITS[0]), Card("Queen", SUITS[1]), Card("King", random.choice(SUITS)),
                                 Card("Ace", random.choice(SUITS)), Card("2", random.choice(SUITS))])
            self.assertEqual(get_cards_type(cards), STRAIGHT)

            cards = Stack()
            start_index = random.randint(1, 8)
            cards.add([Card(VALUES[start_index], SUITS[0]), Card(VALUES[start_index + 1], SUITS[1])])

            for index in range(start_index + 2, start_index + 5):
                cards.add(Card(VALUES[index], random.choice(SUITS)))

            self.assertEqual(get_cards_type(cards), STRAIGHT)

    def test_three_of_a_kind(self):
        for i in range(num_tests):
            cards = Stack()
            value = random.choice(VALUES)

            for suit in random.sample(SUITS, 3):
                cards.add(Card(value, suit))

            self.assertEqual(get_cards_type(cards), THREE_OF_A_KIND)

    def test_pair(self):
        for i in range(num_tests):
            cards = Stack()
            value = random.choice(VALUES)

            for suit in random.sample(SUITS, 2):
                cards.add(Card(value, suit))

            self.assertEqual(get_cards_type(cards), PAIR)

    def test_single(self):
        for i in range(num_tests):
            cards = Stack(cards=[Card(random.choice(VALUES), random.choice(SUITS))])

            self.assertEqual(get_cards_type(cards), SINGLE)

    def test_invalid(self):
        cards = Stack(cards=[Card("3", SUITS[0]), Card("8", SUITS[1])])
        self.assertEqual(get_cards_type(cards), -1)

        cards = Stack(cards=[Card("3", SUITS[0]), Card("4", SUITS[0]), Card("8", SUITS[1])])
        self.assertEqual(get_cards_type(cards), -1)

        cards = Stack(cards=[Card("3", SUITS[0]), Card("4", SUITS[0]), Card("5", SUITS[0]), Card("8", SUITS[1])])
        self.assertEqual(get_cards_type(cards), -1)

        cards = Stack(cards=[Card("3", SUITS[0]), Card("4", SUITS[0]), Card("5", SUITS[0]), Card("6", SUITS[0]),
                             Card("8", SUITS[1])])
        self.assertEqual(get_cards_type(cards), -1)

        cards = Stack(cards=[Card("3", SUITS[0]), Card("4", SUITS[0]), Card("5", SUITS[0]), Card("6", SUITS[0]),
                             Card("7", SUITS[0]), Card("8", SUITS[0])])
        self.assertEqual(get_cards_type(cards), -1)


class TestAreCardsBigger(unittest.TestCase):
    def test_bigger_straight_flush(self):
        for i in range(num_tests):
            cards_a = Stack()
            cards_b = Stack()
            suit = random.choice(SUITS[:3])
            start_index = random.randint(1, 8)

            for index in range(start_index, start_index + 5):
                cards_a.add(Card(VALUES[index], suit))

            if suit == "Hearts":
                suit = "Spades"
            else:
                suit = random.choice(SUITS[(SUITS.index(suit) + 1):])

            start_index = random.randint(1, 8)
            for index in range(start_index, start_index + 5):
                cards_b.add(Card(VALUES[index], suit))

            self.assertTrue(are_cards_bigger(cards_a, cards_b))

    def test_bigger_four_of_a_kind(self):
        for i in range(num_tests):
            cards_a = Stack()
            cards_b = Stack()
            values = list(VALUES[1:])
            four_value = random.choice(values)
            index = values.index(four_value)
            values.remove(four_value)
            extra_value = random.choice(values)

            for suit in SUITS:
                cards_a.add(Card(four_value, suit))
            cards_a.add(Card(extra_value, random.choice(SUITS)))

            if four_value == "Ace":
                four_value = "2"
            else:
                four_value = random.choice(values[index:])
                values.remove(four_value)
            extra_value = random.choice(values)

            for suit in SUITS:
                cards_b.add(Card(four_value, suit))
            cards_b.add(Card(extra_value, random.choice(SUITS)))

            self.assertTrue(are_cards_bigger(cards_a, cards_b))

    def test_bigger_full_house(self):
        for i in range(num_tests):
            cards_a = Stack()
            cards_b = Stack()
            values = list(VALUES[1:])
            three_value = random.choice(values)
            index = values.index(three_value)
            values.remove(three_value)
            two_value = random.choice(values)

            for suit in random.sample(SUITS, 3):
                cards_a.add(Card(three_value, suit))

            for suit in random.sample(SUITS, 2):
                cards_a.add(Card(two_value, suit))

            if three_value == "Ace":
                three_value = "2"
            else:
                three_value = random.choice(values[index:])
                values.remove(three_value)
            two_value = random.choice(values)

            for suit in random.sample(SUITS, 3):
                cards_b.add(Card(three_value, suit))

            for suit in random.sample(SUITS, 2):
                cards_b.add(Card(two_value, suit))

            self.assertTrue(are_cards_bigger(cards_a, cards_b))

    def test_bigger_flush(self):
        for i in range(num_tests):
            cards_a = Stack()
            cards_b = Stack()
            suit = random.choice(SUITS[:2])
            values = random.sample(VALUES, 5)

            for value in values:
                cards_a.add(Card(value, suit))

            if get_cards_type(cards_a) == STRAIGHT_FLUSH:
                continue

            if suit == "Hearts":
                suit = "Spades"
            else:
                suit = random.choice(SUITS[(SUITS.index(suit) + 1):])

            values = random.sample(VALUES, 5)
            for value in values:
                cards_b.add(Card(value, suit))

            if get_cards_type(cards_b) == STRAIGHT_FLUSH:
                continue

            self.assertTrue(are_cards_bigger(cards_a, cards_b))

    def test_bigger_straight(self):
        for i in range(num_tests):
            cards_a = Stack()
            cards_b = Stack()
            start_index = random.randint(1, 7)
            cards_a.add([Card(VALUES[start_index], SUITS[0]), Card(VALUES[start_index + 1], SUITS[1])])

            for index in range(start_index + 2, start_index + 5):
                cards_a.add(Card(VALUES[index], random.choice(SUITS)))

            if start_index + 1 == 8:
                start_index = 8
            else:
                start_index = random.randint(start_index + 1, 7)

            cards_b.add([Card(VALUES[start_index], SUITS[0]), Card(VALUES[start_index + 1], SUITS[1])])
            for index in range(start_index + 2, start_index + 5):
                cards_b.add(Card(VALUES[index], random.choice(SUITS)))

            self.assertTrue(are_cards_bigger(cards_a, cards_b))

    def test_bigger_three_of_a_kind(self):
        for i in range(num_tests):
            cards_a = Stack()
            cards_b = Stack()
            value = random.choice(VALUES[1:])

            for suit in random.sample(SUITS, 3):
                cards_a.add(Card(value, suit))

            if value == "Ace":
                value = "2"
            else:
                value = random.choice(VALUES[(VALUES.index(value) + 1):])

            for suit in random.sample(SUITS, 3):
                cards_b.add(Card(value, suit))

            self.assertTrue(are_cards_bigger(cards_a, cards_b))

    def test_bigger_pair(self):
        for i in range(num_tests):
            cards_a = Stack()
            cards_b = Stack()
            value = random.choice(VALUES[1:])

            for suit in random.sample(SUITS, 2):
                cards_a.add(Card(value, suit))

            if value == "Ace":
                value = "2"
            else:
                value = random.choice(VALUES[(VALUES.index(value) + 1):])

            for suit in random.sample(SUITS, 2):
                cards_b.add(Card(value, suit))

            self.assertTrue(are_cards_bigger(cards_a, cards_b))

    def test_bigger_single(self):
        for i in range(num_tests):
            value = random.choice(VALUES[1:])
            cards_a = Stack(cards=[Card(value, random.choice(SUITS))])

            if value == "Ace":
                value = "2"
            else:
                value = random.choice(VALUES[(VALUES.index(value) + 1):])

            cards_b = Stack(cards=[Card(value, random.choice(SUITS))])

            self.assertTrue(are_cards_bigger(cards_a, cards_b))


if __name__ == '__main__':
    unittest.main()
