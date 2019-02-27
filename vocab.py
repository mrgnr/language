import csv
import getpass
import os
from pathlib import Path, PurePath

import tinycards


def strip_adjective(s, endings=['e', 'en', 'er', 'es', 'em']):
    for ending in endings:
        if s.endswith(ending):
            return s[:-len(ending)]
    return s


class Word:
    _NORMALIZERS = {
        'adjective': strip_adjective
    }

    def __init__(self, word, definition=None, pos=None, wordtrie=None):
        self.word = word
        self.definition = definition
        self.pos = pos if pos is not None else []
        self.wordtrie = wordtrie

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

    def normalize(self, wordtrie=None):
        wordtrie = wordtrie if wordtrie else self.wordtrie

        if not wordtrie:
            raise ValueError('A WordTrie must be given!')

        prefixes, _ = wordtrie.search(self.word)

        # Get functions to attempt to normalize the word, using part-of-speech
        # as a hint if available
        normalizers = []
        for pos in self.pos:
            if pos in self._NORMALIZERS:
              normalizers.append(self._NORMALIZERS[pos])
        else:
            normalizers = self._NORMALIZERS.values()

        # Attempt to normalize the word until a match is found in the wordtrie
        for normalizer in normalizers:
            normalized = normalizer(self.word)
            if normalized in prefixes:
                return normalized

        # Give up -- no normalization could be done
        return self.word

    def __gt__(self, other):
        return self.word > other.word

    def __str__(self):
        return self.word

class WordTrie:
    def __init__(self, words):
        self._data = self._prefix_groups(words)

    def search(self, word):
        prefixes, subtree, _ = self._search(word, 0, self._data)
        return prefixes, subtree

    def _search(self, word, i_start, data):
        subtree = None
        i_end = i_start
        prefixes = []

        for i in range(i_start, len(word) + 1):
            prefix = word[:i]
            #print(prefix)
            if prefix in data:
                # Add prefixes here!
                #print('\tFound bitches!: {}'.format(prefix))
                prefixes, sub, end = self._search(word, i_start, data[prefix])
                if prefix != word:
                    prefixes.append(prefix)
                #sub = self._search(word, 0, data[prefix])
                if sub is not None:
                    subtree = sub
                    i_end = end
                else:
                    subtree = data[prefix]
                    i_end = i

        #print('DONE {} / {}'.format(i_end, len(word)))
        if i_end < len(word):
            return prefixes, None, i_end
        else:
            return prefixes, subtree, i_end

    def _prefix_groups(self, words):
        prefix = None
        groups = dict()
        current_group = []

        for word in words:
            # On the first word, just set it as the prefix and move on
            if prefix is None:
                prefix = word
                continue

            if is_prefix(prefix, word):
                current_group.append(word)
            else:
                # We've encountered a new prefix, so save the current group
                groups[prefix] = current_group
                current_group = []
                prefix = word

        # Dont forget to save the current group when we run out of words!
        if prefix:
            groups[prefix] = current_group

        # Recurse on longer prefixes
        for new_prefix, new_words in groups.items():
            new_groups = self._prefix_groups(new_words)
            if new_groups:
                groups[new_prefix] = new_groups
            else:
                groups[new_prefix] = {word: {} for word in new_words}

        return groups

    def __contains__(self, word):
        return self._contains(word, 0, self._data)
        #_, subtree = self.search(word)
        #return subtree is not None

    def _contains(self, word, i_start, data):
        if word in data:
            return True

        for i in range(i_start, len(word) + 1):
            prefix = word[:i]
            if prefix in data and self._contains(word, i, data[prefix]):
                return True

        return False


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




def normalize_adjective(s, adjectives=None, endings=['e', 'en', 'er', 'es', 'em']):
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


def read_file_lines(path, ignore=None, transform=None):
    ignore = ignore if ignore else lambda x: False
    transform = transform if transform else lambda x: x

    with open(path, 'r') as f:
        for line in f:
            if ignore(line):
                continue
            yield transform(line)


def wordtrie_from_file(path, ignore=None, transform=None):
    file_lines = read_file_lines(path, ignore=ignore, transform=transform)
    return WordTrie(file_lines)

def parse_words(lines, stripchars=None, sep=None):
    import string
    if stripchars is None:
        stripchars = string.whitespace + string.punctuation + string.digits + '«»'

    for line in lines:
        #for word in line.lower().split(sep):
        for word in line.split(sep):
            word = word.strip(stripchars)
            if len(word) > 0:
                yield word


if __name__ == '__main__':
    ignore = lambda x: x == x.upper() or len(x.strip()) < 2
    transform = lambda x: x.strip()
    hh = wordtrie_from_file('/usr/share/dict/ngerman', ignore=ignore, transform=transform)

    print(hh.search('gute'))

    #client = tinycards_login()
    #save_all_to_csv(client)
    #cards = get_tinycards(client)
    #cards = sorted(cards, key=tinycard_sort_key)
