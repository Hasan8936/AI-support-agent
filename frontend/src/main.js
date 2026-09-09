const output = document.getElementById('output');
const messageInput = document.getElementById('message');
const runButton = document.getElementById('run');
const sampleButton = document.getElementById('sample');

const examples = [
    'My package is late and I need an update.',
    'I was charged twice and need a refund.',
    'Someone used my account without permission. This is a fraud issue.',
    'My item arrived damaged and I need support.'
];

function renderLoading() {
    output.innerHTML = `
    <div class="card result-card">
      <h3>Running analysis</h3>
      <p>Evaluating intent, retrieving similar precedents, and deciding whether the message should be auto-handled.</p>
    </div>
  `;
}

function renderError(message) {
    output.innerHTML = `
    <div class="card result-card">
      <div class="error">${message}</div>
    </div>
  `;
}

function renderResult(data) {
    const decisionClass = data.decision === 'auto_handle' ? 'auto' : 'escalate';
    const precedents = (data.precedents || []).map((item) => `
    <li>
      <div>${item.customer_msg}</div>
      <span class="similarity">Similarity: ${item.similarity}</span>
    </li>
  `).join('');

    output.innerHTML = `
    <article class="result-card">
      <h3>Intent</h3>
      <div class="metric-row">
        <span class="value">${data.intent}</span>
        <span class="pill ${decisionClass}">${data.decision}</span>
      </div>
      <div class="metric-row">
        <span>Confidence</span>
        <span class="value">${data.confidence}</span>
      </div>
      <div class="metric-row">
        <span>Reason</span>
        <span>${data.reason}</span>
      </div>
    </article>

    <article class="result-card">
      <h3>Precedents</h3>
      <ul class="precedent-list">${precedents}</ul>
    </article>

    <article class="result-card">
      <h3>Draft reply</h3>
      <p>${data.draft_reply}</p>
    </article>
  `;
}

async function runAgent() {
    const message = messageInput.value.trim();
    if (!message) {
        renderError('Please enter a customer message before running the agent.');
        return;
    }

    renderLoading();

    try {
        const response = await fetch('http://localhost:8000/api/agent/run', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message, brand: 'AmazonHelp' })
        });

        if (!response.ok) {
            throw new Error(`API request failed with status ${response.status}`);
        }

        const data = await response.json();
        renderResult(data);
    } catch (error) {
        renderError(`The demo could not connect to the backend. Make sure the API is running on localhost:8000. ${error.message}`);
    }
}

function loadExample() {
    const nextText = examples[Math.floor(Math.random() * examples.length)];
    messageInput.value = nextText;
}

runButton.addEventListener('click', runAgent);
sampleButton.addEventListener('click', loadExample);