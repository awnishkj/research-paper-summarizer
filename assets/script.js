// Client state management
let activePaperId = null;
let chatMessages = [];
let generalChatMessages = [
    { role: 'assistant', content: '👋 Hello! I am your general research helper. You can ask me general questions, clarify scientific terms, or outline study topics before loading a paper.' }
];
let summariesCache = {
    executive: null,
    structured: null,
    concepts: null
};
let activeChatId = null;

// Configure marked options
marked.setOptions({
    gfm: true,
    breaks: true
});

// DOM Elements
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const apiWarningBanner = document.getElementById('api-warning-banner');
const apiStatusBadge = document.getElementById('api-status-badge');

const blankState = document.getElementById('blank-state');
const loadingState = document.getElementById('loading-state');
const loadingTitle = document.getElementById('loading-title');
const loadingSubtitle = document.getElementById('loading-subtitle');
const loadingProgress = document.getElementById('loading-progress');
const dashboardView = document.getElementById('dashboard-view');

const paperMetadataCard = document.getElementById('paper-metadata-card');
const metaTitle = document.getElementById('meta-title');
const metaAuthor = document.getElementById('meta-author');
const metaSubject = document.getElementById('meta-subject');
const metaPages = document.getElementById('meta-pages');
const resetBtn = document.getElementById('reset-btn');

const activePaperTitle = document.getElementById('active-paper-title');
const tabButtons = document.querySelectorAll('.tab-btn');
const summaryContent = document.getElementById('summary-content');
const tabSkeleton = document.getElementById('tab-skeleton');

const chatMessagesContainer = document.getElementById('chat-messages');
const chatForm = document.getElementById('chat-form');
const chatInput = document.getElementById('chat-input');
const chatSendBtn = document.getElementById('chat-send-btn');
const historyCard = document.getElementById('history-card');
const historyList = document.getElementById('history-list');
const suggestionContainer = document.getElementById('suggestion-container');
const suggestionChips = document.querySelectorAll('.suggestion-chip');

// General Chat Elements (Welcome Page)
const generalChatMessagesContainer = document.getElementById('general-chat-messages');
const generalChatForm = document.getElementById('general-chat-form');
const generalChatInput = document.getElementById('general-chat-input');
const newChatBtn = document.getElementById('new-chat-btn');
const chatHistoryCard = document.getElementById('chat-history-card');
const chatHistoryList = document.getElementById('chat-history-list');

// Initialize Lucide Icons
lucide.createIcons();

// Check API Health Status on page load
checkApiHealth();

// ==========================================================================
// Event Listeners Setup
// ==========================================================================

// Drag & Drop event handlers
['dragenter', 'dragover'].forEach(eventName => {
    dropZone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropZone.classList.add('dragging');
    }, false);
});

['dragleave', 'drop'].forEach(eventName => {
    dropZone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropZone.classList.remove('dragging');
    }, false);
});

dropZone.addEventListener('drop', (e) => {
    const dt = e.dataTransfer;
    const files = dt.files;
    if (files.length > 0) {
        handleFileUpload(files[0]);
    }
});

fileInput.addEventListener('change', (e) => {
    if (fileInput.files.length > 0) {
        handleFileUpload(fileInput.files[0]);
    }
});

// Reset application to load another paper
resetBtn.addEventListener('click', resetApp);
newChatBtn.addEventListener('click', resetApp);

// Tab switching handlers
tabButtons.forEach(button => {
    button.addEventListener('click', () => {
        const tabName = button.getAttribute('data-tab');
        switchTab(tabName);
    });
});

// Chat form submission handler
chatForm.addEventListener('submit', (e) => {
    e.preventDefault();
    handleChatSubmit();
});

// Pressing Enter in chat input (without Shift) sends message
chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        chatForm.requestSubmit();
    }
});

// Auto-expand textarea height as user types
chatInput.addEventListener('input', () => {
    chatInput.style.height = 'auto';
    chatInput.style.height = (chatInput.scrollHeight - 6) + 'px';
});

// Suggestion chip action handlers
suggestionChips.forEach(chip => {
    chip.addEventListener('click', () => {
        const questionText = chip.getAttribute('data-question');
        if (questionText && !chatInput.disabled) {
            chatInput.value = questionText;
            chatInput.focus();
            chatInput.style.height = (chatInput.scrollHeight - 6) + 'px';
        }
    });
});

// General Chat Event Handlers (Welcome Page)
generalChatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const question = generalChatInput.value.trim();
    if (!question) return;
    
    // Hide upper elements and make chat card take full height on first message
    const blankIllustration = document.querySelector('.blank-illustration');
    const blankDescription = document.querySelector('.blank-description');
    const generalChatCard = document.getElementById('general-chat-card');
    
    if (blankIllustration && !blankIllustration.classList.contains('hidden')) {
        blankIllustration.classList.add('hidden');
        if (blankDescription) blankDescription.classList.add('hidden');
        if (dropZone) dropZone.classList.add('hidden');
        if (blankState) blankState.classList.add('chat-focused');
        if (generalChatCard) generalChatCard.classList.add('chat-focused');
    }

    // Clear input & auto-resize textarea
    generalChatInput.value = '';
    generalChatInput.style.height = 'auto';
    
    // Append user message
    appendGeneralMessage('user', question);
    generalChatMessages.push({ role: 'user', content: question });
    
    // Append loader
    const thinkingBubble = appendGeneralThinkingMessage();
    
    try {
        const response = await fetch('/api/chat/general', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ chat_id: activeChatId, messages: generalChatMessages })
        });
        
        if (!response.ok) throw new Error("General chat request failed.");
        const data = await response.json();
        
        activeChatId = data.chat_id;
        
        // Remove loader and append reply
        thinkingBubble.remove();
        appendGeneralMessage('assistant', data.response);
        generalChatMessages.push({ role: 'assistant', content: data.response });
        
        // Refresh sidebar general chats list
        await updateChatHistoryList();
        
    } catch (err) {
        thinkingBubble.remove();
        appendGeneralMessage('assistant', `❌ Error: ${err.message}`);
    }
});

generalChatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        generalChatForm.requestSubmit();
    }
});

generalChatInput.addEventListener('input', () => {
    generalChatInput.style.height = 'auto';
    generalChatInput.style.height = (generalChatInput.scrollHeight - 6) + 'px';
});

// ==========================================================================
// Core Logical Functions
// ==========================================================================

/**
 * Verifies backend API connection and status of Gemini API Key.
 */
async function checkApiHealth() {
    try {
        const response = await fetch('/api/health');
        if (!response.ok) throw new Error("Failed health query.");
        const data = await response.json();
        
        if (data.api_configured) {
            apiStatusBadge.className = "status-badge online";
            apiStatusBadge.innerHTML = '<span class="status-dot"></span> Online';
            apiWarningBanner.classList.add('hidden');
        } else {
            apiStatusBadge.className = "status-badge offline";
            apiStatusBadge.innerHTML = '<span class="status-dot"></span> API Missing';
            apiWarningBanner.classList.remove('hidden');
        }
    } catch (err) {
        console.error("API Health error: ", err);
        apiStatusBadge.className = "status-badge offline";
        apiStatusBadge.innerHTML = '<span class="status-dot"></span> Offline';
    }
}

/**
 * Submits PDF file to server, starts parsing, and displays output.
 */
async function handleFileUpload(file) {
    if (!file || file.type !== 'application/pdf') {
        alert("Please select a valid PDF file.");
        return;
    }
    
    // Switch views to processing/loading state
    blankState.classList.add('hidden');
    loadingState.classList.remove('hidden');
    updateLoadingProgress(10, "Uploading PDF", "Transferring document to session workspace...");
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const errData = await response.json();
            throw new Error(errData.detail || "PDF processing failed.");
        }
        
        const data = await response.json();
        updateLoadingProgress(70, "Generating Summary", "Analyzing paper concepts using Gemini...");
        
        // Save paper state
        activePaperId = data.paper_id;
        summariesCache = {
            executive: data.initial_summary,
            structured: null,
            concepts: null
        };
        
        // Render document details
        renderMetadata(data.metadata, data.paper_id);
        
        // Set active paper titles
        activePaperTitle.textContent = data.metadata.title;
        activePaperTitle.title = data.metadata.title;

        // Render default summary
        summaryContent.innerHTML = marked.parse(data.initial_summary);
        
        // Setup initial Chat pane state
        resetChatWithPaper(data.metadata.title);
        
        // Update session history list
        await updateHistoryList();
        
        // Transition views
        loadingState.classList.add('hidden');
        dashboardView.classList.remove('hidden');
        paperMetadataCard.classList.remove('hidden');
        suggestionContainer.classList.remove('hidden');
        
    } catch (err) {
        console.error("Upload error: ", err);
        alert(`Error processing paper: ${err.message}`);
        loadingState.classList.add('hidden');
        blankState.classList.remove('hidden');
    }
}

/**
 * Swaps selected summaries view tab.
 */
async function switchTab(tabName) {
    if (!activePaperId) return;
    
    // De-activate all tabs and activate selected one
    tabButtons.forEach(btn => {
        if (btn.getAttribute('data-tab') === tabName) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });
    
    // Check if summary is already cached and is not an error string
    if (summariesCache[tabName] && !summariesCache[tabName].startsWith('Error during summary generation:')) {
        summaryContent.classList.remove('hidden');
        tabSkeleton.classList.add('hidden');
        summaryContent.innerHTML = marked.parse(summariesCache[tabName]);
        return;
    }
    
    // Fetch and generate summary dynamically
    summaryContent.classList.add('hidden');
    tabSkeleton.classList.remove('hidden');
    
    try {
        const summary = await fetchSummary(activePaperId, tabName);
        summariesCache[tabName] = summary;
        
        summaryContent.innerHTML = marked.parse(summary);
        summaryContent.classList.remove('hidden');
        tabSkeleton.classList.add('hidden');
    } catch (err) {
        summaryContent.innerHTML = `<p style="color: var(--accent-red)">Failed to load summary: ${err.message}</p>`;
        summaryContent.classList.remove('hidden');
        tabSkeleton.classList.add('hidden');
    }
}

/**
 * Fetches summary content from FastAPI backend.
 */
async function fetchSummary(paperId, summaryType) {
    const response = await fetch(`/api/summary/${paperId}/${summaryType}`);
    if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || "Failed to load summary.");
    }
    const data = await response.json();
    return data.summary;
}

/**
 * Sends a message from the paper grounded chat input.
 */
async function handleChatSubmit() {
    const question = chatInput.value.trim();
    if (!question || !activePaperId) return;
    
    // Clear input box
    chatInput.value = '';
    chatInput.style.height = 'auto';
    
    // Append user query to UI and history
    appendChatMessage('user', question);
    chatMessages.push({ role: 'user', content: question });
    
    // Append loading spinner
    const thinkingBubble = appendChatThinkingMessage();
    
    try {
        const response = await fetch(`/api/chat/${activePaperId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ messages: chatMessages })
        });
        
        if (!response.ok) {
            const errData = await response.json();
            throw new Error(errData.detail || "No response received.");
        }
        
        const data = await response.json();
        
        // Remove loading state and append answer
        thinkingBubble.remove();
        appendChatMessage('assistant', data.response);
        chatMessages.push({ role: 'assistant', content: data.response });
        
    } catch (err) {
        console.error("Chat error: ", err);
        thinkingBubble.remove();
        appendChatMessage('system', `❌ Error: ${err.message}`);
    }
}

// ==========================================================================
// User Interface Helper Operations
// ==========================================================================

/**
 * Fills metadata items with document properties.
 */
function renderMetadata(metadata, paperId) {
    metaTitle.textContent = metadata.title || "Untitled Document";
    metaAuthor.textContent = metadata.author || "Unknown";
    metaSubject.textContent = metadata.subject || "Not Specified";
    metaPages.textContent = metadata.pages_count || "N/A";
}

/**
 * Resets chat inputs with document name.
 */
function resetChatWithPaper(title) {
    chatMessages = [];
    chatInput.disabled = false;
    chatInput.placeholder = "Ask a question about this paper...";
    chatSendBtn.disabled = false;
    chatMessagesContainer.innerHTML = '';
    
    appendChatMessage('system', `👋 Hello! I am your research advisor. I have loaded **"${title}"** into my memory. Ask me specific questions about its equations, datasets, conclusions, or limits.`);
}

/**
 * Appends a message bubble inside the grounded Paper chat window.
 */
function appendChatMessage(role, content) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}-message`;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.innerHTML = marked.parse(content);
    
    messageDiv.appendChild(contentDiv);
    chatMessagesContainer.appendChild(messageDiv);
    chatMessagesContainer.scrollTop = chatMessagesContainer.scrollHeight;
    
    return messageDiv;
}

/**
 * Appends a loading spinner bubble inside the grounded Paper chat window.
 */
function appendChatThinkingMessage() {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant-message';
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.innerHTML = `
        <div class="thinking-indicator">
            <div class="thinking-dot"></div>
            <div class="thinking-dot"></div>
            <div class="thinking-dot"></div>
        </div>
    `;
    
    messageDiv.appendChild(contentDiv);
    chatMessagesContainer.appendChild(messageDiv);
    chatMessagesContainer.scrollTop = chatMessagesContainer.scrollHeight;
    
    return messageDiv;
}

/**
 * Appends a message to the welcome page general chat screen.
 */
function appendGeneralMessage(role, content) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}-message`;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    if (role === 'system') {
        contentDiv.textContent = content;
    } else {
        contentDiv.innerHTML = marked.parse(content);
    }
    
    messageDiv.appendChild(contentDiv);
    generalChatMessagesContainer.appendChild(messageDiv);
    generalChatMessagesContainer.scrollTop = generalChatMessagesContainer.scrollHeight;
    return messageDiv;
}

/**
 * Appends a thinking indicator to the welcome page general chat screen.
 */
function appendGeneralThinkingMessage() {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant-message thinking';
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.innerHTML = `
        <div class="thinking-indicator">
            <div class="thinking-dot"></div>
            <div class="thinking-dot"></div>
            <div class="thinking-dot"></div>
        </div>
    `;
    
    messageDiv.appendChild(contentDiv);
    generalChatMessagesContainer.appendChild(messageDiv);
    generalChatMessagesContainer.scrollTop = generalChatMessagesContainer.scrollHeight;
    
    return messageDiv;
}

/**
 * Updates indicators inside the loading screen.
 */
function updateLoadingProgress(value, title, subtitle) {
    loadingProgress.style.width = `${value}%`;
    if (title) loadingTitle.textContent = title;
    if (subtitle) loadingSubtitle.textContent = subtitle;
}

/**
 * Resets application state to welcome page.
 */
function loadWelcomeChat() {
    const blankIllustration = document.querySelector('.blank-illustration');
    const blankDescription = document.querySelector('.blank-description');
    const generalChatCard = document.getElementById('general-chat-card');
    
    // Always show welcome elements and keep chat in default height on startup/refresh
    if (blankIllustration) blankIllustration.classList.remove('hidden');
    if (blankDescription) blankDescription.classList.remove('hidden');
    if (dropZone) dropZone.classList.remove('hidden');
    if (blankState) blankState.classList.remove('chat-focused');
    if (generalChatCard) generalChatCard.classList.remove('chat-focused');

    // Default welcome state
    generalChatMessages = [
        { role: 'assistant', content: '👋 Hello! I am your general research helper. You can ask me general questions, clarify scientific terms, or outline study topics before loading a paper.' }
    ];
    generalChatMessagesContainer.innerHTML = '';
    appendGeneralMessage('assistant', generalChatMessages[0].content);
}

function resetApp() {
    activePaperId = null;
    activeChatId = null;
    chatMessages = [];
    summariesCache = {
        executive: null,
        structured: null,
        concepts: null
    };

    loadWelcomeChat();

    // Reset layout views
    paperMetadataCard.classList.add('hidden');
    dashboardView.classList.add('hidden');
    suggestionContainer.classList.add('hidden');
    blankState.classList.remove('hidden');

    // Reset tab state
    tabButtons.forEach(btn => {
        if (btn.getAttribute('data-tab') === 'executive') {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });

    // Reset Chat panel
    chatInput.disabled = true;
    chatInput.placeholder = "Upload a paper to start chatting...";
    chatSendBtn.disabled = true;
    chatMessagesContainer.innerHTML = '';
    appendMessage('system', `👋 Hello! I am your research advisor. Upload a research paper, and I can help answer specific questions, explain complex math, locate datasets, or elaborate on their results.`);

    // Refresh history representation
    updateHistoryList();
    updateChatHistoryList();

    // Clear file inputs
    fileInput.value = '';
}

/**
 * Helper to match old resets interface signature.
 */
function appendMessage(role, content) {
    return appendChatMessage(role, content);
}

/**
 * Fetches and renders the list of general assistant chat sessions in the left sidebar.
 */
async function updateChatHistoryList() {
    try {
        const response = await fetch('/api/chats/general');
        if (!response.ok) throw new Error("Failed to load general chat history.");
        const chats = await response.json();
        
        chatHistoryList.innerHTML = '';
        
        if (!chats || chats.length === 0) {
            chatHistoryList.innerHTML = '<div class="history-placeholder">No recent chats</div>';
            return;
        }
        
        chats.forEach(chat => {
            const item = document.createElement('div');
            item.className = `history-item ${chat.chat_id === activeChatId ? 'active' : ''}`;
            item.innerHTML = `
                <i data-lucide="message-square"></i>
                <span class="history-item-title" title="${chat.title}">${chat.title}</span>
            `;
            
            item.addEventListener('click', () => {
                if (chat.chat_id !== activeChatId) {
                    loadGeneralChatSession(chat.chat_id);
                }
            });
            
            chatHistoryList.appendChild(item);
        });
        
        lucide.createIcons({
            nodeList: chatHistoryList.querySelectorAll('[data-lucide]')
        });
    } catch (err) {
        console.error("Error updating chat history list:", err);
    }
}

/**
 * Loads a saved general assistant chat session.
 */
async function loadGeneralChatSession(chatId) {
    activePaperId = null;
    activeChatId = chatId;
    
    blankState.classList.remove('hidden');
    paperMetadataCard.classList.add('hidden');
    dashboardView.classList.add('hidden');
    suggestionContainer.classList.add('hidden');
    
    // Hide welcome elements and expand chat card
    const blankIllustration = document.querySelector('.blank-illustration');
    const blankDescription = document.querySelector('.blank-description');
    const generalChatCard = document.getElementById('general-chat-card');
    
    if (blankIllustration) blankIllustration.classList.add('hidden');
    if (blankDescription) blankDescription.classList.add('hidden');
    if (dropZone) dropZone.classList.add('hidden');
    if (blankState) blankState.classList.add('chat-focused');
    if (generalChatCard) generalChatCard.classList.add('chat-focused');
    
    try {
        const response = await fetch(`/api/chat/general/${chatId}`);
        if (!response.ok) throw new Error("Failed to load general chat session.");
        const data = await response.json();
        
        generalChatMessages = data.messages || [];
        generalChatMessagesContainer.innerHTML = '';
        
        generalChatMessages.forEach(msg => {
            appendGeneralMessage(msg.role, msg.content);
        });
        
        await updateChatHistoryList();
        await updateHistoryList();
    } catch (err) {
        console.error("Error loading chat session:", err);
        alert(`Error loading chat: ${err.message}`);
        resetApp();
    }
}

/**
 * Fetches and renders the list of uploaded papers in the active session.
 */
async function updateHistoryList() {
    try {
        const response = await fetch('/api/papers');
        if (!response.ok) throw new Error("Failed to load history list.");
        const papers = await response.json();
        
        // Always keep the history section visible to fill sidebar space
        historyCard.classList.remove('hidden');
        historyList.innerHTML = '';
        
        if (!papers || papers.length === 0) {
            historyList.innerHTML = '<div class="history-placeholder">No recent documents</div>';
            return;
        }
        
        papers.forEach(paper => {
            const item = document.createElement('div');
            item.className = `history-item ${paper.paper_id === activePaperId ? 'active' : ''}`;
            item.innerHTML = `
                <i data-lucide="file-text"></i>
                <span class="history-item-title" title="${paper.title}">${paper.title}</span>
            `;
            
            item.addEventListener('click', () => {
                if (paper.paper_id !== activePaperId) {
                    loadPaper(paper.paper_id);
                }
            });
            
            historyList.appendChild(item);
        });
        
        // Initialize Lucide Icons for dynamic elements
        lucide.createIcons({
            nodeList: historyList.querySelectorAll('[data-lucide]')
        });
        
    } catch (err) {
        console.error("Error updating history: ", err);
    }
}

/**
 * Loads a specific paper from the session into active state.
 */
async function loadPaper(paperId) {
    blankState.classList.add('hidden');
    dashboardView.classList.add('hidden');
    loadingState.classList.remove('hidden');
    
    updateLoadingProgress(30, "Switching Document", "Loading details from active session...");
    
    try {
        const response = await fetch(`/api/paper/${paperId}`);
        if (!response.ok) throw new Error("Failed to load paper details.");
        const data = await response.json();
        
        // Update client state
        activePaperId = data.paper_id;
        summariesCache = data.summaries;
        
        // Render document details
        renderMetadata(data.metadata, data.paper_id);
        
        // Set active paper titles
        activePaperTitle.textContent = data.metadata.title;
        activePaperTitle.title = data.metadata.title;
        
        // Find currently active tab
        let activeTabName = 'executive';
        tabButtons.forEach(btn => {
            if (btn.classList.contains('active')) {
                activeTabName = btn.getAttribute('data-tab');
            }
        });
        
        // Render or switch tabs
        if (summariesCache[activeTabName]) {
            summaryContent.innerHTML = marked.parse(summariesCache[activeTabName]);
        } else {
            await switchTab(activeTabName);
        }
        
        // Restore Chat history
        chatMessages = data.chat_history || [];
        chatMessagesContainer.innerHTML = '';
        
        // Always append the greeting first for context
        appendChatMessage('system', `👋 Hello! I am your research advisor. I have loaded **"${data.metadata.title}"** into my memory. Ask me specific questions about its equations, datasets, conclusions, or limits.`);
        
        chatInput.disabled = false;
        chatInput.placeholder = "Ask a question about this paper...";
        chatSendBtn.disabled = false;
        suggestionContainer.classList.remove('hidden');
        
        if (chatMessages.length > 0) {
            chatMessages.forEach(msg => {
                appendChatMessage(msg.role, msg.content);
            });
        }
        
        // Update history selection list UI
        await updateHistoryList();
        
        // Transition views
        loadingState.classList.add('hidden');
        dashboardView.classList.remove('hidden');
        paperMetadataCard.classList.remove('hidden');
        suggestionContainer.classList.remove('hidden');
        
    } catch (err) {
        console.error("Switch error: ", err);
        activePaperId = null;
        loadingState.classList.add('hidden');
        blankState.classList.remove('hidden');
        loadWelcomeChat();
    }
}

// Perform initial history load on startup
async function initApp() {
    await updateHistoryList();
    await updateChatHistoryList();
    loadWelcomeChat();
}
initApp();
