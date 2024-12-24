import requests
from bs4 import BeautifulSoup
import json
import re
from collections import defaultdict

# Base URL for the site
BASE_URL = "https://www.note.co.il/abc/"
LETTERS = ['א', 'ב', 'ג', 'ד', 'ה', 'ו', 'ז', 'ח', 'ט', 'י', 'כ', 'ל', 'מ', 'נ', 'ס', 'ע', 'פ', 'צ', 'ק', 'ר', 'ש', 'ת']  # All Hebrew letters

def fetch_page(url):
    """Fetch the HTML content of a page."""
    response = requests.get(url)
    response.raise_for_status()
    return BeautifulSoup(response.text, 'html.parser')

def clean_answer(answer):
    """Clean and truncate answers to stop at non-letters and include multi-word answers properly."""
    pattern = r'^[\u0590-\u05FF]+(?: [\u0590-\u05FF]+)*'  # Match Hebrew letters and spaces only
    match = re.match(pattern, answer.strip())
    return match.group(0) if match else ""

def process_answer(clean_ans):
    """Extract additional info for an answer."""
    words = clean_ans.split()
    lengths = [len(word) for word in words]
    return {
        "answer": clean_ans,
        "lengths": lengths,
        "num_words": len(words),
        "first_letter": clean_ans[0] if clean_ans else ""
    }

def parse_clue_page(url):
    """Parse a clue's page to extract answers and their details."""
    soup = fetch_page(url)
    answers_by_length = defaultdict(list)

    try:
        # Extract the answer block
        answers_block = soup.find('p', class_='dictionary origin_content')
        if not answers_block:
            return answers_by_length  # No answers found

        for line in answers_block.contents:
            if isinstance(line, str) and 'פתרון' in line:
                parts = line.split(':')
                if len(parts) > 1:
                    raw_answers = [ans.strip() for ans in parts[1].split(',')]
                    for raw_answer in raw_answers:
                        clean_ans = clean_answer(raw_answer)
                        if clean_ans:
                            processed = process_answer(clean_ans)
                            total_length = sum(processed["lengths"])
                            answers_by_length[total_length].append(processed)
    except Exception as e:
        print(f"Error parsing clue page {url}: {e}")

    return answers_by_length

def parse_letter_page(soup):
    """Parse the clues and their links from a letter's page."""
    clues = []
    # Find the main container
    main_div = soup.find('div', class_='twelve columns')
    if not main_div:
        return clues  # No content found

    # Find all articles
    articles = main_div.find_all('article', class_='partial_entry')
    for article in articles:
        title_tag = article.find('h3').find('a')
        if title_tag:
            clue_title = title_tag.get_text(strip=True)
            clue_url = title_tag['href']
            clues.append({"title": clue_title, "url": clue_url})

    return clues

def scrape_letter(letter):
    """Scrape all pages for a given letter."""
    letter_url = f"{BASE_URL}{letter}/"
    page_number = 1
    results = []

    while True:
        print(f"Scraping {letter}, page {page_number}...")
        url = f"{letter_url}page/{page_number}/" if page_number > 1 else letter_url
        soup = fetch_page(url)

        # Parse the current page for clues
        page_clues = parse_letter_page(soup)
        if not page_clues:
            break  # No more content

        # For each clue, fetch the answers
        for clue in page_clues:
            clue_title = clue['title']
            clue_url = clue['url']
            print(f"Scraping clue: {clue_title} ({clue_url})...")
            answers_by_length = parse_clue_page(clue_url)
            results.append({
                "clue": clue_title,
                "answers_by_length": answers_by_length
            })

        # Check for next page
        pagination = soup.find('ul', class_='pagination')
        if pagination:
            next_page = pagination.find('a', class_='next page-numbers')
            if not next_page:
                break
        else:
            break
        page_number += 1

    return results

def scrape_all_letters():
    """Scrape all letters and return the data."""
    all_data = {}
    for letter in LETTERS:
        print(f"Scraping letter: {letter}...")
        all_data[letter] = scrape_letter(letter)
    return all_data

def save_scraped_data(all_data, filename="crossword_solutions.json"):
    """Save the scraped data to a JSON file."""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=4)
    print(f"Data saved to {filename}.")
