from sudachipy import dictionary, tokenizer
from collections import Counter
import re
import os
import csv
import sys
import argparse

csv.field_size_limit(sys.maxsize)

# --- Initialize global tokenizer and counter ---
tokenizer_obj = dictionary.Dictionary().create()
mode = tokenizer.Tokenizer.SplitMode.C
word_counter = Counter()
total_words = 0
total_words_freq_list = 163439781

#--- Arg Parse setup ---
parser = argparse.ArgumentParser(description="Analyze Japanese subtitle word frequencies.")
parser.add_argument("folder", help="Path to the folder containing SRT files")
args = parser.parse_args()

folder_path = args.folder

# --- Function 1: Extract content words (nouns, verbs, adjectives) ---
# def extract_content_words(text: str):
#     """
#     Takes in a Japanese text string and returns a list of nouns, verbs, and adjectives.
#     Verbs are returned in their dictionary form; nouns and adjectives keep their surface form.
#     """
#     tokens = tokenizer_obj.tokenize(text, mode)
#     content_words = []

#     for t in tokens:
#         pos = t.part_of_speech()[0]
#         if pos in ("名詞", "動詞", "形容詞"):
#             if pos == "動詞":
#                 word = t.dictionary_form() or t.normalized_form()
#             else:
#                 word = t.surface()
#             content_words.append(word)

#     return content_words

def extract_content_words(text: str):
    """
    Takes in a Japanese text string and returns a list of nouns, verbs, and adjectives.
    Verbs are returned in their dictionary form; nouns and adjectives keep their surface form.
    Proper nouns (固有名詞) are excluded.
    """
    tokens = tokenizer_obj.tokenize(text, mode)
    content_words = []
    total_tokens = len(tokens)

    for t in tokens:
        pos = t.part_of_speech()  # tuple like ('名詞', '固有名詞', ...)
        main_pos = pos[0]
        sub_pos = pos[1]

        # Include only nouns, verbs, adjectives, and exclude proper nouns
        if main_pos in ("名詞", "動詞", "形容詞") and sub_pos != "固有名詞":
            if main_pos == "動詞":
                word = t.dictionary_form() or t.normalized_form()
            else:
                word = t.surface()
            content_words.append(word)

    return content_words, total_tokens

# --- Function 2: Update global counter ---
def update_word_counter(words):
    """
    Takes a list of words and updates the global word counter.
    """
    global word_counter
    for w in words:
        word_counter[w] += 1

def extract_sentences_from_srt(filepath: str):
    """
    Reads an SRT file and returns a list of cleaned Japanese subtitle lines.
    Example:
        41
        00:01:40,142 --> 00:01:41,519
        （ひとり）あ… ありがとう
    becomes:
        ["あ… ありがとう"]
    """
    sentences = []

    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    buffer = []
    for line in lines:
        line = line.strip()
        # Skip empty lines, subtitle indexes, and timestamps
        if not line or re.match(r"^\d+$", line) or "-->" in line:
            continue

        # Remove full-width and half-width parentheses and their contents
        line = re.sub(r"[（(].*?[）)]", "", line)

        # Remove extra spaces left behind
        line = line.strip()

        if line:
            buffer.append(line)

    # Optionally join multiline subtitles (sometimes one caption has two lines)
    sentences = [" ".join(buffer).strip() for buffer in [buffer]][0].splitlines()
    return buffer

def print_top_words(num: int):
    """
    Prints the top 'num' most frequent words in the global word_counter,
    along with their counts.
    """
    top_words = word_counter.most_common(num)
    print(f"Top {num} words:")
    for word, count in top_words:
        print(f"{word}: {count}")

def load_frequencies(tsv_file):
    """
    Reads the TSV file and returns a dictionary mapping
    column 1 values to their frequency.
    Assumes the TSV has a 'frequency' column as the last column.
    """
    freq_dict = {}
    with open(tsv_file, 'r', newline='', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter='\t')
        header = next(reader)
        freq_idx = len(header) - 1  # frequency is last column
        for row in reader:
            key = row[0]
            try:
                freq = float(row[freq_idx])
            except ValueError:
                freq = 0.0
            freq_dict[key] = freq
    return freq_dict

def get_frequency(word, freq_dict):
    """
    Returns the frequency of a word from the dictionary.
    If the word is not found, returns 0.
    """
    return freq_dict.get(word, 0.0)

# --- Example usage ---
# if __name__ == "__main__":
#     filepath = "BocchiTheRockS1/ぼっち・ざ・ろっく！.S01E01.#1.転がるぼっち.WEBRip.Amazon.ja-jp[sdh].srt"
#     output = extract_sentences_from_srt(filepath)
#     for sentence in output:
#         tokens = extract_content_words(sentence)
#         update_word_counter(tokens)

#     print(word_counter)
if __name__ == "__main__":
    transcript_path = folder_path + "/Transcripts"
    file_count = 0

    # Iterate over all files in the folder
    for filename in os.listdir(transcript_path):
        file_count += 1
        # Only process .srt files
        if filename.endswith(".srt"):
            filepath = os.path.join(transcript_path, filename)
            output = extract_sentences_from_srt(filepath)

            # Process each sentence in the file
            for sentence in output:
                tokens, c = extract_content_words(sentence)
                total_words += c
                update_word_counter(tokens)

    freq_dict = load_frequencies('ja_frequency_list_clean.tsv')

    freq_diff_dict = {}
    for word, count in word_counter.most_common(total_words//3):
        freq = word_counter[word] / total_words
        if word_counter[word] < 2*file_count:
            continue
        nat_freq = get_frequency(word, freq_dict)
        if nat_freq == 0:
            continue
        overrepresentation = freq / nat_freq
        freq_diff_dict[word] = overrepresentation

    sorted_freq_diff = sorted(freq_diff_dict.items(), key=lambda x: x[1], reverse=True)

    # outside results to folder_path/overrepresented_words.txt
    output_file = os.path.join(folder_path, "overrepresented_words.txt")

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"word: overrepresentation\n")
        for word, overrep in sorted_freq_diff:
            f.write(f"{word}: {overrep:.2f}\n")

