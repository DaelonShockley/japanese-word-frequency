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

"""
Takes sentence as input and tokenizes via SudachiPy to return nouns, verbs, and adjectives. 
Proper nouns are attempted to be excluded but this doesn't always work, especially with names
appearing in katakana.
"""
def extract_content_words(text: str):
    tokens = tokenizer_obj.tokenize(text, mode)
    content_words = []
    total_tokens = len(tokens)

    for t in tokens:
        pos = t.part_of_speech()  
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

"""
Takes a list of words and updates the global word counter.
"""
def update_word_counter(words):
    global word_counter
    for w in words:
        word_counter[w] += 1

"""
Reads an SRT file and returns a list of cleaned Japanese subtitle lines.
Each caption (which may span multiple lines) becomes one sentence.
"""
def extract_sentences_from_srt(filepath: str):
    """
    Reads an SRT file and returns a list of cleaned Japanese subtitle lines.
    Each caption (which may span multiple lines) becomes one sentence.
    """
    sentences = []
    current_caption = []

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            # If this is a timestamp or index, it's the end of a caption block
            if not line or re.match(r"^\d+$", line) or "-->" in line:
                if current_caption:
                    sentence = " ".join(current_caption).strip()
                    if sentence:
                        sentences.append(sentence)
                    current_caption = []
                continue

            # Remove full-width and half-width parentheses and their contents
            line = re.sub(r"[（(].*?[）)]", "", line)
            line = line.strip()

            if line:
                current_caption.append(line)

    # Catch any remaining lines after the loop
    if current_caption:
        sentence = " ".join(current_caption).strip()
        if sentence:
            sentences.append(sentence)

    return sentences

"""
Prints the top 'num' most frequent words in the global word_counter,
along with their counts.
"""
def print_top_words(num: int):
    top_words = word_counter.most_common(num)
    print(f"Top {num} words:")
    for word, count in top_words:
        print(f"{word}: {count}")

"""
Reads the TSV file and returns a dictionary mapping
column 1 values to their frequency.
Assumes the TSV has a 'frequency' column as the last column.
"""
def load_frequencies(tsv_file):
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

"""
Searches freq_dict to find the frequency of a word. Returns 0 if word not found
"""
def get_frequency(word, freq_dict):
    return freq_dict.get(word, 0.0)

"""
Processes all subtitle (.srt) files in the folder represented by folder_path, identifying overrepresented words compared to
ja_frequency_list_clean.tsv, outputs overrepresented_words.txt in the folder_path folder.
"""
def process_folder(folder_path):
    global total_words
    transcript_path = folder_path + "/Transcripts"
    file_count = 0

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
        if count < 2*file_count:
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

    """
    Entry point for the Japanese subtitle word frequency analysis script.

    This section handles command-line execution, allowing the script to process:
      1. A single specified folder containing subtitle transcripts, or
      2. All eligible show folders within the project directory (when the 'all' argument is used).

    Command-line Arguments:
        folder (str):
            - Path to the folder containing an individual show's "Transcripts" directory.
            - Alternatively, specify 'all' to process every subfolder in the project root
              that contains a "Transcripts" subdirectory.

    Behavior:
        - When a single folder is specified:
            The script calls `process_folder()` directly on that folder.

        - When 'all' is specified:
            The script automatically detects all subfolders in the base directory that contain
            a "Transcripts" folder. Each folder is processed independently, with fresh word
            counters initialized for each run to ensure isolated results.

    Example Usage:
        $ python DetermineOverrepresentation.py BocchiTheRockS1
        $ python DetermineOverrepresentation.py all
    """
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze Japanese subtitle word frequencies.")
    parser.add_argument(
        "folder",
        help="Path to the folder containing SRT files, or 'all' to process every show folder in the project directory",
    )
    args = parser.parse_args()

    base_dir = os.path.dirname(os.path.abspath(__file__))

    if args.folder.lower() == "all":
        # Look for all subfolders that contain a "Transcripts" folder
        subfolders = [
            os.path.join(base_dir, d)
            for d in os.listdir(base_dir)
            if os.path.isdir(os.path.join(base_dir, d))
            and os.path.isdir(os.path.join(base_dir, d, "Transcripts"))
        ]

        print(f"Processing all {len(subfolders)} folders under {base_dir}...\n")
        for folder_path in subfolders:
            print(f"Processing {os.path.basename(folder_path)}")
            total_words = 0
            word_counter = Counter()
            try:
                process_folder(folder_path)
            except Exception as e:
                print(f"Error processing {folder_path}: {e}")
        print("\nFinished all folders.")
    else:
        # Run for a single specified folder
        folder_path = args.folder
        process_folder(folder_path)


