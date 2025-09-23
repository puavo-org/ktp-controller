import os.path

with open(
    os.path.join(os.path.dirname(__file__), "words.txt"), "r", encoding="utf-8"
) as words_file:
    WORDS = tuple(line.strip() for line in words_file)
