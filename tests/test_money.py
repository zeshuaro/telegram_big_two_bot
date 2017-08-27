import unittest

from pydealer import Stack, Card

from money import get_money_lost


class TestGetMoneyLost(unittest.TestCase):
    def test_basic(self):
        cards = Stack(cards=[Card("3", "Diamonds"), Card("3", "Clubs")])
        self.assertEqual(get_money_lost(cards, 5, 20), 10)

        cards = Stack(cards=[Card("3", "Diamonds"), Card("3", "Clubs"), Card("3", "Hearts")])
        self.assertEqual(get_money_lost(cards, 5, 20), 15)

    def test_ten_cards(self):
        cards = Stack(cards=[Card("3", "Diamonds"), Card("4", "Clubs"), Card("5", "Diamonds"), Card("6", "Clubs"),
                             Card("7", "Diamonds"), Card("8", "Clubs"), Card("9", "Diamonds"), Card("10", "Clubs"),
                             Card("Jack", "Diamonds"), Card("Queen", "Clubs")])
        self.assertEqual(get_money_lost(cards, 5, 20), 100)

    def test_has_two(self):
        cards = Stack(cards=[Card("2", "Diamonds")])
        self.assertEqual(get_money_lost(cards, 5, 20), 10)

        cards = Stack(cards=[Card("2", "Diamonds"), Card("2", "Clubs")])
        self.assertEqual(get_money_lost(cards, 5, 20), 40)

    def test_thirteen_cards(self):
        cards = Stack(cards=[Card("3", "Diamonds"), Card("4", "Clubs"), Card("5", "Diamonds"), Card("6", "Clubs"),
                             Card("7", "Diamonds"), Card("8", "Clubs"), Card("9", "Diamonds"), Card("10", "Clubs"),
                             Card("Jack", "Diamonds"), Card("Queen", "Clubs"), Card("King", "Diamonds"),
                             Card("Ace", "Clubs"), Card("3", "Hearts")])
        self.assertEqual(get_money_lost(cards, 5, 20), 260)

    def test_all_thirteen_cards(self):
        cards = Stack(cards=[Card("3", "Diamonds"), Card("4", "Clubs"), Card("5", "Diamonds"), Card("6", "Clubs"),
                             Card("7", "Diamonds"), Card("8", "Clubs"), Card("9", "Diamonds"), Card("10", "Clubs"),
                             Card("Jack", "Diamonds"), Card("Queen", "Clubs"), Card("King", "Diamonds"),
                             Card("Ace", "Clubs"), Card("3", "Hearts")])
        self.assertEqual(get_money_lost(cards, 5, 39), 520)

    def test_straight_flush(self):
        cards = Stack(cards=[Card("3", "Diamonds"), Card("4", "Diamonds"), Card("5", "Diamonds"),
                             Card("6", "Diamonds"), Card("7", "Diamonds")])
        self.assertEqual(get_money_lost(cards, 5, 20), 50)

        cards = Stack(cards=[Card("3", "Diamonds"), Card("4", "Diamonds"), Card("5", "Diamonds"),
                             Card("6", "Diamonds"), Card("7", "Diamonds"), Card("7", "Clubs")])
        self.assertEqual(get_money_lost(cards, 5, 20), 60)

    def test_four_of_a_kind(self):
        cards = Stack(cards=[Card("3", "Diamonds"), Card("3", "Clubs"), Card("3", "Hearts"), Card("3", "Spades"),
                             Card("4", "Diamonds")])
        self.assertEqual(get_money_lost(cards, 5, 20), 50)

        cards = Stack(cards=[Card("3", "Diamonds"), Card("3", "Clubs"), Card("3", "Hearts"), Card("3", "Spades"),
                             Card("4", "Diamonds"), Card("5", "Spades")])
        self.assertEqual(get_money_lost(cards, 5, 20), 60)


if __name__ == '__main__':
    unittest.main()
