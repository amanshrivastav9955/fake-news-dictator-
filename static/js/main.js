// ==========================================================================
// VERIFACT CLIENT CONTROLLER
// ==========================================================================

document.addEventListener('DOMContentLoaded', function() {
    
    // --- 1. THEME INITIALIZATION & TOGGLE ---
    const htmlElement = document.documentElement;
    const themeToggleBtn = document.getElementById('themeToggle');
    const currentTheme = localStorage.getItem('theme') || 'dark';
    
    htmlElement.setAttribute('data-theme', currentTheme);
    
    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', function() {
            const activeTheme = htmlElement.getAttribute('data-theme');
            const newTheme = activeTheme === 'dark' ? 'light' : 'dark';
            
            htmlElement.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
        });
    }

    // --- 2. MOBILE NAVIGATION DRAWER ---
    const mobileNavToggle = document.getElementById('mobileNavToggle');
    const navMenu = document.getElementById('navMenu');
    
    if (mobileNavToggle && navMenu) {
        mobileNavToggle.addEventListener('click', function() {
            navMenu.classList.toggle('open');
            const icon = mobileNavToggle.querySelector('i');
            if (navMenu.classList.contains('open')) {
                icon.classList.replace('fa-bars', 'fa-xmark');
            } else {
                icon.classList.replace('fa-xmark', 'fa-bars');
            }
        });
    }

    // --- 3. DRAG & DROP FILE READER ---
    const dropzone = document.getElementById('fileDropzone');
    const fileInput = document.getElementById('fileInput');
    const newsTitleInput = document.getElementById('newsTitle');
    const newsTextInput = document.getElementById('newsText');
    const fileNameIndicator = document.getElementById('fileNameIndicator');
    
    if (dropzone && fileInput) {
        // Clicking dropzone opens file dialog
        dropzone.addEventListener('click', () => fileInput.click());
        
        // Drag events
        ['dragenter', 'dragover'].forEach(eventName => {
            dropzone.addEventListener(eventName, (e) => {
                e.preventDefault();
                dropzone.classList.add('dragover');
            }, false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            dropzone.addEventListener(eventName, (e) => {
                e.preventDefault();
                dropzone.classList.remove('dragover');
            }, false);
        });
        
        // Drop file event
        dropzone.addEventListener('drop', (e) => {
            const dt = e.dataTransfer;
            const files = dt.files;
            if (files.length) {
                handleUploadedFile(files[0]);
            }
        });
        
        // Selected file event
        fileInput.addEventListener('change', (e) => {
            if (fileInput.files.length) {
                handleUploadedFile(fileInput.files[0]);
            }
        });
    }

    function handleUploadedFile(file) {
        if (file.type !== 'text/plain' && !file.name.endsWith('.txt')) {
            alert('Please upload a valid plain text file (.txt).');
            return;
        }
        
        fileNameIndicator.textContent = `Attached: ${file.name}`;
        
        const reader = new FileReader();
        reader.onload = function(e) {
            const textContent = e.target.result;
            
            // Clean up title and body
            // Let's assume the first non-empty line is the Title, rest is Body.
            const lines = textContent.split(/\r?\n/).map(l => l.trim()).filter(l => l.length > 0);
            
            if (lines.length > 0) {
                // Set first line as Title if not already set, or overwrite it
                newsTitleInput.value = lines[0];
                
                // Rest of the lines are the main text body
                newsTextInput.value = lines.slice(1).join('\n\n');
            } else {
                newsTextInput.value = textContent;
            }
        };
        
        reader.readAsText(file);
    }

    // --- 4. PREDICTION FORM SUBMISSION ---
    const predictionForm = document.getElementById('predictionForm');
    const submitBtn = document.getElementById('submitBtn');
    const clearBtn = document.getElementById('clearBtn');
    const resultCard = document.getElementById('resultCard');
    
    if (predictionForm) {
        predictionForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const title = newsTitleInput.value.trim();
            const text = newsTextInput.value.trim();
            
            if (!title && !text) {
                alert('Please enter a headline and content to analyze.');
                return;
            }
            
            // UI Loading state
            submitBtn.disabled = true;
            const origHTML = submitBtn.innerHTML;
            submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Analyzing News...';
            
            const formData = new FormData();
            formData.append('title', title);
            formData.append('text', text);
            formData.append('source', fileInput.files.length > 0 ? 'file' : 'manual');
            
            fetch('/predict', {
                method: 'POST',
                body: formData
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Prediction request failed.');
                }
                return response.json();
            })
            .then(data => {
                // Restore button
                submitBtn.disabled = false;
                submitBtn.innerHTML = origHTML;
                
                // Show Result card
                resultCard.classList.remove('hidden');
                
                // Render verdict badge
                const verdictBadge = document.getElementById('verdictBadge');
                const verdictDesc = document.getElementById('verdictDesc');
                
                verdictBadge.textContent = data.final_prediction;
                
                if (data.final_prediction === 'REAL') {
                    verdictBadge.className = 'verdict-badge real animate-fade-in';
                    verdictDesc.textContent = 'This news article shows high credibility alignment with verified reports.';
                } else {
                    verdictBadge.className = 'verdict-badge fake animate-fade-in';
                    verdictDesc.textContent = 'Caution: This article exhibits structural and text pattern features typical of fake news.';
                }
                
                // Render Passive Aggressive Classifier details
                updateModelUI('pac', data.pac_pred, data.pac_conf);
                // Render Logistic Regression details
                updateModelUI('lr', data.lr_pred, data.lr_conf);
                // Render Naive Bayes details
                updateModelUI('nb', data.nb_pred, data.nb_conf);
                
                // Update download report button
                const downloadBtn = document.getElementById('downloadReportBtn');
                downloadBtn.href = `/download_report/${data.pred_id}`;
                
                // --- DYNAMIC AI CONVERSATIONAL INTEGRATION HOOK ---
                let explainBtn = document.getElementById('explainAIBtn');
                if (!explainBtn) {
                    const resultActions = document.querySelector('.result-actions');
                    if (resultActions) {
                        explainBtn = document.createElement('button');
                        explainBtn.id = 'explainAIBtn';
                        explainBtn.className = 'btn btn-primary w-100 text-center';
                        explainBtn.style.marginTop = '10px';
                        explainBtn.style.background = 'var(--accent-gradient)';
                        explainBtn.innerHTML = '<i class="fa-solid fa-brain"></i> Generate Detailed AI Analysis Report';
                        resultActions.appendChild(explainBtn);
                    }
                }
                
                if (explainBtn) {
                    explainBtn.onclick = function(e) {
                        e.preventDefault();
                        // Open Chat Window
                        chatbotWindow.classList.add('open');
                        chatbotInput.focus();
                        
                        // Fire specialized LLM detailed report
                        sendAIDeepAnalysis(title, text);
                    };
                }
                
                // Scroll to results
                resultCard.scrollIntoView({ behavior: 'smooth' });
            })
            .catch(error => {
                console.error(error);
                submitBtn.disabled = false;
                submitBtn.innerHTML = origHTML;
                alert('An error occurred during classification. Ensure train.py has been run and models exist.');
            });
        });
    }
    
    function updateModelUI(prefix, pred, conf) {
        const label = document.getElementById(`${prefix}Label`);
        const bar = document.getElementById(`${prefix}Bar`);
        const confText = document.getElementById(`${prefix}Conf`);
        
        label.textContent = `${pred} (${conf}%)`;
        label.className = `model-prediction-label ${pred.toLowerCase()}`;
        
        bar.style.width = `${conf}%`;
        if (pred === 'REAL') {
            bar.className = 'progress-bar-fill success';
        } else {
            bar.className = 'progress-bar-fill danger';
        }
        
        confText.textContent = `${conf}%`;
    }
    
    // Clear Fields handler
    if (clearBtn) {
        clearBtn.addEventListener('click', function() {
            predictionForm.reset();
            fileNameIndicator.textContent = '';
            fileInput.value = '';
            resultCard.classList.add('hidden');
        });
    }

    // --- 5. UPGRADED CONVERSATIONAL AI CHATBOT INTERFACE (v2.5) ---
    const chatbotContainer = document.getElementById('chatbotContainer');
    const chatbotToggle = document.getElementById('chatbotToggle');
    const chatbotWindow = document.getElementById('chatbotWindow');
    const chatbotClose = document.getElementById('chatbotClose');
    const chatbotInput = document.getElementById('chatbotInput');
    const chatbotSend = document.getElementById('chatbotSend');
    const chatbotMessages = document.getElementById('chatbotMessages');
    const suggestionChips = document.querySelectorAll('.suggestion-chip');
    
    // Upgraded control references
    const chatbotHistoryToggle = document.getElementById('chatbotHistoryToggle');
    const chatbotHistorySidebar = document.getElementById('chatbotHistorySidebar');
    const newThreadBtn = document.getElementById('newThreadBtn');
    
    let chatThreads = [];
    let activeThread = null;
    
    // A. Initialize chat threads history
    function initThreads() {
        const stored = localStorage.getItem('verifact_chat_threads');
        if (stored) {
            try {
                chatThreads = JSON.parse(stored);
            } catch (e) {
                chatThreads = [];
            }
        }
        
        if (chatThreads.length === 0) {
            startNewThread();
        } else {
            activeThread = chatThreads[0];
            loadThreadMessages(activeThread);
        }
        renderHistorySidebar();
    }
    
    function startNewThread() {
        const id = 'thread_' + Date.now();
        const newT = {
            id: id,
            title: 'New Investigation ' + new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            messages: []
        };
        chatThreads.unshift(newT);
        activeThread = newT;
        saveThreadsToStorage();
        renderHistorySidebar();
        
        // Reset messages to welcome card
        chatbotMessages.innerHTML = `
            <div class="chat-message bot">
                🛡️ **Greetings, Investigator.** I am **VERIFACT AI**, your real-time conversational media verification and cyber-intelligence assistant.
                
                Submit any claim, news text, or URL to begin. I can help you:
                * **Explain** why an article is flagged as fake
                * **Spot** structural clickbait or bias
                * **Analyze** emotional manipulation & propaganda patterns
                * **Suggest** trusted fact-checking references
            </div>
        `;
    }
    
    function saveThreadsToStorage() {
        localStorage.setItem('verifact_chat_threads', JSON.stringify(chatThreads));
    }
    
    function loadThreadMessages(thread) {
        chatbotMessages.innerHTML = '';
        if (thread.messages.length === 0) {
            chatbotMessages.innerHTML = `
                <div class="chat-message bot">
                    🛡️ **Greetings, Investigator.** I am **VERIFACT AI**, your real-time conversational media verification and cyber-intelligence assistant.
                    
                    Submit any claim, news text, or URL to begin. I can help you:
                    * **Explain** why an article is flagged as fake
                    * **Spot** structural clickbait or bias
                    * **Analyze** emotional manipulation & propaganda patterns
                    * **Suggest** trusted fact-checking references
                </div>
            `;
            return;
        }
        
        thread.messages.forEach(msg => {
            if (msg.role === 'user') {
                appendChatBubble(msg.content, 'user');
            } else {
                appendChatBubble(marked.parse(msg.content), 'bot');
            }
        });
        chatbotMessages.scrollTop = chatbotMessages.scrollHeight;
    }
    
    function renderHistorySidebar() {
        const listContainer = document.getElementById('chatbotHistoryList');
        if (!listContainer) return;
        
        listContainer.innerHTML = '';
        if (chatThreads.length === 0) {
            listContainer.innerHTML = '<span class="empty-history-msg">No saved chats</span>';
            return;
        }
        
        chatThreads.forEach(t => {
            let dispTitle = t.messages.length > 0 ? t.messages[0].content : t.title;
            // Clean markdown notation from title if present
            dispTitle = dispTitle.replace(/[\*#_`]/g, '').trim();
            if (dispTitle.length > 25) dispTitle = dispTitle.substring(0, 22) + '...';
            
            const item = document.createElement('div');
            item.className = `history-item ${t.id === activeThread.id ? 'active' : ''}`;
            
            item.innerHTML = `
                <div class="history-item-content">
                    <i class="fa-solid fa-terminal"></i>
                    <span>${dispTitle}</span>
                </div>
                <button class="btn-delete-thread" data-id="${t.id}" title="Delete Thread">
                    <i class="fa-solid fa-trash-can"></i>
                </button>
            `;
            
            item.querySelector('.history-item-content').onclick = function() {
                activeThread = t;
                loadThreadMessages(t);
                renderHistorySidebar();
            };
            
            item.querySelector('.btn-delete-thread').onclick = function(e) {
                e.stopPropagation();
                deleteThread(t.id);
            };
            
            listContainer.appendChild(item);
        });
    }
    
    function deleteThread(id) {
        chatThreads = chatThreads.filter(t => t.id !== id);
        if (activeThread.id === id) {
            if (chatThreads.length > 0) {
                activeThread = chatThreads[0];
                loadThreadMessages(activeThread);
            } else {
                startNewThread();
            }
        }
        saveThreadsToStorage();
        renderHistorySidebar();
    }
    
    if (newThreadBtn) {
        newThreadBtn.addEventListener('click', startNewThread);
    }
    
    // B. Window toggling and bindings
    if (chatbotToggle && chatbotWindow) {
        chatbotToggle.addEventListener('click', () => {
            chatbotWindow.classList.toggle('open');
            if (chatbotWindow.classList.contains('open')) {
                chatbotInput.focus();
            }
        });
        
        if (chatbotClose) {
            chatbotClose.addEventListener('click', () => {
                chatbotWindow.classList.remove('open');
            });
        }
        
        if (chatbotHistoryToggle && chatbotHistorySidebar) {
            chatbotHistoryToggle.addEventListener('click', () => {
                chatbotHistorySidebar.classList.toggle('hidden');
                chatbotHistoryToggle.classList.toggle('active');
                chatbotWindow.classList.toggle('history-expanded');
            });
        }
        
        // Handle input click/enter key actions
        chatbotSend.addEventListener('click', sendChatbotMsg);
        chatbotInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                sendChatbotMsg();
            }
        });
        
        // Handle Suggestion Chips click
        suggestionChips.forEach(chip => {
            chip.addEventListener('click', function() {
                const message = this.getAttribute('data-msg');
                chatbotInput.value = message;
                sendChatbotMsg();
            });
        });
        
        // Initialize threads
        initThreads();
    }
    
    // C. Server-Sent Events Token Streaming logic
    async function sendChatbotMsg() {
        const query = chatbotInput.value.trim();
        if (!query) return;
        
        // Append user query bubble
        appendChatBubble(query, 'user');
        chatbotInput.value = '';
        
        // Add to history list
        activeThread.messages.push({ role: 'user', content: query });
        saveThreadsToStorage();
        renderHistorySidebar();
        
        // Typing / thinking state
        const typingId = appendChatBubble('<i class="fa-solid fa-spinner fa-spin"></i> Directing query to Groq Llama 3 intelligence matrix...', 'bot typing');
        
        try {
            const response = await fetch('/api/stream-chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: query,
                    history: activeThread.messages.slice(0, -1) // excluding this new query
                })
            });
            
            const typingBubble = document.getElementById(typingId);
            if (typingBubble) typingBubble.remove();
            
            if (!response.ok) {
                throw new Error("Server rejected streaming connection.");
            }
            
            // Build streaming target bubble
            const botBubbleId = appendChatBubble('', 'bot streaming');
            const botBubble = document.getElementById(botBubbleId);
            
            let fullText = "";
            const reader = response.body.getReader();
            const decoder = new TextDecoder('utf-8');
            
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                
                const chunk = decoder.decode(value);
                const lines = chunk.split('\n');
                
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const dataStr = line.substring(6).trim();
                        if (dataStr === '[DONE]') {
                            break;
                        }
                        
                        try {
                            const parsed = JSON.parse(dataStr);
                            if (parsed.token) {
                                fullText += parsed.token;
                                botBubble.innerHTML = marked.parse(fullText);
                                chatbotMessages.scrollTop = chatbotMessages.scrollHeight;
                            } else if (parsed.error) {
                                fullText += `\n⚠️ *Stream Error: ${parsed.error}*`;
                                botBubble.innerHTML = marked.parse(fullText);
                            }
                        } catch (e) {
                            // Non-json or socket packets boundary split
                        }
                    }
                }
            }
            
            // Save final string to active history
            activeThread.messages.push({ role: 'assistant', content: fullText });
            saveThreadsToStorage();
            renderHistorySidebar();
            
        } catch (err) {
            console.error(err);
            const typingBubble = document.getElementById(typingId);
            if (typingBubble) typingBubble.remove();
            appendChatBubble("⚠️ **AI Brain offline:** Could not establish stream completion. Please verify that your API key is correct and loaded.", 'bot');
        }
    }
    
    // D. Voice Speech-to-Text Input logic
    const chatbotMic = document.getElementById('chatbotMic');
    if (chatbotMic) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (SpeechRecognition) {
            const recognition = new SpeechRecognition();
            recognition.continuous = false;
            recognition.lang = 'en-US';
            recognition.interimResults = false;
            
            recognition.onstart = function() {
                chatbotMic.classList.add('recording');
                chatbotInput.placeholder = "Listening... dictate your claim...";
            };
            
            recognition.onerror = function(e) {
                console.error("Speech Recognition Error: ", e);
                chatbotMic.classList.remove('recording');
                chatbotInput.placeholder = "Microphone error. Check settings...";
            };
            
            recognition.onend = function() {
                chatbotMic.classList.remove('recording');
                chatbotInput.placeholder = "Analyze a claim or ask a question...";
            };
            
            recognition.onresult = function(event) {
                const transcript = event.results[0][0].transcript;
                chatbotInput.value = transcript;
                chatbotInput.focus();
            };
            
            chatbotMic.onclick = function() {
                if (chatbotMic.classList.contains('recording')) {
                    recognition.stop();
                } else {
                    recognition.start();
                }
            };
        } else {
            // Hide mic button if Speech API is not supported in current browser
            chatbotMic.style.display = 'none';
        }
    }
    
    // E. Generative AI deep analysis report caller (Triggered by the Result card explainer button)
    function sendAIDeepAnalysis(title, text) {
        chatbotMessages.innerHTML = ''; // Fresh workspace
        appendChatBubble("🤖 **VERIFACT AI Misinformation Engine starting up...**", 'bot');
        
        const typingId = appendChatBubble('<i class="fa-solid fa-circle-nodes fa-spin"></i> Parsing TF-IDF weight matrices and running Deep ML consensus explanation... (Llama 3)', 'bot typing');
        
        const formData = new FormData();
        formData.append('title', title);
        formData.append('text', text);
        formData.append('url', '');
        
        fetch('/api/ai-analysis', {
            method: 'POST',
            body: formData
        })
        .then(res => {
            if (!res.ok) {
                throw new Error("AI analysis query failed.");
            }
            return res.json();
        })
        .then(data => {
            const typingBubble = document.getElementById(typingId);
            if (typingBubble) typingBubble.remove();
            
            // Render markdown explanation
            appendChatBubble(marked.parse(data.explanation), 'bot');
            
            // Add thread entry
            const newT = {
                id: 'thread_' + Date.now(),
                title: 'Report: ' + title.substring(0, 18) + '...',
                messages: [
                    { role: 'user', content: `Explain news article: "${title}"` },
                    { role: 'assistant', content: data.explanation }
                ]
            };
            chatThreads.unshift(newT);
            activeThread = newT;
            saveThreadsToStorage();
            renderHistorySidebar();
            
            chatbotInput.value = '';
            chatbotInput.placeholder = "Ask Verifact AI follow up questions about this report...";
        })
        .catch(err => {
            console.error(err);
            const typingBubble = document.getElementById(typingId);
            if (typingBubble) typingBubble.remove();
            appendChatBubble("⚠️ **Deep AI Analysis failed.** Check Groq API configuration details.", 'bot');
        });
    }



    function appendChatBubble(htmlContent, type) {
        const bubble = document.createElement('div');
        const bubbleId = 'bubble-' + Date.now() + Math.random().toString(36).substr(2, 5);
        bubble.id = bubbleId;
        bubble.className = `chat-message ${type}`;
        bubble.innerHTML = htmlContent;
        
        chatbotMessages.appendChild(bubble);
        chatbotMessages.scrollTop = chatbotMessages.scrollHeight;
        
        return bubbleId;
    }
});
