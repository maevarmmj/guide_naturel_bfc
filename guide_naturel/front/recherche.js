document.addEventListener('DOMContentLoaded', () => {
    // --- CONSTANTES ET VARIABLES GLOBALES ---
    const API_BASE_URL = 'http://localhost:5001';
    const chatLog = document.getElementById('chat-log');
    const chatInput = document.getElementById('chat-input');
    const sendButton = document.getElementById('send-chat-button');
    const skipButton = document.getElementById('skip-chat-button');
    const finalResultsContentElement = document.getElementById('final-chatbot-results-content');
    const MAX_CONSECUTIVE_SKIPS = 6

    let conversationId = null;         // ID pour le flux de questions du chatbot
    let resultsConversationId = null;    // ID pour le flux de résultats paginés
    let currentQuestionIsSkippable = false;
    let currentPage = 1;
    let totalPages = 1;
    let fullItemsForCurrentPage = [];
    let currentAggregationType = 'unknown';
    let infoboxElement = null;           // L'élément HTML de l'infobox
    let currentlyDisplayedInfoboxItemIndex = null;
    let consecutiveSkips = 0;


    const taxoIcons = { // Correspondance icône <-> taxonomie
        "Amphibiens et reptiles": "🦎",
        "Autres": "🪨",
        "Crabes, crevettes, cloportes et mille-pattes": "🦐",
        "Escargots et autres mollusques": "🐌",
        "Insectes et araignées": "🐜",
        "Mammifères": "🐻",
        "Oiseaux": "🕊️",
        "Poissons": "🐟",
        "Champignons et lichens": "🍄"
    };

    // --- FONCTIONS UTILITAIRES ---

    const displayMessage = (message, sender, isHtml = false) => {
        const p = document.createElement('p');
        if (isHtml) { p.innerHTML = message; } else { p.textContent = message; }
        p.classList.add(sender === 'user' ? 'user-message' : 'bot-message');
        chatLog.appendChild(p);
        requestAnimationFrame(() => requestAnimationFrame(() => p.classList.add('visible')));
        chatLog.scrollTop = chatLog.scrollHeight;
    };

    const setInputState = (enable, isSkippable = false) => {
        chatInput.disabled = !enable;
        sendButton.disabled = !enable;
        currentQuestionIsSkippable = enable && isSkippable;
        skipButton.disabled = !currentQuestionIsSkippable;
        if (enable) chatInput.focus();
    };

    const errorHandler = async (error, message = "Oups, une erreur s'est produite.", retry = null) => {
        console.error(error);
        displayMessage(`${message} ${error.message || error}`, 'bot');
        if (retry) setTimeout(retry, 5000);
    };

    const clearResultDisplayArea = () => {
        finalResultsContentElement.innerHTML = ''; // Supprime le contenu, y compris la pagination
        hideInfobox();
    };

    const fetchAPI = async (url, options = {}) => {
        try {
            const response = await fetch(url, options);
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ error: `Erreur HTTP: ${response.status}` }));
                throw new Error(errorData.error || `Erreur HTTP ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            throw error;
        }
    };

    // --- GESTION DE L'AFFICHAGE DES RESULTATS (LISTE + INFOS) ---

    const displayPaginatedResults = (resultsData, convIdForTheseResults) => {
        if (!finalResultsContentElement) {
            displayMessage("Erreur critique: Zone d'affichage des résultats non trouvée.", "bot");
            return;
        }

        clearResultDisplayArea();
        resultsConversationId = convIdForTheseResults;
        currentAggregationType = resultsData.aggregation_type || 'unknown';

        const { items, message, page, total_pages, total_items } = resultsData;
        currentPage = parseInt(page, 10);
        totalPages = parseInt(total_pages, 10);
        fullItemsForCurrentPage = items || [];

        if (message && fullItemsForCurrentPage.length === 0 && currentPage === 1 && total_items === 0) {
            const messageDiv = document.createElement('div');
            messageDiv.className = 'results-message no-results-message';
            messageDiv.textContent = message;
            finalResultsContentElement.appendChild(messageDiv);
        }

        if (fullItemsForCurrentPage.length > 0) {
            const resultsList = document.createElement('ul');
            resultsList.className = 'results-list';
            fullItemsForCurrentPage.forEach((item, index) => {
                const li = document.createElement('li');
                li.className = 'result-item-clickable';

                const nomVern = item.nomVernaculaire || 'N/A';
                const nomSci = item.nomScientifiqueRef || 'N/A';
                const groupeTaxoSimple = item.groupeTaxoSimple || "Plantes"; //Par defaut
                const taxoIcon = taxoIcons[groupeTaxoSimple] || "🌱";

                li.textContent = `${taxoIcon} ${nomVern} (${nomSci})`;
                li.dataset.itemIndex = index.toString();
                li.addEventListener('click', (event) => {
                    event.stopPropagation();
                    toggleInfobox(index, li);
                });
                resultsList.appendChild(li);
            });
            finalResultsContentElement.appendChild(resultsList);
        }

        if (message && (fullItemsForCurrentPage.length > 0 || total_items > 0)) {
            const summaryDiv = document.createElement('div');
            summaryDiv.className = 'results-summary';
            summaryDiv.textContent = message;
            finalResultsContentElement.appendChild(summaryDiv);
        }

        renderPaginationControls(total_items > 0);
    };

    const createInfoboxElement = () => {
        if (!infoboxElement) {
            infoboxElement = document.createElement('div');
            infoboxElement.id = 'item-infobox';
            infoboxElement.className = 'infobox-hidden';

            const contentDiv = document.createElement('div');
            contentDiv.id = 'infobox-content-details';
            infoboxElement.appendChild(contentDiv);

            document.body.appendChild(infoboxElement);
            infoboxElement.addEventListener('click', (e) => e.stopPropagation());
        }
    };

    const positionInfobox = (targetLiElement) => {
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
    };

    const toggleInfobox = (itemIndex, targetLiElement) => {
        createInfoboxElement();
        const item = fullItemsForCurrentPage[itemIndex];
        if (!item) {
            errorHandler(new Error(`Infobox: Item not found at index ${itemIndex}`));
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
                keySp.textContent = `${formatFieldKey(key, label)} : `;
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
        if (aggregationTypeForItem === "departement_specifique" && item.hasOwnProperty("communesDetails")) {
            if (Array.isArray(item.communesDetails) && item.communesDetails.length > 0) {
                const li = document.createElement('li');
                const keySp = document.createElement('span');
                keySp.className = 'infobox-detail-key';
                keySp.textContent = `${formatFieldKey("communesDetails", "Lieux (Commune (Dépt.))")} : `;
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
    };

    const hideInfobox = () => {
        if (infoboxElement) {
            infoboxElement.classList.remove('infobox-visible');
            currentlyDisplayedInfoboxItemIndex = null;
        }
    };

    // --- FORMATAGE DE TEXTE (NOMS DE CHAMPS) ---

    const formatFieldKey = (key, defaultLabel = null) => {
        if (defaultLabel) return defaultLabel;
        let formatted = key.replace(/([A-Z])/g, ' $1').toLowerCase();
        formatted = formatted.charAt(0).toUpperCase() + formatted.slice(1);
        formatted = formatted.replace(/id$/i, "ID").replace(/^Cd /i, "Code ").replace(/Lb /i, "");
        formatted = formatted.replace("code Insee", "Code INSEE");

        const replacements = {
            nomVernaculaire: "Nom vernaculaire",
            nomScientifiqueRef: "Nom scientifique",
            totalObservationsEspece: "Total observations",
            departements: "Départements",
            communesDetails: "Lieux (Commune (Dépt.))",
            statuts: "Statuts"
        };
        return replacements[key] || formatted.trim();
    };

    // --- GESTION DE LA PAGINATION ---

    const renderPaginationControls = (hasResults) => {
        const existingPagination = finalResultsContentElement.querySelector('.pagination-controls');
        if (existingPagination) existingPagination.remove();
        if (!hasResults || totalPages <= 1) return;

        const paginationDiv = document.createElement('div');
        paginationDiv.className = 'pagination-controls';

        const createButton = (label, clickHandler, isDisabled = false, title = '', arrowImage = null) => {
            const button = document.createElement('button');
            if (arrowImage) {
                const arrowImageEl = document.createElement('img');
                arrowImageEl.src = arrowImage;
                arrowImageEl.alt = label;
                arrowImageEl.classList.add('pagination-arrow-icon');
                button.appendChild(arrowImageEl);
            } else {
                button.textContent = label;
            }
            button.title = title;
            button.disabled = isDisabled;
            button.addEventListener('click', clickHandler);
            return button;
        };

        const prevButton = createButton('Précédent', () => { hideInfobox(); fetchPaginatedResults(currentPage - 1); }, currentPage === 1, 'Page précédente', 'ressources/arrow/precedent.webp');
        const nextButton = createButton('Suivant', () => { hideInfobox(); fetchPaginatedResults(currentPage + 1); }, currentPage === totalPages, 'Page suivante', 'ressources/arrow/suivant.webp');

        const pageInputContainer = document.createElement('div');
        pageInputContainer.className = 'page-input-container';

        const pageInputLabel = document.createElement('label');
        pageInputLabel.htmlFor = 'page-number-input';
        pageInputLabel.textContent = 'Page :';
        pageInputLabel.className = 'page-input-label';

        const pageInput = document.createElement('input');
        pageInput.type = 'number';
        pageInput.id = 'page-number-input';
        pageInput.className = 'page-number-input';
        pageInput.min = '1';
        pageInput.max = totalPages.toString();
        pageInput.value = currentPage.toString();
        pageInput.setAttribute('aria-label', 'Numéro de page à atteindre');

        const totalPagesSpan = document.createElement('span');
        totalPagesSpan.className = 'total-pages-indicator';
        totalPagesSpan.textContent = `/ ${totalPages}`;

        const goToPageButton = createButton('OK', () => {
            const pageNum = parseInt(pageInput.value, 10);
            if (!isNaN(pageNum) && pageNum >= 1 && pageNum <= totalPages) {
                hideInfobox();
                fetchPaginatedResults(pageNum);
            } else {
                pageInput.value = currentPage.toString();
                alert(`Veuillez entrer un numéro de page valide entre 1 et ${totalPages}.`);
            }
        }, false, 'Aller à la page spécifiée');

        pageInput.addEventListener('keypress', (e) => { if (e.key === 'Enter') { e.preventDefault(); goToPageButton.click(); } });

        pageInputContainer.appendChild(pageInputLabel);
        pageInputContainer.appendChild(pageInput);
        pageInputContainer.appendChild(totalPagesSpan);

        paginationDiv.appendChild(prevButton);
        paginationDiv.appendChild(pageInputContainer);
        paginationDiv.appendChild(goToPageButton);
        paginationDiv.appendChild(nextButton);

        finalResultsContentElement.appendChild(paginationDiv);
    };

    const fetchPaginatedResults = async (page) => {
        if (!resultsConversationId) {
            displayMessage("Session de résultats invalide. Relance d'une recherche...", "bot");
            clearResultDisplayArea();
            setTimeout(() => startConversation(false), 2000);
            return;
        }

        const requestedPage = parseInt(page, 10);
        if (isNaN(requestedPage) || requestedPage < 1 || (totalPages > 0 && requestedPage > totalPages)) {
            const pageNumInput = document.getElementById('page-number-input');
            if (pageNumInput) pageNumInput.value = currentPage.toString();
            if (totalPages > 0) {
                alert(`Numéro de page invalide. Entrez un nombre entre 1 et ${totalPages}.`);
            }
            return;
        }

        try {
            const data = await fetchAPI(`${API_BASE_URL}/chat/results/${resultsConversationId}/page/${requestedPage}`);
            if (data.error) throw new Error(data.error);

            if (data.results_data) {
                displayPaginatedResults(data.results_data, resultsConversationId);
            } else {
                displayMessage("Aucune donnée reçue pour cette page.", "bot");
            }
        } catch (error) {
            errorHandler(error, 'Erreur pagination:', () => renderPaginationControls(fullItemsForCurrentPage.length > 0 || totalPages > 0));
        }
    };

    // --- GESTION DU CHATBOT (QUESTIONS/REPONSES) ---

    const startConversation = async (isInitialLoad = false) => {
        if (isInitialLoad) {
            clearResultDisplayArea();
            resultsConversationId = null;
            fullItemsForCurrentPage = [];
            currentAggregationType = 'unknown';
            const placeholder = document.createElement('div');
            placeholder.className = 'results-message initial-placeholder';
            placeholder.textContent = "Les résultats de ta recherche apparaîtront ici...";
            finalResultsContentElement.appendChild(placeholder);
        }
        chatLog.innerHTML = '';
        setInputState(false);
        consecutiveSkips = 0;

        displayMessage('Coucou 👋🏻 Prêt(e) pour une nouvelle recherche ? Plus tu es précis(e), plus je pourrai t\'aider !', "bot");
        try {
            const data = await fetchAPI(`${API_BASE_URL}/chat/start`, { method: 'POST', headers: { 'Content-Type': 'application/json' } });
            if (data.error) throw new Error(data.error);

            conversationId = data.conversation_id;

            if (data.question && data.question.text) {
                displayMessage(data.question.text, 'bot');
                setInputState(true, data.question.is_skippable || false);
            } else {
                displayMessage("Aucune question initiale reçue !", "bot");
                setInputState(false);
            }
        } catch (error) {
            errorHandler(error, "Oups, j'ai une petite erreur. Nouvelle tentative...", () => startConversation(isInitialLoad));
        }
    };

    const handleSend = async (messageToSend) => {
        if (!conversationId) {
            displayMessage("Session de questions non active. Relance...", 'bot');
            setTimeout(() => startConversation(false), 2000);
            return;
        }

        setInputState(false);
        hideInfobox();


    // Gesion du compteur de "skip" consécutifs
    if (messageToSend.toLowerCase() === "passer") {
        consecutiveSkips++;
    } else {
        consecutiveSkips = 0;
    }

    if (consecutiveSkips >= MAX_CONSECUTIVE_SKIPS) {
        displayMessage("Il faut que tu m'aides à préciser mes réponses. 😊 Allez, je te laisse une autre chance !", 'bot'); // VOTRE MESSAGE PERSONNALISÉ
        consecutiveSkips = 0;
        setInputState(false);
        setTimeout(() => {
            startConversation(false);
        }, 5000);
        return;
    }

        try {
            const data = await fetchAPI(`${API_BASE_URL}/chat/send`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: messageToSend, conversation_id: conversationId }),
            });

            if (data.error) {
                displayMessage(`Erreur serveur: ${data.error}`, 'bot');
                setInputState(true, currentQuestionIsSkippable);
            } else if (data.is_final_questions && data.results_data) {
                displayMessage("J'ai cherché pour toi, voici les résultats à droite !", "bot");
                displayPaginatedResults(data.results_data, data.conversation_id);
                displayMessage("C'est affiché ! Je reviens dans un instant...", "bot");
                setTimeout(() => startConversation(false), 2000);
            } else if (data.question && data.question.text) {
                displayMessage(data.question.text, 'bot');
                setInputState(true, data.question.is_skippable || false);
            } else {
                displayMessage("Oups, réponse inattendue. Relance...", 'bot');
                setTimeout(() => startConversation(false), 2000);
            }
        } catch (error) {
            errorHandler(error, 'Erreur envoi message:', () => setInputState(true, currentQuestionIsSkippable));
        }
    };

    // --- EVENEMENTS UTILISATEUR ---

    document.addEventListener('click', (event) => {
        if (infoboxElement && infoboxElement.classList.contains('infobox-visible')) {
            hideInfobox();
        }
    });

    sendButton.addEventListener('click', () => {
        const messageText = chatInput.value.trim();
        if (!messageText || chatInput.disabled) return;
        displayMessage(messageText, 'user');
        chatInput.value = '';
        handleSend(messageText);
    });

    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !chatInput.disabled) {
            sendButton.click(); // Déclenche l'événement click sur le bouton "Envoyer"
        }
    });

    skipButton.addEventListener('click', () => {
        displayMessage("<i>(Je ne sais pas)</i>", 'user', true);
        chatInput.value = '';
        handleSend("passer");
    });

    // --- INITIALISATION ---

    startConversation(true);
});