from sudachipy import dictionary, tokenizer
from collections import Counter
import re
import os
import csv
import sys
import argparse
from jamdict import Jamdict

csv.field_size_limit(sys.maxsize)
jam = Jamdict()

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

    katakana_pattern = re.compile(r"^[\u30A0-\u30FF]+$")
    sfx_pattern = re.compile(r"^([\u30A0-\u30FF]{1,3})\1+$")  # e.g., ワクワク, ドキドキ

    for t in tokens:
        pos = t.part_of_speech()
        main_pos = pos[0]
        sub_pos = pos[1]
        word = t.surface()

        if main_pos not in ("名詞", "動詞", "形容詞"):
            continue
        if sub_pos == "固有名詞":
            continue

        # Normalize verbs
        if main_pos == "動詞":
            word = t.dictionary_form() or t.normalized_form()

        # --- Katakana filtering heuristics ---
        if katakana_pattern.match(word):
            # Remove obvious sound effects
            if sfx_pattern.match(word) or word.endswith("ッ") or word.endswith("ー"):
                continue
            # Likely a name if long and not in frequency list
            if len(word) >= 3 and word not in freq_dict:
                continue

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

freq_dict = load_frequencies('ja_frequency_list_clean.tsv')

"""
Reads words from folder_path/exclude.txt and returns them as a list of strings.
If exclude.txt does not exist, returns an empty list.
Lines starting with '#' or empty lines are ignored.
"""
def load_exclude(folder_path: str):
    exclude_file = os.path.join(folder_path, "exclude.txt")

    if not os.path.exists(exclude_file):
        return []

    with open(exclude_file, "r", encoding="utf-8") as f:
        words = [
            line.strip()
            for line in f
            if line.strip() and not line.strip().startswith("#")
        ]

    return words

"""
Searches freq_dict to find the frequency of a word. Returns 0 if word not found
"""
def get_frequency(word, freq_dict):
    return freq_dict.get(word, 0.0)

def GetWordInformation(word):
    result = jam.lookup(word)

    if not result.entries and not result.chars:
        return ""

    lines = []

    for entry in result.entries:
        # Extract kanji and kana readings
        kanji_list = [k.text for k in entry.kanji_forms] if entry.kanji_forms else []
        kana_list = [k.text for k in entry.kana_forms] if entry.kana_forms else []

        head = []
        if kana_list:
            head.append(", ".join(kana_list))
        if kanji_list:
            head.append(", ".join(kanji_list))

        header = " / ".join(head) if head else word
        lines.append(f"• {header}")

        # Glosses and part-of-speech per sense
        if entry.senses:
            for idx, sense in enumerate(entry.senses, 1):
                pos_str = ", ".join(sense.pos) if sense.pos else ""
                gloss_texts = [g.text for g in sense.gloss] if sense.gloss else []
                gloss = "; ".join(gloss_texts)
                line = f"    {idx}. {gloss}"
                if pos_str:
                    line += f" ({pos_str})"
                lines.append(line)

        lines.append("")  # spacer between entries

    # Character info (kanji breakdown)
    if result.chars:
        lines.append("Kanji components:")
        for ch in result.chars:
            # Safely handle ch.meanings
            meanings = []
            if hasattr(ch, "meanings") and ch.meanings:
                if isinstance(ch.meanings, str):
                    meanings = [ch.meanings]
                elif isinstance(ch.meanings, (list, tuple)):
                    # Make sure all items are strings
                    meanings = [str(m) for m in ch.meanings]
            grade = getattr(ch, "grade", "?")
            lines.append(f"    {ch.literal} — {'; '.join(meanings)}; grade {grade}")

    return "\n".join(lines).strip()


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

    exclude = load_exclude(folder_path)
    exclude = set(exclude)

    freq_diff_dict = {}
    if not exclude:
        for word, count in word_counter.most_common(total_words//3):
            freq = count / total_words
            if count < 2*file_count:
                continue
            nat_freq = get_frequency(word, freq_dict)
            if nat_freq == 0:
                continue
            overrepresentation = freq / nat_freq
            freq_diff_dict[word] = overrepresentation
    else:
        for word, count in word_counter.most_common(total_words//3):
            freq = count / total_words
            if count < 2*file_count:
                continue
            if word in exclude:
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

    output_file = os.path.join(folder_path, "overrepresented_words_information.txt")
    count = 1
    with open(output_file, "w", encoding="utf-8") as f:
        for word, overrep in sorted_freq_diff:
            f.write(f"{count}. {word} ({overrep:.2f}x standard frequency)\n\n")
            info = GetWordInformation(word)
            if info: 
                f.write(info)
                f.write("\n\n")
                count += 1
            else: 
                f.write("Sorry! We are unable to provide information about this word at this time. ")
                f.write("\n\n")
                count += 1 

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


