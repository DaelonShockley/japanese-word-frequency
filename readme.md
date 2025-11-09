# Japanese Word Frequency Analysis

## Overview
This project analyzes the relative frequency of words in Japanese subtitle transcripts in order to produce a list of words most overrepresented in the transcripts relative to spoken Japanese as a whole. Tokenization is done via SudachiPy, only verbs, adjectives, and nouns are considered when determining overrepresentation. The code attempts to exclude proper nouns (as character names are often the most overrepresented words in a given series), but this is not perfect. Additionally, only the 1/3 most used words will be considered, and the word must appear at least an average of twice per transcript. This is done to avoid rare words gaining highly inflated representation values, and keeps the list to relevant words. Word frequencies are compared to the [tublex](https://github.com/naist-nlp/tubelex?tab=readme-ov-file) Japanese frequency list, which was designed to best approximate the frequency of words in spoken Japanese by analyzing Japanese language YouTube videos. For further details about tublex, please read the paper published by it's creators [here](https://aclanthology.org/2025.coling-main.641/). At the time of writing, all transcripts have been sourced from [kitsunekko.net](https://kitsunekko.net/dirlist.php?dir=subtitles%2Fjapanese%2FOne_Piece%2F).

## Usage
For those simply interested in viewing the list of overrepresented words for a given series, click the folder named after said series and open overrepresented_words.txt. Here you will find a list of words in the format "word: overrepresentation", sorted by the most overrepresented at the top. The number for overrepresentation represents the magnitude in which a word is overrepresented in a given series compared to the tublex frequency list. For example, in Bocchi the Rock Season 1 the word あした (meaning tomorrow) is used 236.64 times more frequently than in typical spoken Japanese. As a result, the words entry in overrepresented_words.txt is "あした: 236.64". 

For those interested in using the code to generate an overrepresented words list for their own transcripts, you must first clone the repository and create a subfolder named after the series. Within that subfolder, create another subfolder called "Transcripts", and place your transcripts in this folder. **Please note that only .srt files are supported at this time**. After this you can run the following. FolderName is a required flag, without it the script will not run. 

```python DetermineOverrepresentation.py FolderName```

Once the script runs, overrepresented_words.txt will be created in the relevant folder. 

## Purpose and Contributing
The intention of this project is to help language learners study the words which are most unique and relevant to a given series. It is my belief that studying these words prior to watching the series as comprehensible input will improve the watchers ability to pick up on the usage, connotation, and general context for of this words when they appear in the series. At this time only Japanese is supported, but if there's enough interest, I may expand the project to support other languages as well. Additionally, the focus of the project is currently on anime, but I would love to eventually expand to other forms of content. Contributions are welcome! If you have a quality set of transcripts which you would like to be added to the project, you can submit a PR with the transcripts in a properly named folder, or if you're not familiar with submitting PRs send a message to my email daelonshockley@gmail.com or dshocc on discord. For contributions to the code, you can submit a PR, create an issue, or message me with information about a bug. 

## Ideas for the Future
I would like to eventually implement the following
1. Support for other file types and types of content
2. Implement other languages
3. Automatically define overrepresented words, create flashcards, or provide other educational material for each word

If you have ideas for other features you think would be helpful, or improvements that can be made, I'd love to hear about them! 

