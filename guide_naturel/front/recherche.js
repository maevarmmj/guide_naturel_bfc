document.addEventListener('DOMContentLoaded', () => {
    const chatLog = document.getElementById('chat-log');
    const chatInput = document.getElementById('chat-input');
    const sendButton = document.getElementById('send-chat-button');
    const skipButton = document.getElementById('skip-chat-button');
    const finalResultsContentElement = document.getElementById('final-chatbot-results-content');

    const API_BASE_URL = 'http://localhost:5001';

    let conversationId = null;
    let currentQuestionIsSkippable = false;
    let currentPage = 1;
    let totalPages = 1;

    function addMessageToLog(message, sender, isHtml = false) {
        const p = document.createElement('p');
        if (isHtml) {
            p.innerHTML = message;
        } else {
            p.textContent = message;
        }
        p.classList.add(sender === 'user' ? 'user-message' : 'bot-message');
        chatLog.appendChild(p);
        requestAnimationFrame(() => {
            requestAnimationFrame(() => {
                p.classList.add('visible');
            });
        });
        chatLog.scrollTop = chatLog.scrollHeight;
    }

    function clearResultDisplayArea() {
        if (finalResultsContentElement) {
            finalResultsContentElement.innerHTML = '';
        }
    }

    function displayPaginatedResults(resultsData) {
        if (!finalResultsContentElement) {
            addMessageToLog("Zone de résultats non trouvée.", "bot");
            return;
        }
        clearResultDisplayArea();

        const { items, message, page, total_pages, total_items } = resultsData;
        currentPage = parseInt(page, 10); // S'assurer que currentPage est un nombre
        totalPages = parseInt(total_pages, 10); // S'assurer que totalPages est un nombre

        if (message && items.length === 0 && currentPage === 1) {
            const messageDiv = document.createElement('div');
            messageDiv.className = 'results-message';
            messageDiv.textContent = message;
            finalResultsContentElement.appendChild(messageDiv);
        }

        const resultsList = document.createElement('ul');
        resultsList.className = 'results-list';
        if (items && items.length > 0) {
            items.forEach(item => {
                const li = document.createElement('li');
                const nomVern = item.nomVernaculaire || 'N/A';
                const nomSci = item.nomScientifiqueRef || 'N/A';
                const regne = item.regne || 'N/A';
                const commune = item.commune || 'N/A';
                const nbObs = item.nombreObservations !== undefined ? item.nombreObservations : 'N/A';
                li.textContent = `- ${nomVern} (${nomSci}) - Règne: ${regne} - Commune: ${commune} (Obs: ${nbObs})`;
                resultsList.appendChild(li);
            });
            finalResultsContentElement.appendChild(resultsList);
        }

        if (message && items.length > 0) {
            const summaryDiv = document.createElement('div');
            summaryDiv.className = 'results-summary';
            summaryDiv.textContent = message;
            finalResultsContentElement.appendChild(summaryDiv);
        }
        renderPaginationControls(total_items > 0);
    }

    function renderPaginationControls(hasResults) {
        const existingPagination = finalResultsContentElement.querySelector('.pagination-controls');
        if (existingPagination) existingPagination.remove();

        if (!hasResults || totalPages <= 1) return;

        const paginationDiv = document.createElement('div');
        paginationDiv.className = 'pagination-controls';

        // 1. Bouton Précédent
        const prevButton = document.createElement('button');
        prevButton.textContent = 'Précédent';
        prevButton.title = 'Page précédente';
        prevButton.disabled = currentPage === 1;
        prevButton.addEventListener('click', () => fetchPaginatedResults(currentPage - 1));
        paginationDiv.appendChild(prevButton);

        // 2. Conteneur pour l'input de page
        const pageInputContainer = document.createElement('div');
        pageInputContainer.className = 'page-input-container';

        const pageInputLabel = document.createElement('label');
        pageInputLabel.htmlFor = 'page-number-input';
        pageInputLabel.textContent = 'Page :';
        pageInputLabel.className = 'page-input-label';
        pageInputContainer.appendChild(pageInputLabel);

        const pageInput = document.createElement('input');
        pageInput.type = 'number';
        pageInput.id = 'page-number-input';
        pageInput.className = 'page-number-input';
        pageInput.min = '1';
        pageInput.max = totalPages.toString();
        pageInput.value = currentPage.toString();
        pageInput.setAttribute('aria-label', 'Numéro de page à atteindre');
        pageInputContainer.appendChild(pageInput);

        const totalPagesSpan = document.createElement('span');
        totalPagesSpan.className = 'total-pages-indicator';
        totalPagesSpan.textContent = `/ ${totalPages}`;
        pageInputContainer.appendChild(totalPagesSpan);

        paginationDiv.appendChild(pageInputContainer);

        // 3. Bouton "OK" pour l'input
        const goToPageButton = document.createElement('button');
        goToPageButton.textContent = 'OK';
        goToPageButton.title = 'Aller à la page spécifiée';
        goToPageButton.className = 'goto-page-button';
        goToPageButton.addEventListener('click', () => {
            const pageNum = parseInt(pageInput.value, 10);
            if (!isNaN(pageNum)) { // La validation fine (min/max) se fait dans fetchPaginatedResults
                fetchPaginatedResults(pageNum);
            } else {
                pageInput.value = currentPage.toString(); // Réinitialiser si non numérique
                alert(`Veuillez entrer un numéro de page valide.`);
            }
        });
        pageInput.addEventListener('keypress', (event) => {
            if (event.key === 'Enter') {
                event.preventDefault();
                goToPageButton.click();
            }
        });
        paginationDiv.appendChild(goToPageButton);

        // 4. Bouton Suivant
        const nextButton = document.createElement('button');
        nextButton.textContent = 'Suivant';
        nextButton.title = 'Page suivante';
        nextButton.disabled = currentPage === totalPages;
        nextButton.addEventListener('click', () => fetchPaginatedResults(currentPage + 1));
        paginationDiv.appendChild(nextButton);

        finalResultsContentElement.appendChild(paginationDiv);
    }

    async function fetchPaginatedResults(page) {
        const requestedPage = parseInt(page, 10); // S'assurer que c'est un nombre

        if (!conversationId) {
            console.error("Aucun ID de conversation pour la pagination.");
            addMessageToLog("Erreur: Session de recherche invalide. Une nouvelle recherche va démarrer.", "bot");
            setTimeout(() => startConversation(false), 2000);
            return;
        }

        if (isNaN(requestedPage) || requestedPage < 1 || requestedPage > totalPages) {
            console.warn(`Demande de page invalide : ${requestedPage}. Doit être entre 1 et ${totalPages}.`);
            const pageNumInput = document.getElementById('page-number-input');
            if (pageNumInput) {
                pageNumInput.value = currentPage.toString(); // Réinitialiser l'input à la page actuelle connue
            }
            alert(`Numéro de page invalide. Veuillez entrer un nombre entre 1 et ${totalPages}.`);
            return;
        }

        // Optionnel: addMessageToLog(`Chargement de la page ${requestedPage}...`, "bot");

        try {
            const response = await fetch(`${API_BASE_URL}/chat/results/${conversationId}/page/${requestedPage}`, {
                method: 'GET',
                headers: { 'Content-Type': 'application/json' },
            });
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ error: `Erreur HTTP: ${response.status}` }));
                throw new Error(errorData.error || `Erreur HTTP ${response.status}`);
            }
            const data = await response.json();
            if (data.error) throw new Error(data.error);

            if (data.results_data) {
                displayPaginatedResults(data.results_data);
            } else {
                addMessageToLog("Aucune donnée de résultat reçue pour cette page.", "bot");
            }
        } catch (error) {
            console.error('Erreur résultats paginés:', error);
            addMessageToLog(`Erreur pagination: ${error.message}.`, 'bot');
        }
    }

    function enableInputs(isQuestionSkippable) {
        chatInput.disabled = false;
        sendButton.disabled = false;
        currentQuestionIsSkippable = isQuestionSkippable;
        updateSkipButtonState();
        chatInput.focus();
    }

    function disableInputs() {
        chatInput.disabled = true;
        sendButton.disabled = true;
        skipButton.disabled = true;
    }

    function updateSkipButtonState() {
        if (chatInput.disabled) {
            skipButton.disabled = true;
        } else {
            skipButton.disabled = !currentQuestionIsSkippable;
        }
    }

   async function startConversation(isInitialLoad = false) {
        if (isInitialLoad && finalResultsContentElement) {
            clearResultDisplayArea();
            const placeholder = document.createElement('div');
            placeholder.className = 'results-message';
            placeholder.textContent = "Les résultats de votre recherche apparaîtront ici...";
            finalResultsContentElement.appendChild(placeholder);
        }
        chatLog.innerHTML = '';
        disableInputs();
        addMessageToLog("Bonjour ! Prêt pour une nouvelle recherche ? Je vais vous poser quelques questions.", "bot");

        try {
            const response = await fetch(`${API_BASE_URL}/chat/start`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
            });
            if (!response.ok) throw new Error(`Erreur HTTP: ${response.status}`);
            const data = await response.json();
            if (data.error) throw new Error(data.error);

            conversationId = data.conversation_id;
            if (data.question && data.question.text) {
                addMessageToLog(data.question.text, 'bot');
                enableInputs(data.question.is_skippable || false);
            } else {
                 addMessageToLog("Aucune question initiale reçue.", "bot");
                 disableInputs();
            }
        } catch (error) {
            console.error('Erreur au démarrage:', error);
            addMessageToLog(`Impossible de démarrer: ${error.message}. Nouvelle tentative...`, 'bot');
            disableInputs();
            setTimeout(() => startConversation(isInitialLoad), 5000);
        }
    }

    async function handleSend(messageToSend) {
        if (!conversationId) {
            addMessageToLog("Erreur: Conversation non active. Relance...", 'bot');
            setTimeout(() => startConversation(false), 2000);
            return;
        }
        disableInputs();

        try {
            const response = await fetch(`${API_BASE_URL}/chat/send`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: messageToSend, conversation_id: conversationId }),
            });
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ error: `Erreur HTTP: ${response.status}` }));
                throw new Error(errorData.error || `Erreur HTTP non spécifiée`);
            }
            const data = await response.json();
            if (data.conversation_id) conversationId = data.conversation_id;

            if (data.error) {
                addMessageToLog(`Erreur serveur: ${data.error}`, 'bot');
                enableInputs(currentQuestionIsSkippable);
            } else if (data.is_final_questions && data.results_data) {
                addMessageToLog("Recherche terminée. Traitement des résultats...", "bot");
                displayPaginatedResults(data.results_data);
                addMessageToLog("Résultats affichés. Nouvelle recherche dans quelques secondes...", "bot");
                setTimeout(() => {
                    startConversation(false);
                }, 4000);
            } else if (data.question && data.question.text) {
                addMessageToLog(data.question.text, 'bot');
                enableInputs(data.question.is_skippable || false);
            } else {
                addMessageToLog("Réponse inattendue. Relance d'une nouvelle recherche...", 'bot');
                disableInputs();
                setTimeout(() => startConversation(false), 3000);
            }
        } catch (error) {
            console.error('Erreur envoi message:', error);
            addMessageToLog(`Erreur communication: ${error.message}.`, 'bot');
            enableInputs(currentQuestionIsSkippable);
        }
    }

    function regularSendMessage() {
        const messageText = chatInput.value.trim();
        if (!messageText) return;
        addMessageToLog(messageText, 'user');
        chatInput.value = '';
        handleSend(messageText);
    }

    function skipQuestion() {
        addMessageToLog("<i>(Je ne sais pas)</i>", 'user', true);
        chatInput.value = '';
        handleSend("passer");
    }

    sendButton.addEventListener('click', regularSendMessage);
    chatInput.addEventListener('keypress', (event) => {
        if (event.key === 'Enter' && !chatInput.disabled) {
            regularSendMessage();
        }
    });
    skipButton.addEventListener('click', () => {
        if (!skipButton.disabled) {
            skipQuestion();
        }
    });

    startConversation(true);
});