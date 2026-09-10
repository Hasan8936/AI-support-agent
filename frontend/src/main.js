const output = document.getElementById('output');
const messageInput = document.getElementById('message');
const runButton = document.getElementById('run');
const sampleButton = document.getElementById('sample');
const apiBaseUrl = (typeof
    import.meta !== 'undefined' &&
    import.meta.env &&
    import.meta.env.VITE_API_URL) || 'http://localhost:8000';

const examples = [
    'My package is late and I need an update.',
    'I was charged twice and need a refund.',
    'Someone used my account without permission. This is a fraud issue.',
    'My item arrived damaged and I need support.'
];

function createTextElement(tagName, text, className) {
    const el = document.createElement(tagName);
    el.textContent = text;
    if (className) el.className = className;
    return el;
}

function renderLoading() {
    output.replaceChildren(createTextElement('div', 'Running analysis...', 'card result-card'));
}

function renderError(message) {
    const card = document.createElement('div');
    card.className = 'card result-card';
    const error = document.createElement('div');
    error.className = 'error';
    error.textContent = message;
    card.appendChild(error);
    output.replaceChildren(card);
}

function renderResult(data) {
    const decisionClass = data.decision === 'auto_handle' ? 'auto' : 'escalate';
    const resultCard = document.createElement('article');
    resultCard.className = 'result-card';

    const intentHeading = createTextElement('h3', 'Intent', '');
    const metricRow = document.createElement('div');
    metricRow.className = 'metric-row';
    metricRow.appendChild(createTextElement('span', data.intent || '', 'value'));
    const pill = createTextElement('span', data.decision || '', `pill ${decisionClass}`);
    metricRow.appendChild(pill);

    const confidenceRow = document.createElement('div');
    confidenceRow.className = 'metric-row';
    confidenceRow.appendChild(createTextElement('span', 'Confidence', ''));
    confidenceRow.appendChild(createTextElement('span', String(data.confidence || ''), 'value'));

    const reasonRow = document.createElement('div');
    reasonRow.className = 'metric-row';
    reasonRow.appendChild(createTextElement('span', 'Reason', ''));
    reasonRow.appendChild(createTextElement('span', data.reason || '', ''));

    resultCard.append(intentHeading, metricRow, confidenceRow, reasonRow);

    const precedentCard = document.createElement('article');
    precedentCard.className = 'result-card';
    const precedentHeading = createTextElement('h3', 'Precedents', '');
    const list = document.createElement('ul');
    list.className = 'precedent-list';
    (data.precedents || []).forEach((item) => {
        const li = document.createElement('li');
        const msg = document.createElement('div');
        msg.textContent = item.customer_msg || '';
        const sim = document.createElement('span');
        sim.className = 'similarity';
        sim.textContent = `Similarity: ${item.similarity}`;
        li.append(msg, sim);
        list.appendChild(li);
    });
    precedentCard.append(precedentHeading, list);

    const replyCard = document.createElement('article');
    replyCard.className = 'result-card';
    replyCard.appendChild(createTextElement('h3', 'Draft reply', ''));
    const draft = document.createElement('p');
    draft.textContent = data.draft_reply || '';
    replyCard.appendChild(draft);

    output.replaceChildren(resultCard, precedentCard, replyCard);
}

async function runAgent() {
    const message = messageInput.value.trim();
    if (!message) {
        renderError('Please enter a customer message before running the agent.');
        return;
    }

    renderLoading();

    try {
        const response = await fetch(`${apiBaseUrl}/api/agent/run`, {
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
        renderError(`The demo could not connect to the backend. Make sure the API is running on ${apiBaseUrl}. ${error.message}`);
    }
}

function loadExample() {
    const nextText = examples[Math.floor(Math.random() * examples.length)];
    messageInput.value = nextText;
}

runButton.addEventListener('click', runAgent);
sampleButton.addEventListener('click', loadExample);