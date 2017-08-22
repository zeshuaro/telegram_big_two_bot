#!/usr/bin/env python3

import pydealer


class Player:
    def __init__(self, player_tele_id, player_name, player_id):
        self.player_tele_id = player_tele_id
        self.player_name = player_name
        self.player_ID = player_id
        self.cards = pydealer.Stack()
