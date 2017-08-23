#!/usr/bin/env python3

import random
import unittest

import card_type as ct
from game import big_two_game as bt

num_tests = 100


class TestCard(unittest.TestCase):
    def test_invalid_cards(self):
        with self.assertRaises(ValueError):
            bt.Card(-1, 3)
            bt.Card(4, 3)
            bt.Card(0, 0)
            bt.Card(0, 20)
            bt.Card(-1, 30)

    def test_compare_cards(self):
        card_a = bt.Card(0, 3)
        card_b = bt.Card(0, 3)
        self.assertEqual(card_a, card_b)
        self.assertFalse(card_a > card_b)
        self.assertFalse(card_a < card_b)

        card_a = bt.Card(0, 3)
        card_b = bt.Card(1, 3)
        self.assertFalse(card_a == card_b)
        self.assertFalse(card_a > card_b)
        self.assertTrue(card_a < card_b)

        card_a = bt.Card(0, 3)
        card_b = bt.Card(0, 4)
        self.assertFalse(card_a == card_b)
        self.assertFalse(card_a > card_b)
        self.assertTrue(card_a < card_b)


class TestGetCardsType(unittest.TestCase):
    def test_same_suit_dragon(self):
        for i in range(num_tests):
            cards = []
            suit = random.randint(0, 3)

            for num in range(3, 16):
                cards.append(bt.Card(suit, num))

            self.assertEqual(bt.get_cards_type(cards), ct.SAME_SUIT_DRAGON)

    def test_diff_suit_dragon(self):
        for i in range(num_tests):
            cards = []

            for num in range(3, 16):
                cards.append(bt.Card(random.randint(0, 3), num))

            self.assertEqual(bt.get_cards_type(cards), ct.DRAGON)

    def test_straight_flush(self):
        for i in range(num_tests):
            suit = random.randint(0, 3)

            # Tests for A 2 3 4 5
            cards = [bt.Card(suit, 3), bt.Card(suit, 4), bt.Card(suit, 5), bt.Card(suit, 14), bt.Card(suit, 15)]
            self.assertEqual(bt.get_cards_type(cards), ct.STRAIGHT_FLUSH)

            # Tests for 2 3 4 5 6
            cards = [bt.Card(suit, 3), bt.Card(suit, 4), bt.Card(suit, 5), bt.Card(suit, 6), bt.Card(suit, 15)]
            self.assertEqual(bt.get_cards_type(cards), ct.STRAIGHT_FLUSH)

            cards = []
            start_num = random.randint(3, 11)

            for num in range(start_num, start_num + 5):
                cards.append(bt.Card(suit, num))

            self.assertEqual(bt.get_cards_type(cards), ct.STRAIGHT_FLUSH)

    def test_four_of_a_kind(self):
        for i in range(num_tests):
            cards = []
            nums = list(range(3, 16))
            four_num = random.choice(nums)
            nums.remove(four_num)
            extra_num = random.choice(nums)

            for suit in range(0, 4):
                cards.append(bt.Card(suit, four_num))
            cards.append(bt.Card(random.randint(0, 3), extra_num))

            self.assertEqual(bt.get_cards_type(cards), ct.FOUR_OF_A_KIND)

    def test_full_house(self):
        for i in range(num_tests):
            cards = []
            nums = list(range(3, 16))
            three_num = random.choice(nums)
            nums.remove(three_num)
            two_num = random.choice(nums)

            for suit in random.sample(range(0, 4), 3):
                cards.append(bt.Card(suit, three_num))

            for suit in random.sample(range(0, 4), 2):
                cards.append(bt.Card(suit, two_num))

            self.assertEqual(bt.get_cards_type(cards), ct.FULL_HOUSE)

    def test_flush(self):
        for i in range(num_tests):
            cards = []
            suit = random.randint(0, 3)
            nums = random.sample(range(3, 16), 5)

            while sorted(nums) == list(range(min(nums), max(nums) + 1)) or sorted(nums) == [3, 4, 5, 14, 15] or \
                    sorted(nums) == [3, 4, 5, 6, 15]:
                nums = random.sample(range(3, 16), 5)

            for num in nums:
                cards.append(bt.Card(suit, num))

            self.assertEqual(bt.get_cards_type(cards), ct.FLUSH)

    def test_straight(self):
        for i in range(num_tests):
            # Tests for A 2 3 4 5
            cards = [bt.Card(random.randint(1, 3), 3), bt.Card(random.randint(1, 3), 4),
                     bt.Card(random.randint(1, 3), 5), bt.Card(random.randint(1, 3), 14),
                     bt.Card(0, 15)]
            self.assertEqual(bt.get_cards_type(cards), ct.STRAIGHT)

            # Tests for 2 3 4 5 6
            cards = [bt.Card(random.randint(1, 3), 3), bt.Card(random.randint(1, 3), 4),
                     bt.Card(random.randint(1, 3), 5), bt.Card(random.randint(1, 3), 6),
                     bt.Card(0, 15)]
            self.assertEqual(bt.get_cards_type(cards), ct.STRAIGHT)

            cards = []
            start_num = random.randint(3, 11)
            cards.append(bt.Card(0, start_num))

            for num in range(start_num + 1, start_num + 5):
                cards.append(bt.Card(random.randint(1, 3), num))

            self.assertEqual(bt.get_cards_type(cards), ct.STRAIGHT)

    def test_three_of_a_kind(self):
        for i in range(num_tests):
            cards = []
            num = random.randint(3, 15)

            for suit in random.sample(range(0, 4), 3):
                cards.append(bt.Card(suit, num))

            self.assertEqual(bt.get_cards_type(cards), ct.THREE_OF_A_KIND)

    def test_pair(self):
        for i in range(num_tests):
            cards = []
            num = random.randint(3, 15)

            for suit in random.sample(range(0, 4), 2):
                cards.append(bt.Card(suit, num))

            self.assertEqual(bt.get_cards_type(cards), ct.PAIR)

    def test_single(self):
        for i in range(num_tests):
            cards = [bt.Card(random.randint(0, 3), random.randint(3, 15))]

            self.assertEqual(bt.get_cards_type(cards), ct.SINGLE)

    def test_invalid(self):
        cards = [bt.Card(0, 3), bt.Card(1, 8)]
        self.assertEqual(bt.get_cards_type(cards), -1)

        cards = [bt.Card(0, 3), bt.Card(0, 4), bt.Card(1, 8)]
        self.assertEqual(bt.get_cards_type(cards), -1)

        cards = [bt.Card(0, 3), bt.Card(0, 4), bt.Card(0, 5), bt.Card(1, 8)]
        self.assertEqual(bt.get_cards_type(cards), -1)

        cards = [bt.Card(0, 3), bt.Card(0, 4), bt.Card(0, 5), bt.Card(0, 6), bt.Card(1, 8)]
        self.assertEqual(bt.get_cards_type(cards), -1)

        cards = [bt.Card(0, 3), bt.Card(0, 4), bt.Card(0, 5), bt.Card(0, 6), bt.Card(0, 7), bt.Card(0, 8)]
        self.assertEqual(bt.get_cards_type(cards), -1)


class TestIsBigger(unittest.TestCase):
    def test_bigger_straight_flush(self):
        for i in range(num_tests):
            cards_a = []
            suit = random.randint(0, 2)
            start_num = random.randint(3, 11)

            for num in range(start_num, start_num + 5):
                cards_a.append(bt.Card(suit, num))

            cards_b = []
            start_num = random.randint(3, 11)

            if suit + 1 == 3:
                suit = 3
            else:
                suit = random.randint(suit + 1, 3)

            for num in range(start_num, start_num + 5):
                cards_b.append(bt.Card(suit, num))

            self.assertTrue(bt.is_bigger(cards_a, cards_b))

    def test_bigger_four_of_a_kind(self):
        for i in range(num_tests):
            cards_a = []
            cards_b = []
            nums = list(range(3, 15))
            four_num = random.choice(nums)
            nums.remove(four_num)
            extra_num = random.choice(nums)

            for suit in range(0, 4):
                cards_a.append(bt.Card(suit, four_num))
            cards_a.append(bt.Card(random.randint(0, 3), extra_num))

            if four_num + 1 == 15:
                four_num = 15
            else:
                nums = list(range(four_num + 1, 16))
                four_num = random.choice(nums)
                nums.remove(four_num)
            extra_num = random.choice(nums)

            for suit in range(0, 4):
                cards_b.append(bt.Card(suit, four_num))
            cards_b.append(bt.Card(random.randint(0, 3), extra_num))

            self.assertTrue(bt.is_bigger(cards_a, cards_b))

    def test_bigger_full_house(self):
        for i in range(num_tests):
            cards_a = []
            cards_b = []
            nums = list(range(3, 15))
            three_num = random.choice(nums)
            nums.remove(three_num)
            two_num = random.choice(nums)

            for suit in random.sample(range(0, 4), 3):
                cards_a.append(bt.Card(suit, three_num))

            for suit in random.sample(range(0, 4), 2):
                cards_a.append(bt.Card(suit, two_num))

            if three_num + 1 == 15:
                three_num = 15
            else:
                nums = list(range(three_num + 1, 16))
                three_num = random.choice(nums)
                nums.remove(three_num)
            two_num = random.choice(nums)

            for suit in random.sample(range(0, 4), 3):
                cards_b.append(bt.Card(suit, three_num))

            for suit in random.sample(range(0, 4), 2):
                cards_b.append(bt.Card(suit, two_num))

            self.assertTrue(bt.is_bigger(cards_a, cards_b))

    #
    def test_bigger_flush(self):
        for i in range(num_tests):
            cards_a = []
            suit = random.randint(0, 2)
            nums = random.sample(range(3, 16), 5)

            while sorted(nums) == list(range(min(nums), max(nums) + 1)) or sorted(nums) == [3, 4, 5, 14, 15] or \
                    sorted(nums) == [3, 4, 5, 6, 15]:
                nums = random.sample(range(3, 16), 5)

            for num in nums:
                cards_a.append(bt.Card(suit, num))

            if suit + 1 == 3:
                suit = 3
            else:
                suit = random.randint(suit + 1, 3)

            cards_b = []
            nums = random.sample(range(3, 16), 5)

            while sorted(nums) == list(range(min(nums), max(nums) + 1)) or sorted(nums) == [3, 4, 5, 14, 15] or \
                    sorted(nums) == [3, 4, 5, 6, 15]:
                nums = random.sample(range(3, 16), 5)

            for num in nums:
                cards_b.append(bt.Card(suit, num))

            self.assertTrue(bt.is_bigger(cards_a, cards_b))

    def test_bigger_straight(self):
        for i in range(num_tests):
            cards_a = []
            start_num = random.randint(3, 10)
            cards_a.append(bt.Card(0, start_num))

            for num in range(start_num + 1, start_num + 5):
                cards_a.append(bt.Card(random.randint(1, 3), num))

            if start_num + 1 == 11:
                start_num = 11
            else:
                start_num = random.randint(start_num + 1, 11)

            cards_b = [bt.Card(0, start_num)]

            for num in range(start_num + 1, start_num + 5):
                cards_b.append(bt.Card(random.randint(1, 3), num))

            self.assertTrue(bt.is_bigger(cards_a, cards_b))

    def test_bigger_three_of_a_kind(self):
        for i in range(num_tests):
            cards_a = []
            cards_b = []
            num = random.randint(3, 14)

            for suit in random.sample(range(0, 4), 3):
                cards_a.append(bt.Card(suit, num))

            if num + 1 == 15:
                num = 15
            else:
                num = random.randint(num + 1, 15)

            for suit in random.sample(range(0, 4), 3):
                cards_b.append(bt.Card(suit, num))

            self.assertTrue(bt.is_bigger(cards_a, cards_b))

    def test_bigger_pair(self):
        for i in range(num_tests):
            cards_a = []
            cards_b = []
            num = random.randint(3, 14)

            for suit in random.sample(range(0, 4), 2):
                cards_a.append(bt.Card(suit, num))

            if num + 1 == 15:
                num = 15
            else:
                num = random.randint(num + 1, 15)

            for suit in random.sample(range(0, 4), 2):
                cards_b.append(bt.Card(suit, num))

            self.assertTrue(bt.is_bigger(cards_a, cards_b))

    def test_bigger_single(self):
        for i in range(num_tests):
            num = random.randint(3, 14)
            cards_a = [bt.Card(random.randint(0, 3), num)]

            if num + 1 == 15:
                num = 15
            else:
                num = random.randint(num + 1, 15)

            cards_b = [bt.Card(random.randint(0, 3), num)]

            self.assertTrue(bt.is_bigger(cards_a, cards_b))


if __name__ == '__main__':
    unittest.main()
