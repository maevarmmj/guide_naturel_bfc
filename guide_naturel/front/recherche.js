document.addEventListener('DOMContentLoaded', () => {
    const chatLog = document.getElementById('chat-log');
    const chatInput = document.getElementById('chat-input');
    const sendButton = document.getElementById('send-chat-button');
    const skipButton = document.getElementById('skip-chat-button');
    const finalResultsContentElement = document.getElementById('final-chatbot-results-content');

    const API_BASE_URL = 'http://localhost:5001'; // Ajustez si nécessaire

    let conversationId = null; // ID pour le flux de questions en cours
    let resultsConversationId = null; // ID de la conversation qui a produit les RÉSULTATS actuellement affichés
    let currentQuestionIsSkippable = false;
    let currentPage = 1;
    let totalPages = 1;
    let fullItemsForCurrentPage = [];
    let currentAggregationType = 'unknown';

    let infoboxElement = null;
    let currentlyDisplayedInfoboxItemIndex = null;

    console.log("Chatbot script loaded. Version: KeepOldPagination");

    function addMessageToLog(message, sender, isHtml = false) {
        const p = document.createElement('p');
        if (isHtml) { p.innerHTML = message; } else { p.textContent = message; }
        p.classList.add(sender === 'user' ? 'user-message' : 'bot-message');
        chatLog.appendChild(p);
        requestAnimationFrame(() => requestAnimationFrame(() => p.classList.add('visible')));
        chatLog.scrollTop = chatLog.scrollHeight;
    }

    function enableInputs(isQuestionSkippable) {
        chatInput.disabled = false;
        sendButton.disabled = false;
        currentQuestionIsSkippable = isQuestionSkippable;
        updateSkipButtonState();
        chatInput.focus();
        console.log("Inputs enabled. Skippable:", isQuestionSkippable);
    }

    function disableInputs() {
        chatInput.disabled = true;
        sendButton.disabled = true;
        skipButton.disabled = true;
        console.log("Inputs disabled.");
    }

    function updateSkipButtonState() {
        if (chatInput.disabled) {
            skipButton.disabled = true;
        } else {
            skipButton.disabled = !currentQuestionIsSkippable;
        }
    }

    function clearResultDisplayArea() {
        console.log("Clearing result display area (innerHTML).");
        if (finalResultsContentElement) finalResultsContentElement.innerHTML = ''; // Ceci enlèvera tout, y compris la pagination
        hideInfobox();
    }

    function displayPaginatedResults(resultsData, convIdForTheseResults) {
        console.log("Displaying paginated results. Data received:", resultsData, "for convId:", convIdForTheseResults);
        if (!finalResultsContentElement) {
            addMessageToLog("Erreur critique: Zone d'affichage des résultats non trouvée.", "bot");
            return;
        }
        // Vider la zone de résultats pour les nouveaux résultats.
        // Cela enlèvera aussi les anciens contrôles de pagination s'ils étaient là.
        clearResultDisplayArea();

        resultsConversationId = convIdForTheseResults; // Mettre à jour avec l'ID de la conversation qui a généré ces résultats
        currentAggregationType = resultsData.aggregation_type || 'unknown';
        console.log("Current aggregation type set to:", currentAggregationType);

        const { items, message, page, total_pages, total_items } = resultsData;

        currentPage = parseInt(page, 10);
        totalPages = parseInt(total_pages, 10);
        fullItemsForCurrentPage = items || [];

        if (message && fullItemsForCurrentPage.length === 0 && currentPage === 1 && total_items === 0) {
            const messageDiv = document.createElement('div');
            messageDiv.className = 'results-message no-results-message';
            messageDiv.textContent = message; // Ex: "Désolée, rien trouvé..."
            finalResultsContentElement.appendChild(messageDiv);
        }

        const resultsList = document.createElement('ul');
        resultsList.className = 'results-list';
        if (fullItemsForCurrentPage.length > 0) {
            fullItemsForCurrentPage.forEach((item, index) => {
                const li = document.createElement('li');
                li.className = 'result-item-clickable';
                const nomVern = item.nomVernaculaire || 'N/A';
                const nomSci = item.nomScientifiqueRef || 'N/A';
                li.textContent = `- ${nomVern} (${nomSci})`;
                li.dataset.itemIndex = index.toString();
                li.addEventListener('click', (event) => {
                    event.stopPropagation();
                    toggleInfobox(index, li);
                });
                resultsList.appendChild(li);
            });
            finalResultsContentElement.appendChild(resultsList);
        }

        // Afficher le message de résumé (ex: "Page 1 sur X (Y espèces)")
        // seulement s'il y a des items à afficher ou un total d'items > 0
        if (message && (fullItemsForCurrentPage.length > 0 || total_items > 0)) {
            const summaryDiv = document.createElement('div');
            summaryDiv.className = 'results-summary';
            summaryDiv.textContent = message;
            finalResultsContentElement.appendChild(summaryDiv);
        }

        // Toujours tenter de rendre la pagination, renderPaginationControls a sa propre logique pour afficher/cacher
        renderPaginationControls(total_items > 0);
    }

    function createInfoboxElement() {
        // ... (code inchangé) ...
        if (!infoboxElement) {
            console.log("Creating infobox element for the first time.");
            infoboxElement = document.createElement('div');
            infoboxElement.id = 'item-infobox';
            infoboxElement.className = 'infobox-hidden';
            const contentDiv = document.createElement('div');
            contentDiv.id = 'infobox-content-details';
            infoboxElement.appendChild(contentDiv);
            const closeButton = document.createElement('button');
            closeButton.id = 'infobox-close-button';
            closeButton.innerHTML = '×';
            closeButton.title = "Fermer";
            closeButton.addEventListener('click', (e) => { e.stopPropagation(); hideInfobox(); });
            infoboxElement.appendChild(closeButton);
            document.body.appendChild(infoboxElement);
            infoboxElement.addEventListener('click', (e) => e.stopPropagation());
        }
    }

    function toggleInfobox(itemIndex, targetLiElement) {
        // ... (code inchangé, il utilise currentAggregationType ou item.aggregation_type) ...
        createInfoboxElement();
        const item = fullItemsForCurrentPage[itemIndex];
        console.log("Toggling infobox for item:", item, "at index:", itemIndex);
        if (!item) {
            console.error("Infobox: Item not found at index", itemIndex);
            return;
        }

        if (infoboxElement.classList.contains('infobox-visible') && currentlyDisplayedInfoboxItemIndex === itemIndex) {
            hideInfobox();
            return;
        }

        const contentDiv = infoboxElement.querySelector('#infobox-content-details');
        if (!contentDiv) return;
        contentDiv.innerHTML = '';

        const detailsTitle = document.createElement('h4');
        detailsTitle.className = 'infobox-title';
        detailsTitle.textContent = item.nomVernaculaire || item.nomScientifiqueRef || "Détails";
        contentDiv.appendChild(detailsTitle);

        const detailsList = document.createElement('ul');
        detailsList.className = 'infobox-details-list';

        const commonFieldsToShow = {
            nomScientifiqueRef: "Nom scientifique",
            regne: "Règne",
            groupeTaxoSimple: "Groupe taxonomique",
            totalObservationsEspece: "Total observations",
            departements: "Départements d'observation",
            statuts: "Statuts observés"
        };

        for (const [key, label] of Object.entries(commonFieldsToShow)) {
            if (item.hasOwnProperty(key) && item[key] !== undefined && item[key] !== null) {
                const li = document.createElement('li');
                const keySp = document.createElement('span');
                keySp.className = 'infobox-detail-key';
                keySp.textContent = `${formatFieldKey(key, label)}: `;
                li.appendChild(keySp);
                const valSp = document.createElement('span');
                valSp.className = 'infobox-detail-value';
                let valToDisp = 'N/A';
                if (key === "departements" || key === "statuts") {
                    if (Array.isArray(item[key]) && item[key].length > 0) valToDisp = item[key].join(', ');
                } else if (item[key].toString().trim() !== '') {
                    valToDisp = item[key].toString();
                }
                valSp.textContent = valToDisp;
                li.appendChild(valSp);
                detailsList.appendChild(li);
            }
        }

        const aggregationTypeForItem = item.aggregation_type || currentAggregationType;
        console.log("Infobox: Aggregation type for this item:", aggregationTypeForItem);

        if (aggregationTypeForItem === "departement_specifique" && item.hasOwnProperty("communesDetails")) {
            if (Array.isArray(item.communesDetails) && item.communesDetails.length > 0) {
                const li = document.createElement('li');
                const keySp = document.createElement('span');
                keySp.className = 'infobox-detail-key';
                keySp.textContent = `${formatFieldKey("communesDetails", "Lieux (Commune (Dépt.))")}: `;
                li.appendChild(keySp);
                const valSp = document.createElement('span');
                valSp.className = 'infobox-detail-value';
                valSp.textContent = item.communesDetails.map(cd => `${cd.commune || 'N/A'} (${cd.departement || 'N/A'})`).join('; ');
                li.appendChild(valSp);
                detailsList.appendChild(li);
            }
        }

        contentDiv.appendChild(detailsList);
        positionInfobox(targetLiElement);
        infoboxElement.classList.remove('infobox-hidden');
        infoboxElement.getBoundingClientRect();
        infoboxElement.classList.add('infobox-visible');
        currentlyDisplayedInfoboxItemIndex = itemIndex;
    }

    function positionInfobox(targetLiElement) {
        // ... (code inchangé) ...
        if (!infoboxElement || !targetLiElement) return;
        const targetRect = targetLiElement.getBoundingClientRect();
        const wasHidden = infoboxElement.style.display === 'none' || infoboxElement.classList.contains('infobox-hidden');
        if (wasHidden) {
            infoboxElement.style.visibility = 'hidden';
            infoboxElement.style.display = 'block';
            infoboxElement.style.opacity = '0';
        }
        const infoboxRect = infoboxElement.getBoundingClientRect();
        if (wasHidden) {
            if (!infoboxElement.classList.contains('infobox-visible')) {
                infoboxElement.style.display = 'none';
            }
            infoboxElement.style.visibility = '';
            infoboxElement.style.opacity = '';
        }
        const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
        const scrollLeft = window.pageXOffset || document.documentElement.scrollLeft;
        const viewportWidth = window.innerWidth;
        const viewportHeight = window.innerHeight;
        const margin = 15;
        let top = targetRect.bottom + scrollTop;
        let left = targetRect.left + scrollLeft;
        if (top + infoboxRect.height + margin > viewportHeight + scrollTop) {
            top = targetRect.top + scrollTop - infoboxRect.height - margin;
        }
        if (top < scrollTop + margin) top = scrollTop + margin;
        if (left + infoboxRect.width + margin > viewportWidth + scrollLeft) {
            left = viewportWidth + scrollLeft - infoboxRect.width - margin;
        }
        if (left < scrollLeft + margin) left = scrollLeft + margin;
        infoboxElement.style.top = `${Math.max(0, top)}px`;
        infoboxElement.style.left = `${Math.max(0, left)}px`;
    }

    function hideInfobox() {
        // ... (code inchangé) ...
        if (infoboxElement) {
            infoboxElement.classList.remove('infobox-visible');
            currentlyDisplayedInfoboxItemIndex = null;
            console.log("Infobox hidden.");
        }
    }

    document.addEventListener('click', (event) => {
        // ... (code inchangé) ...
        if (infoboxElement && infoboxElement.classList.contains('infobox-visible')) {
            hideInfobox();
        }
    });

    function formatFieldKey(key, defaultLabel = null) {
        // ... (code inchangé) ...
        if (defaultLabel) return defaultLabel;
        let formatted = key.replace(/([A-Z])/g, ' $1').toLowerCase();
        formatted = formatted.charAt(0).toUpperCase() + formatted.slice(1);
        formatted = formatted.replace(/id$/i, "ID").replace(/^Cd /i, "Code ").replace(/Lb /i, "");
        formatted = formatted.replace("code Insee", "Code INSEE");
        if (key === "nomVernaculaire") formatted = "Nom vernaculaire";
        if (key === "nomScientifiqueRef") formatted = "Nom scientifique";
        if (key === "totalObservationsEspece") formatted = "Total observations";
        if (key === "departements") formatted = "Départements";
        if (key === "communesDetails") formatted = "Lieux (Commune (Dépt.))";
        if (key === "statuts") formatted = "Statuts";
        return formatted.trim();
    }

    function renderPaginationControls(hasResults) {
        // ... (code inchangé) ...
        const existingPagination = finalResultsContentElement.querySelector('.pagination-controls');
        if (existingPagination) existingPagination.remove();
        if (!hasResults || totalPages <= 1) {
            console.log("Render pagination: No controls needed (hasResults:", hasResults, "totalPages:", totalPages,")");
            return;
        }
        console.log("Render pagination: Rendering controls for page", currentPage, "of", totalPages);
        const paginationDiv = document.createElement('div');
        paginationDiv.className = 'pagination-controls';
        const prevButton = document.createElement('button');
        const prevArrowImage = document.createElement('img');
        prevArrowImage.src = 'ressources/arrow/precedent.png';
        prevArrowImage.alt = 'Précédent';
        prevArrowImage.classList.add('pagination-arrow-icon');
        prevButton.appendChild(prevArrowImage);
        prevButton.title = 'Page précédente';
        prevButton.disabled = currentPage === 1;
        prevButton.addEventListener('click', () => { hideInfobox(); fetchPaginatedResults(currentPage - 1); });
        paginationDiv.appendChild(prevButton);
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
        const goToPageButton = document.createElement('button');
        goToPageButton.textContent = 'OK';
        goToPageButton.title = 'Aller à la page spécifiée';
        goToPageButton.className = 'goto-page-button';
        goToPageButton.addEventListener('click', () => {
            const pageNum = parseInt(pageInput.value, 10);
            if (!isNaN(pageNum) && pageNum >= 1 && pageNum <= totalPages) {
                hideInfobox(); fetchPaginatedResults(pageNum);
            } else {
                pageInput.value = currentPage.toString();
                alert(`Veuillez entrer un numéro de page valide entre 1 et ${totalPages}.`);
            }
        });
        pageInput.addEventListener('keypress', (e) => { if (e.key === 'Enter') { e.preventDefault(); goToPageButton.click(); }});
        paginationDiv.appendChild(goToPageButton);
        const nextButton = document.createElement('button');
        const nextArrowImage = document.createElement('img');
        nextArrowImage.src = 'ressources/arrow/suivant.png';
        nextArrowImage.alt = 'Suivant';
        nextArrowImage.classList.add('pagination-arrow-icon');
        nextButton.appendChild(nextArrowImage);
        nextButton.title = 'Page suivante';
        nextButton.disabled = currentPage === totalPages;
        nextButton.addEventListener('click', () => { hideInfobox(); fetchPaginatedResults(currentPage + 1); });
        paginationDiv.appendChild(nextButton);
        finalResultsContentElement.appendChild(paginationDiv);
    }

    async function fetchPaginatedResults(page) {
        // ... (code inchangé) ...
        console.log(`Fetching paginated results for page: ${page}, using results conv ID: ${resultsConversationId}`);
        const requestedPage = parseInt(page, 10);
        if (!resultsConversationId) {
            console.error("fetchPaginatedResults: No resultsConversationId. Cannot fetch page.");
            addMessageToLog("Session de résultats invalide. Relance d'une recherche...", "bot");
            const existingPagination = finalResultsContentElement.querySelector('.pagination-controls');
            if (existingPagination) existingPagination.remove();
            setTimeout(() => startConversation(false), 2000);
            return;
        }
        if (isNaN(requestedPage) || requestedPage < 1 || (totalPages > 0 && requestedPage > totalPages) ) {
            console.warn(`Demande de page invalide: ${requestedPage}. Doit être entre 1 et ${totalPages}.`);
            const pageNumInput = document.getElementById('page-number-input');
            if (pageNumInput) pageNumInput.value = currentPage.toString();
            if (totalPages > 0) {
                alert(`Numéro de page invalide. Entrez un nombre entre 1 et ${totalPages}.`);
            }
            return;
        }
        try {
            const response = await fetch(`${API_BASE_URL}/chat/results/${resultsConversationId}/page/${requestedPage}`, {
                method: 'GET', headers: { 'Content-Type': 'application/json' },
            });
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ error: `Erreur HTTP: ${response.status}` }));
                throw new Error(errorData.error || `Erreur HTTP ${response.status}`);
            }
            const data = await response.json();
            console.log("Paginated results received:", data);
            if (data.error) throw new Error(data.error);
            if (data.results_data) {
                displayPaginatedResults(data.results_data, resultsConversationId);
            } else {
                addMessageToLog("Aucune donnée reçue pour cette page.", "bot");
            }
        } catch (error) {
            console.error('Erreur résultats paginés:', error);
            addMessageToLog(`Erreur pagination: ${error.message}.`, 'bot');
            renderPaginationControls(fullItemsForCurrentPage.length > 0 || totalPages > 0);
        }
    }

    async function startConversation(isInitialLoad = false) {
        console.log("Starting conversation. Initial load:", isInitialLoad);
        if (isInitialLoad) {
            if (finalResultsContentElement) {
                clearResultDisplayArea();
                resultsConversationId = null;
                fullItemsForCurrentPage = [];
                currentAggregationType = 'unknown';
                const placeholder = document.createElement('div');
                placeholder.className = 'results-message initial-placeholder';
                placeholder.textContent = "Les résultats de votre recherche apparaîtront ici...";
                finalResultsContentElement.appendChild(placeholder);
            }
        } else {
            // LORSQU'UNE NOUVELLE CONVERSATION DE QUESTIONS DÉMARRE APRÈS DES RÉSULTATS,
            // NE PAS ENLEVER LES CONTRÔLES DE PAGINATION DES RÉSULTATS PRÉCÉDENTS.
            // Ils seront enlevés par clearResultDisplayArea() LORSQUE de NOUVEAUX résultats arriveront.
            console.log("Restarting chat Q&A, previous results and pagination (if any) remain.");
            // const existingPagination = finalResultsContentElement.querySelector('.pagination-controls');
            // if (existingPagination) existingPagination.remove(); // LIGNE COMMENTÉE/SUPPRIMÉE
        }
        chatLog.innerHTML = ''; // Toujours vider le log du chat
        disableInputs();
        addMessageToLog('Coucou ! Prêt(e) pour une nouvelle recherche ?', "bot");
        try {
            const response = await fetch(`${API_BASE_URL}/chat/start`, {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
            });
            if (!response.ok) throw new Error(`Erreur HTTP au démarrage: ${response.status}`);
            const data = await response.json();
            console.log("Start conversation response:", data);
            if (data.error) throw new Error(data.error);

            conversationId = data.conversation_id; // Nouvel ID pour le flux de questions
            // resultsConversationId N'EST PAS réinitialisé ici, il appartient aux résultats déjà affichés

            if (data.question && data.question.text) {
                addMessageToLog(data.question.text, 'bot');
                enableInputs(data.question.is_skippable || false);
            } else {
                 addMessageToLog("Aucune question initiale reçue.", "bot");
                 disableInputs();
            }
        } catch (error) {
            console.error('Erreur au démarrage de la conversation:', error);
            addMessageToLog(`Impossible de démarrer: ${error.message}. Nouvelle tentative...`, 'bot');
            disableInputs();
            setTimeout(() => startConversation(isInitialLoad), 5000); // isInitialLoad sera false ici
        }
    }

    async function handleSend(messageToSend) {
        // ... (code inchangé) ...
        console.log(`Handling send. Message: "${messageToSend}", Conv ID for Q&A: ${conversationId}`);
        if (!conversationId) { // ID pour le flux de questions
            addMessageToLog("Session de questions non active. Relance...", 'bot');
            setTimeout(() => startConversation(false), 2000);
            return;
        }
        disableInputs();
        hideInfobox();
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
            console.log("Handle send response (after Q&A):", data);

            if (data.error) {
                addMessageToLog(`Erreur serveur: ${data.error}`, 'bot');
                enableInputs(currentQuestionIsSkippable);
            } else if (data.is_final_questions && data.results_data) {
                addMessageToLog("J'ai cherché pour toi ! Voici les résultats à droite.", "bot");
                // data.conversation_id ici est l'ID de la conversation qui vient de se terminer
                // et qui a produit ces filtres/résultats. C'est celui qu'on veut pour la pagination.
                displayPaginatedResults(data.results_data, data.conversation_id);
                // resultsConversationId est maintenant mis à jour par displayPaginatedResults
                addMessageToLog("C'est affiché ! Prêt pour une nouvelle recherche dans un instant...", "bot");
                setTimeout(() => startConversation(false), 2000);
            } else if (data.question && data.question.text) {
                addMessageToLog(data.question.text, 'bot');
                enableInputs(data.question.is_skippable || false);
            } else {
                addMessageToLog("Oups, réponse inattendue. Relance...", 'bot');
                disableInputs();
                setTimeout(() => startConversation(false), 2000);
            }
        } catch (error) {
            console.error('Erreur envoi message:', error);
            addMessageToLog(`Erreur communication: ${error.message}.`, 'bot');
            enableInputs(currentQuestionIsSkippable);
        }
    }

    function regularSendMessage() {
        // ... (code inchangé) ...
        const messageText = chatInput.value.trim();
        if (!messageText || chatInput.disabled) return;
        addMessageToLog(messageText, 'user');
        chatInput.value = '';
        handleSend(messageText);
    }

    function skipQuestion() {
        // ... (code inchangé) ...
        if (skipButton.disabled) return;
        addMessageToLog("<i>(Je ne sais pas)</i>", 'user', true);
        chatInput.value = '';
        handleSend("passer");
    }

    sendButton.addEventListener('click', regularSendMessage);
    chatInput.addEventListener('keypress', (e) => { if (e.key === 'Enter' && !chatInput.disabled) regularSendMessage(); });
    skipButton.addEventListener('click', skipQuestion);

    startConversation(true);
});