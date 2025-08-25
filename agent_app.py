import os
import requests
from flask import Flask, request, jsonify, render_template
from notion_client import Client
import sys

# Append the current directory to the Python path to allow local imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agent_core import run_agent_executor
from agent_tools import load_api_keys_and_clients

# Initialize the Flask application
app = Flask(__name__)

# --- Global variables for Notion and keys ---
notion: Client = None
NOTION_DATABASE_ID = "20d26c2f146480a782afedbbb797cfb2"  # NOTE: This is hardcoded from your original file.

# Load keys and clients on app startup
try:
    notion = load_api_keys_and_clients()
except Exception as e:
    print(f"Error initializing: {e}", file=sys.stderr)
    sys.exit(1)


@app.route('/')
def home():
    """Renders a simple HTML interface for the user."""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AI Agent</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
            body { font-family: 'Inter', sans-serif; }
        </style>
    </head>
    <body class="bg-gray-100 min-h-screen flex items-center justify-center p-4">
        <div class="bg-white p-8 rounded-xl shadow-lg w-full max-w-2xl">
            <h1 class="text-3xl font-bold text-center text-gray-800 mb-6">AI Agent</h1>
            <div class="space-y-4">
                <input type="text" id="queryInput" placeholder="Enter your query..." class="w-full px-4 py-3 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all duration-200">
                <button onclick="runAgent()" class="w-full bg-indigo-600 text-white font-semibold py-3 rounded-lg hover:bg-indigo-700 transition-all duration-200">Run Agent</button>
            </div>
            <div id="loadingIndicator" class="text-center mt-6 hidden">
                <div class="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-indigo-500 mx-auto"></div>
                <p class="mt-2 text-gray-600">Thinking...</p>
            </div>
            <div id="responseContainer" class="mt-6 p-4 bg-gray-50 border border-gray-200 rounded-lg">
                <h2 class="text-xl font-semibold text-gray-700 mb-2">Response:</h2>
                <pre id="responseOutput" class="whitespace-pre-wrap text-gray-800 font-normal leading-relaxed"></pre>
                <div class="mt-4">
                    <button id="showThoughtsBtn" class="bg-gray-200 text-gray-700 font-medium py-2 px-4 rounded-lg hover:bg-gray-300 transition-all duration-200 hidden">Show Agent Thoughts</button>
                </div>
            </div>
            <div id="thoughtsContainer" class="mt-4 p-4 bg-gray-50 border border-gray-200 rounded-lg hidden">
                <h2 class="text-xl font-semibold text-gray-700 mb-2">Agent Thoughts:</h2>
                <pre id="thoughtsOutput" class="whitespace-pre-wrap text-gray-800 font-normal leading-relaxed text-sm"></pre>
            </div>
        </div>
        <script>
            let agentThoughts = '';

            async function runAgent() {
                const query = document.getElementById('queryInput').value;
                if (!query.trim()) {
                    alert('Please enter a query.');
                    return;
                }
                const loadingIndicator = document.getElementById('loadingIndicator');
                const responseOutput = document.getElementById('responseOutput');
                const showThoughtsBtn = document.getElementById('showThoughtsBtn');
                const thoughtsContainer = document.getElementById('thoughtsContainer');

                loadingIndicator.classList.remove('hidden');
                responseOutput.textContent = '';
                thoughtsContainer.classList.add('hidden');
                showThoughtsBtn.classList.add('hidden');

                try {
                    const response = await fetch('/run-agent', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ query: query }),
                    });

                    const data = await response.json();

                    if (response.ok) {
                        responseOutput.textContent = data.answer;
                        agentThoughts = data.thoughts;
                        showThoughtsBtn.classList.remove('hidden');
                    } else {
                        responseOutput.textContent = 'Error: ' + (data.error || 'An unknown error occurred.');
                        showThoughtsBtn.classList.add('hidden');
                    }
                } catch (error) {
                    responseOutput.textContent = 'Failed to connect to the server: ' + error.message;
                    showThoughtsBtn.classList.add('hidden');
                } finally {
                    loadingIndicator.classList.add('hidden');
                }
            }

            document.getElementById('showThoughtsBtn').addEventListener('click', () => {
                const thoughtsContainer = document.getElementById('thoughtsContainer');
                const thoughtsOutput = document.getElementById('thoughtsOutput');
                thoughtsOutput.textContent = agentThoughts;
                thoughtsContainer.classList.toggle('hidden');
            });
        </script>
    </body>
    </html>
    """


@app.route('/run-agent', methods=['POST'])
def run_agent_api():
    """Receives a user query and runs the full agent."""
    data = request.get_json()
    user_query = data.get('query')
    if not user_query:
        return jsonify({'error': 'Query not provided'}), 400

    try:
        final_answer, agent_thoughts = run_agent_executor(user_query, NOTION_DATABASE_ID)
        return jsonify({'answer': final_answer, 'thoughts': agent_thoughts})

    except Exception as e:
        print(f"Error during agent invocation: {e}", file=sys.stderr)
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
