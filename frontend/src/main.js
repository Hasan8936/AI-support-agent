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

// Similarity thresholds for the honest match-strength badge. These are
// deliberately conservative for a TF-IDF/keyword retrieval system: a 0.3
// similarity is not "strong" evidence, even if the intent classifier is
// confident about something else entirely. Keeping this label decoupled
// from intent confidence avoids the two numbers being read as if they
// support each other when they measure different things.
const SIMILARITY_THRESHOLDS = { strong: 0.55, moderate: 0.3 };

function matchStrength(similarity) {
    const value = Number(similarity);
    if (Number.isNaN(value)) return null;
    if (value >= SIMILARITY_THRESHOLDS.strong) return 'strong';
    if (value >= SIMILARITY_THRESHOLDS.moderate) return 'moderate';
    return 'weak';
}

function el(tagName, className, text) {
    const node = document.createElement(tagName);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
}

function renderLoading() {
    const card = el('article', 'result-card');
    card.appendChild(el('div', 'loading-line', 'RUNNING ANALYSIS'));
    output.replaceChildren(card);
}

function renderError(message) {
    const card = el('article', 'result-card');
    card.appendChild(el('div', 'error', message));
    output.replaceChildren(card);
}

function fieldRow(key, value) {
    const row = el('div', 'field-row');
    row.appendChild(el('span', 'field-key', key));
    row.appendChild(el('span', 'field-val', value));
    return row;
}

function renderResult(data) {
    const isAuto = data.decision === 'auto_handle';
    const decisionClass = isAuto ? 'auto' : 'escalate';
    const confidencePct = Math.round((Number(data.confidence) || 0) * 100);

    // --- decision card ---
    const decisionCard = el('article', 'result-card');
    decisionCard.appendChild(el('h3', 'panel-label', 'Routing Decision'));

    const readout = el('div', 'decision-readout');
    readout.appendChild(el('span', `status-light ${decisionClass}`));

    const copy = el('div', 'decision-copy');
    copy.appendChild(el('span', 'decision-intent', data.intent || 'UNKNOWN'));
    copy.appendChild(el('span', `decision-status ${decisionClass}`, isAuto ? 'AUTO-HANDLE' : 'ESCALATE TO HUMAN'));
    readout.appendChild(copy);

    const meter = el('div', 'confidence-meter');
    meter.appendChild(el('span', 'confidence-value', `${confidencePct}%`));
    const bar = el('div', 'meter-bar');
    const fill = el('span');
    fill.style.width = `${Math.min(100, Math.max(0, confidencePct))}%`;
    bar.appendChild(fill);
    meter.appendChild(bar);
    meter.appendChild(el('span', 'meter-caption', 'Intent Confidence'));
    readout.appendChild(meter);

    decisionCard.appendChild(readout);
    decisionCard.appendChild(fieldRow('REASON', data.reason || '—'));

    // --- precedents card ---
    const precedentCard = el('article', 'result-card');
    const precedents = data.precedents || [];
    const topStrength = precedents.length ? matchStrength(precedents[0].similarity) : null;

    const precedentHeading = el('h3', 'panel-label', 'Retrieved Precedents');
    if (topStrength) {
        precedentHeading.appendChild(el('span', `match-strength ${topStrength}`, `${topStrength} match`));
    }
    precedentCard.appendChild(precedentHeading);

    const list = el('ul', 'precedent-list');
    precedents.forEach((item) => {
        const li = el('li');
        li.appendChild(el('div', 'precedent-msg', item.customer_msg || ''));
        const sim = el('span', 'similarity');
        const simValue = Number(item.similarity);
        sim.textContent = 'Similarity: ';
        sim.appendChild(el('span', 'num', Number.isNaN(simValue) ? String(item.similarity) : simValue.toFixed(3)));
        li.appendChild(sim);
        list.appendChild(li);
    });
    if (!precedents.length) {
        list.appendChild(el('li', '', 'No precedents retrieved.'));
    }
    precedentCard.appendChild(list);

    // --- draft reply card ---
    const replyCard = el('article', 'result-card');
    replyCard.appendChild(el('h3', 'panel-label', 'Draft Reply'));
    replyCard.appendChild(el('p', 'draft-reply', data.draft_reply || ''));

    output.replaceChildren(decisionCard, precedentCard, replyCard);
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
