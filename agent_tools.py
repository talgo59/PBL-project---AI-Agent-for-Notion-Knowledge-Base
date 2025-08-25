import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import List, Tuple, Dict
from langchain.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from notion_client import Client
import sys
import re

# --- Global variables for Notion and keys ---
notion: Client = None
NOTION_DATABASE_ID = "20d26c2f146480a782afedbbb797cfb2"  # NOTE: This is hardcoded from your original file.


def load_api_keys_and_clients():
    """
    Loads API keys for Gemini and Notion from environment variables or files.
    Initializes the Notion client.
    """
    global notion
    # Load Gemini API Key
    try:
        with open("gemini_API_key.txt", "r") as f:
            os.environ['GOOGLE_API_KEY'] = f.read().strip()
    except FileNotFoundError:
        raise FileNotFoundError("Error: 'gemini_API_key.txt' not found. Ensure your Gemini API key is in this file.")

    # Load Notion API Key
    notion_token = None
    try:
        with open("notion_API_key.txt", "r") as f:
            notion_token = f.read().strip()
    except FileNotFoundError:
        notion_token = os.environ.get("NOTION_TOKEN")

    if not notion_token:
        raise ValueError("CRITICAL ERROR: Notion API token not found.")

    try:
        notion = Client(auth=notion_token)
    except Exception as e:
        raise RuntimeError(f"Error initializing Notion client: {e}")
    return notion


# --- Helper Function for LLM Calls ---
def _get_llm_response_for_tool(prompt_template_string: str, input_variables: dict) -> str:
    """Helper function to get an LLM response with consistent model and temperature settings."""
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.7)
    prompt = PromptTemplate.from_template(prompt_template_string)
    chain = prompt | llm
    response = chain.invoke(input_variables)
    return response.content


# --- Agent Tools (Copied from your original script) ---
def tool_get_relevant_articles_from_homepage(input_string: str) -> str:
    """
    Searches a given homepage URL for articles relevant to provided keywords.
    It scrapes the homepage and immediately filters article links based on keywords
    found in their titles or URLs. This version is more robust, looking for
    titles/text within a broader range of tags (e.g., div) and then finding the
    associated parent or sibling link.

    Input should be a string containing the homepage URL, followed by "|||"
    and then a comma-separated list of keywords.
    Example: "https://www.engadget.com/|||Galaxy Z fold 7,Samsung"

    Returns a newline-separated string of "Title: [article_title] | URL: [article_url]",
    or "No relevant articles found on this homepage." or an error message.
    """
    found_articles = set()

    try:
        parts = input_string.split("|||")
        if len(parts) != 2:
            return "Error: Invalid input format. Expected 'homepage_url|||keyword1,keyword2'."

        homepage_url = parts[0].strip()
        keywords_str = parts[1].strip()
        keywords: List[str] = [k.strip().lower() for k in keywords_str.split(',') if k.strip()]

        if not homepage_url.startswith(('http://', 'https://')):
            homepage_url = 'https://' + homepage_url

        response = requests.get(homepage_url, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # List of tags that commonly contain article titles or snippets
        title_tags = soup.find_all(['h1', 'h2', 'h3', 'div', 'span', 'p', 'a'])

        base_netloc = urlparse(homepage_url).netloc
        unique_links_data = set()

        # New logic to find titles in various tags and then find the parent or sibling link
        for tag in title_tags:
            tag_text = tag.get_text(strip=True)
            if not tag_text:
                continue

            # Check if keywords are in the text content of the tag
            is_relevant_by_keyword = False
            if keywords:
                if any(kw in tag_text.lower() for kw in keywords):
                    is_relevant_by_keyword = True
            else:
                is_relevant_by_keyword = True

            if is_relevant_by_keyword:
                # Look for a parent link tag that contains this element
                parent_a = tag.find_parent('a', href=True)
                href = None

                if parent_a:
                    href = parent_a.get('href')

                # Check for the data-url attribute
                if not href:
                    parent_url_tag = tag.find_parent(attrs={'data-url': True})
                    if parent_url_tag:
                        href = parent_url_tag.get('data-url')

                # Check for the data-destinationlink attribute
                if not href:
                    parent_destination_tag = tag.find_parent(attrs={'data-destinationlink': True})
                    if parent_destination_tag:
                        href = parent_destination_tag.get('data-destinationlink')

                # If the tag itself is a link with an href
                if not href and tag.name == 'a' and tag.get('href'):
                    href = tag.get('href')

                # If a link was found, add it to the set
                if href:
                    title = tag_text
                    unique_links_data.add((title, href))
                else:
                    # If no direct parent link, look for a sibling link
                    next_sibling_a = tag.find_next_sibling('a', href=True)
                    if next_sibling_a:
                        title = tag_text
                        href = next_sibling_a['href']
                        unique_links_data.add((title, href))
                    else:
                        previous_sibling_a = tag.find_previous_sibling('a', href=True)
                        if previous_sibling_a:
                            title = tag_text
                            href = previous_sibling_a['href']
                            unique_links_data.add((title, href))

        # Filter the collected links
        for title, href in unique_links_data:
            if href.startswith('//'):
                href = 'https:' + href
            elif not href.startswith(('http://', 'https://')):
                href = 'https://' + href

            absolute_url = urljoin(homepage_url, href)
            parsed_absolute_url = urlparse(absolute_url)

            # Apply the existing, more robust filters
            if (parsed_absolute_url.netloc == base_netloc or parsed_absolute_url.netloc.endswith(
                    '.' + base_netloc)) and \
                    len(parsed_absolute_url.path) > 5 and \
                    not absolute_url.startswith(('mailto:', '#')) and \
                    not any(kw in absolute_url for kw in
                            ['category', 'tag', 'author', 'login', 'search', 'about', 'contact', 'privacy', '.pdf',
                             '.xml', '.css', '.js']):
                is_article_path = False
                path_lower = parsed_absolute_url.path.lower()
                if any(keyword in path_lower for keyword in
                       ['/news/', '/article/', '/story/', '/blog/', '/post/', '.html', '.php']):
                    is_article_path = True
                if len(path_lower.split('/')) > 2:  # Heuristic for deeper paths
                    is_article_path = True

                if is_article_path:
                    found_articles.add((title, absolute_url))

        if found_articles:
            return "\n".join([f"Title: {title} | URL: {url}" for title, url in list(found_articles)])
        else:
            return "No relevant articles found on this homepage."

    except requests.exceptions.RequestException as e:
        return f"Error fetching homepage {homepage_url}: {e}"
    except Exception as e:
        return f"An unexpected error occurred while processing {homepage_url}: {e}"

def tool_get_urls_from_notion_by_topics(input_string: str) -> str:
    """
    Returns a list of URLs from the Notion database filtered by the provided subjects.
    """
    try:
        if not notion:
            return "Error: Notion client not initialized. Call load_api_keys_and_clients first."
        parts = input_string.split("|||")
        if len(parts) != 2:
            return "Error: Invalid input format. Expected 'DATABASE_ID|||topic1,topic2'."
        database_id = parts[0].strip()
        topics_list_str = parts[1].strip()
        topics_list = [t.strip() for t in topics_list_str.split(',') if t.strip()]
        if not topics_list:
            return "Error: No topics provided for Notion query."
        filters = {
            "or": [
                {
                    "property": "Category",
                    "select": {
                        "equals": topic
                    }
                } for topic in topics_list
            ]
        }
        response = notion.databases.query(
            database_id=database_id,
            filter=filters
        )
        results_urls = []
        for page in response['results']:
            properties = page['properties']
            url_property = properties.get('Website', {}).get('url')
            if url_property:
                results_urls.append(url_property)
        if results_urls:
            return "\n".join(results_urls)
        else:
            return "No URLs found for the specified topics."
    except Exception as e:
        return f"Error fetching URLs from Notion: {e}. Ensure DATABASE_ID is correct and Notion token has access."


def tool_get_article_paragraphs(article_url_string: str) -> str:
    """
    Fetches the content of a given article URL and extracts the title (h1),
    a potential subtitle (h2), and all text from paragraph (<p>) tags within
    the estimated main article body.
    """
    extracted_title1 = "N/A"
    extracted_title2 = "N/A"
    extracted_paragraphs_text = "No content found."
    try:
        article_url = article_url_string.strip()
        response = requests.get(article_url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        title_tag1 = soup.find('h1', class_='mainTitle') or soup.find('span', class_='headline') or soup.find('h1')
        if title_tag1:
            extracted_title1 = title_tag1.get_text(strip=True)
        subtitle_tag = soup.find('span', class_='subTitle') or soup.find('h2')
        if subtitle_tag:
            extracted_title2 = subtitle_tag.get_text(strip=True)
        main_content_div = soup.find('section', itemprop='articleBody') or soup.find('div',
                                                                                     id='find-article-content') or soup.find(
            'div', class_='text_editor_section') or soup.find('div', id='article_content_wrapper') or soup.find('div',
                                                                                                                id='article_text_content') or soup.find(
            'div', class_='article-content') or soup.find('div', class_='entry-content') or soup.find('div',
                                                                                                      class_='post-content') or soup.find(
            'div', class_='story-body') or soup.find('div', class_='main-content-article') or soup.find('div',
                                                                                                        class_='main-article-body') or soup.find(
            'div', class_='text_editor') or soup.find('div', class_='article-body') or soup.find('div',
                                                                                                 class_='story-text') or soup.find(
            'div', class_='item-container') or soup.find('div', class_='article-container') or soup.find('div',
                                                                                                         class_='news_story_content') or soup.find(
            'div', class_='article-text') or soup.find('div', class_='content-wrapper') or soup.find('div',
                                                                                                     class_='col-md-8') or soup.find(
            'div', class_='s-article') or soup.find('div', class_='slot_body_content') or soup.find('div',
                                                                                                    class_='article_general_wrapper') or soup.find(
            'div', id='articleBody') or soup.find('div', id='content') or soup.find('div',
                                                                                    id='mainContent') or soup.find(
            'div', id='story') or soup.find('div', id='main') or soup.find('div',
                                                                           id='paywall_article_parent') or soup.find(
            'div', id='ArticleBodyComponent') or soup.find('section', class_='article-paragraph-wrap') or soup.find(
            'article') or soup.find('main') or soup
        extracted_text = []

        def clean_and_extract_text(tag):
            temp_tag_soup = BeautifulSoup(str(tag), 'html.parser')
            for junk_tag_name in ['script', 'style', 'iframe', 'figure', 'img', 'video', 'audio', 'figcaption',
                                  'noscript']:
                for junk_tag in temp_tag_soup.find_all(junk_tag_name):
                    junk_tag.extract()
            text = temp_tag_soup.get_text(strip=True)
            return text

        if main_content_div:
            content_containers = main_content_div.find_all(['p', 'section', 'div', 'span'])
            for container in content_containers:
                is_valid_paragraph = (container.name == 'p' or 'text_editor_paragraph' in container.get('class',
                                                                                                        []) or 'text_editor_section' in container.get(
                    'class', []) or 'article-body-paragraph' in container.get('class', []) or container.get(
                    'data-text') == 'true')
                if is_valid_paragraph:
                    paragraph_text = clean_and_extract_text(container)
                    if paragraph_text and len(paragraph_text) > 20 and paragraph_text not in extracted_text:
                        extracted_text.append(paragraph_text)
        extracted_paragraphs_text = "\n\n".join(extracted_text) if extracted_text else "No content found."
        return (f"H1 Title: {extracted_title1} ||| H2 Subtitle: {extracted_title2} ||| "
                f"Content: {extracted_paragraphs_text}")
    except requests.exceptions.RequestException as e:
        return f"Error fetching article from {article_url_string}: {e}"
    except Exception as e:
        return f"An unexpected error occurred while processing {article_url_string}: {e}"


def tool_analyze_query_and_map_subjects(input_string: str) -> str:
    """
    Analyzes a user query to extract relevant keywords and map it to subject categories.
    """
    try:
        parts = input_string.split(" ||| ")
        if len(parts) != 2:
            return "Error: Invalid input format. Expected 'user_query ||| types_list'."
        user_query = parts[0].strip()
        available_website_types_str = parts[1].strip()
        available_website_types = [t.strip() for t in available_website_types_str.split(',') if t.strip()]
        if not available_website_types:
            return "Error: No available website types provided in the input."
        prompt_template = """
        Given the user query: "{query}" and the available subject categories: [{types_list}]
        1. Extract the most important keywords or key phrases from the query.
        2. Identify the most relevant subject categories from the provided list.
        Return the results in the exact format: "Keywords: [comma-separated-keywords or None] ||| Subjects: [comma-separated-subjects or None]"
        Please write the category names in lower case.
        """
        types_list_str = ", ".join(available_website_types)
        input_vars = {"query": user_query, "types_list": types_list_str}
        raw_response = _get_llm_response_for_tool(prompt_template, input_vars)
        if "Keywords:" in raw_response and "Subjects:" in raw_response:
            return raw_response
        else:
            return "Keywords: None ||| Subjects: None"
    except Exception as e:
        return f"Error in analyze_query_and_map_subjects tool: {e}"


def tool_answer_question_with_llm_and_urls(input_string: str) -> str:
    """
    Takes the user's question and processed article data, sends it to an LLM
    to generate a short paragraph answer, including relevant URLs.
    """
    try:
        parts = input_string.split("|||", 1)
        if len(parts) != 2:
            return "Error: Invalid input format. Expected 'user_question|||processed_articles_data_string'."
        user_question = parts[0].strip()
        processed_articles_data_str = parts[1].strip()
        if not processed_articles_data_str:
            return "I could not find any relevant information to answer your question from the available articles."
        processed_articles_data: List[Dict[str, str]] = []
        for article_entry_str in processed_articles_data_str.split('\n'):
            if not article_entry_str.strip():
                continue
            article_dict = {}
            kv_pairs = article_entry_str.split(" | ")
            for kv_pair in kv_pairs:
                try:
                    key, value = kv_pair.split(": ", 1)
                    article_dict[key.strip()] = value.strip()
                except ValueError:
                    continue
            if article_dict:
                processed_articles_data.append(article_dict)
        context_parts = []
        for i, article in enumerate(processed_articles_data):
            context_parts.append(f"--- Article {i + 1} ---")
            context_parts.append(f"Title: {article.get('H1 Title', article.get('Original Title', 'N/A'))}")
            context_parts.append(f"URL: {article.get('URL', 'N/A')}")
            context_parts.append("Content:")
            context_parts.append(article.get('Content', 'No content available.'))
            context_parts.append("\n")
        full_context = "\n".join(context_parts)
        prompt_template = """
        Answer the following question based ONLY on the provided context.
        Your answer should be a short paragraph.
        Crucially, include the URLs from the context where you found the information.
        Question: "{question}"
        Context: {context}
        Answer:
        """
        input_vars = {"question": user_question, "context": full_context}
        llm_answer = _get_llm_response_for_tool(prompt_template, input_vars)
        return llm_answer
    except Exception as e:
        return f"An error occurred while generating the answer: {e}"
