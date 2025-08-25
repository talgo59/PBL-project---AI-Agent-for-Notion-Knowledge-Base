AI Agent for Notion Knowledge Base

This repository contains the code for an AI Agent designed to answer user queries by leveraging a Notion knowledge base and dynamic web scraping. The agent is built using the LangChain framework and the Google Gemini Flash model to orchestrate a series of specialized tools.

The project consists of a simple Flask web application that provides a user interface to interact with the agent.

Features
Natural Language Query: Users can ask questions in natural language.

Intelligent Tool Use: The AI agent analyzes the query and intelligently decides which tools to use and in what order to find the answer.

Notion Integration: Searches a specified Notion database for relevant website URLs based on a query's subject.

Robust Web Scraping: Scrapes articles from websites found in the Notion database. The scraping logic is designed to be resilient to common variations in website structure.

Content Summarization: Uses a Large Language Model (LLM) to summarize the scraped content and generate a concise answer.

Source Citation: The final answer includes the URLs of the articles used to generate the response.

Agent Transparency: A verbose log of the agent's thought process and tool usage can be viewed directly in the application.

Prerequisites
Before running the application, you need to set up the following:

Python 3.8+

Required Python packages: Install them using pip:

pip install Flask langchain langchain-google-genai notion-client beautifulsoup4 requests

Google Gemini API Key: Obtain an API key from the Google AI Studio.

Notion API Token: Obtain an API integration token from Notion.

Notion Database ID: Create a Notion database and get its ID. The database should have a Multi-select property for Topic and a URL property for URL.

Setup and Configuration
API Keys:

Create a file named gemini_API_key.txt in the project root and paste your Gemini API key inside it.

Create a file named notion_API_key.txt in the project root and paste your Notion API token inside it.

Alternatively, you can set these as environment variables: GOOGLE_API_KEY and NOTION_TOKEN.

Notion Database:

In the agent_app.py and agent_tools.py files, update the NOTION_DATABASE_ID variable with your specific database ID.

NOTION_DATABASE_ID = "YOUR_DATABASE_ID_HERE"

Populate your Notion database with pages. Each page should have a URL and a Topic tag (e.g., "tech", "news", "economy").

Project Structure
agent_app.py: Contains the Flask application, defines the web routes, and handles user interaction. It loads the agent_core and agent_tools modules.

agent_core.py: Initializes the LangChain agent and defines the sequence of tools it can use. This is the "brain" of the application.

agent_tools.py: Contains the individual, specialized functions (tools) that the agent calls. These include:

tool_analyze_query_and_map_subjects: Analyzes a user query and extracts keywords and subjects.

tool_get_urls_from_notion_by_topics: Queries the Notion database for URLs.

tool_get_relevant_articles_from_homepage: Scrapes and filters articles from a given homepage.

tool_get_article_paragraphs: Extracts the main content from a specific article URL.

tool_answer_question_with_llm_and_urls: Uses the collected content to formulate a final answer.

gemini_API_key.txt: Your Gemini API key.

notion_API_key.txt: Your Notion API token.

How to Run the Application
Navigate to the project directory in your terminal.

Run the Flask application:

python agent_app.py

Open your web browser and go to http://127.0.0.1:5000.

Enter your query in the input box and click the "Get Answer" button. The agent's response will appear below. You can also click "Show Agent Thoughts" to see the detailed log of the agent's actions.

Troubleshooting
FileNotFoundError: Ensure gemini_API_key.txt and notion_API_key.txt files exist and contain your keys.

ValueError: CRITICAL ERROR: Notion API token not found.: Check your notion_API_key.txt file and make sure the token is valid.

Web Scraping Issues: If the agent fails to scrape a website, it might be due to a change in the site's HTML structure. The tool_get_relevant_articles_from_homepage function may need to be updated to account for new class names or tags.

API Errors: If the agent fails with an API error, check your API key/token validity and that your Notion database is shared with the integration.
