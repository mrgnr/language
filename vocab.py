import csv
import getpass
import os
from pathlib import Path, PurePath

import tinycards


class Word:
    def __init__(self, word, definition=None, pos=None):
        self.word = word
        self.definition = definition
        self.pos = pos if pos is not None else []

    def update_pos(self):
        from wiktionaryparser import WiktionaryParser
        parser = WiktionaryParser()
        parser.set_default_language('german')
        result = parser.fetch(self.word)
        self.pos = [definition['partOfSpeech']
                    for entry in result
                    for definition in entry['definitions']]

    def is_noun(self):
        return 'noun' in self.pos

    def is_verb(self):
        return 'verb' in self.pos

    def is_adjective(self):
        return 'adjective' in self.pos

    def is_adverb(self):
        return 'adverb' in self.pos

    def is_preposition(self):
        return 'preposition' in self.pos

    def normalize(self):
        pass

    def __gt__(self, other):
        return self.word > other.word


def tinycards_login():
    username = os.environ.get('TINYCARDS_IDENTIFIER')
    if not username:
        print("Username:")
        username = input()

    password = os.environ.get('TINYCARDS_PASSWORD')
    if not password:
        password = getpass.getpass()


    return tinycards.Tinycards(username, password)


def save_cards_to_csv(cards, csv_file='cards'):
    front_column = 'front'
    back_column = 'back'
    pos_column = 'partOfSpeech'
    save_dir = os.environ.get('TINYCARDS_DATADIR')
    if not save_dir:
        save_dir = Path.cwd()

    p = PurePath.joinpath(save_dir, csv_file + '.csv')
    with open(str(p), 'w') as f:
        csv_writer = csv.DictWriter(f, fieldnames=[front_column, back_column, pos_column])

        print('Saving cards to "{}"...'.format(p))
        for card in cards:
            front_word = card.front.concepts[0].fact.text
            back_word = card.back.concepts[0].fact.text
            stripped = strip_article(front_word)

            print('{} ({})'.format(front_word, stripped))
            pos = part_of_speech(stripped)

            csv_writer.writerow({front_column: front_word,
                                 back_column: back_word,
                                 pos_column: "; ".join(pos)})


def save_all_to_csv(client):
    save_dir = os.environ.get('TINYCARDS_DATADIR')
    if not save_dir:
        save_dir = Path.cwd()

    for deck in client.get_decks():
        p = PurePath.joinpath(save_dir, deck.title + '.csv')

        print('Saving deck "{}" to "{}"...'.format(deck.title, p))
        with open(str(p), 'w') as f:
            deck.save_cards_to_csv(f, front_column='', back_column='')


def get_tinycards(client=None):
    if client is None:
        client = tinycards_login()

    return [card
            for deck in client.get_decks()
            for card in deck.cards]

def get_words(tinycards):
    return [Word(card.front.concepts[0].fact.text,
                 card.back.concepts[0].fact.text)
            for card in tinycards]


def strip_article(s, articles=['der', 'das', 'die', 'the']):
    for article in articles:
        stripped = s.replace(article + ' ', '', 1)
        if stripped != s: break
    return stripped.strip()


def strip_adjective(s, endings=['e', 'en', 'er', 'es']):
    for ending in endings:
        if s.endswith(ending):
            return s[:-len(ending)]
    return s


def normalize_adjective(s, adjectives=None, endings=['e', 'en', 'er', 'es']):
    for ending in endings:
        if s.endswith(ending) and s[:-len(ending)] in adjectives:
            return s[:-len(ending)]
    return s


def is_prefix(s, other):
    return other.startswith(s)


def part_of_speech(s):
    from wiktionaryparser import WiktionaryParser
    parser = WiktionaryParser()
    parser.set_default_language('german')
    word = parser.fetch(s)
    return [definition['partOfSpeech'] for entry in word for definition in entry['definitions']]

def tinycard_sort_key(tinycard):
    return strip_article(tinycard.front.concepts[0].fact.text).lower()

def prefix_groups(words):
    prefix = None
    groups = dict()
    current_group = []

    for word in words:
        # Filter out abbreviations and single letters
        if len(word) < 2 or word == word.upper():
            continue

        # First valid word
        if prefix is None:
            prefix = word
            continue

        if is_prefix(prefix, word):
            current_group.append(word)
        else:
            if len(current_group):
                groups[prefix] = current_group
                current_group = []
            prefix = word

    return groups


def read_file_lines(path):
    with open(path, 'r') as f:
        while True:
            line = f.readline().strip()
            if not line:
                break
            yield line

def prefix_groups_from_file(path):
    file_lines = read_file_lines(path)
    return prefix_groups(file_lines)


if __name__ == '__main__':

    client = tinycards_login()
    #save_all_to_csv(client)
    cards = get_tinycards(client)
    cards = sorted(cards, key=tinycard_sort_key)
