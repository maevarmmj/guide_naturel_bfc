// On attend que le document initial html soit complètement chargé...
document.addEventListener('DOMContentLoaded', () => {

    // *** CONSTANTES ***
    const API_BASE_URL = 'http://localhost:5000';
    // Définies dans le recherche.html avec leur ID
    const chatLog = document.getElementById('chat-log');
    const chatInput = document.getElementById('chat-input');
    const sendButton = document.getElementById('send-chat-button');
    const skipButton = document.getElementById('skip-chat-button');
    const finalResultsContentElement = document.getElementById('final-chatbot-results-content');
    const resultsSearchBarContainer = document.getElementById('results-search-bar-container');
    const speciesSearchInput = document.getElementById('species-search-input');
    const speciesSearchButton = document.getElementById('species-search-button');
    const speciesSuggestionsList = document.getElementById('species-suggestions-list');

    const MAX_CONSECUTIVE_SKIPS = 6; // Nombre de skips max avant de relancer le chatbot

    // Icônes lors de l'affichage des résultats
    const taxoIcons = {
        "Amphibiens et reptiles": "🦎",
        "Autres": "🪨",
        "Crabes, crevettes, cloportes et mille-pattes": "🦐",
        "Escargots et autres mollusques": "🐌",
        "Insectes et araignées": "🐜",
        "Mammifères": "🐻",
        "Oiseaux": "🕊️",
        "Poissons": "🐟",
        "Champignons et lichens": "🍄",
        "Plantes, mousses et fougères": "🌿"
    };

    /// *** VARIABLES GLOBALES ***
    let conversationId = null;
    let resultsConversationId = null;
    let currentQuestionIsSkippable = false;
    let currentPage = 1;
    let totalPages = 1;
    let totalItemsOverall = 0;
    let fullItemsForCurrentPage = [];
    let originalFullItemsForCurrentPage = [];
    let isCurrentlyLocallyFiltered = false;

    let currentAggregationType = "unknown";
    let infoboxElement = null;
    let currentlyDisplayedInfoboxItemIndex = null;
    let consecutiveSkips = 0;


    // *** FONCTIONS UTILITAIRES ***

    // Afficher un nouveau message dans le chat
    // Paramètres : message (le message à envoyer), sender (la personne qui envoie), isHtml (interprétation d'un simple txt ou code html)
    const displayMessage = (message, sender, isHtml = false) => {
        const p = document.createElement('p');
        if (isHtml) {
            p.innerHTML = message; // Si par ex il y a du texte en italique ("Je ne sais pas")
        }
        else {
            p.textContent = message; // Par défaut
        }
        p.classList.add(sender === 'user' ? 'user-message' : 'bot-message'); // Message de l'utilisateur ou du chatbot ?
        chatLog.appendChild(p); // on ajoute le nouveau paragraphe créé dans le html (chat-log)
        requestAnimationFrame(() => requestAnimationFrame(() => p.classList.add('visible')));
        chatLog.scrollTop = chatLog.scrollHeight;
    };

    // Gère l'état des éléments d'entrée de l'utilisateur
    const setInputState = (enable, isSkippable = false) => {
        chatInput.disabled = !enable; // Pas activé par défaut
        sendButton.disabled = !enable;
        currentQuestionIsSkippable = enable && isSkippable; // Nouvelle variable bool
        if (skipButton) {
            skipButton.disabled = !currentQuestionIsSkippable; // Active/désactive le bouton skip en fonction de la situation
        }
        if (enable) {
            chatInput.focus(); // "Active" le chat input
        }
    };

    // Message d'erreur envoyé dans le chat
    const errorHandler = async (error, message = "Oups, une erreur s'est produite !", retry = null) => {
        console.error(message, error);
        displayMessage(`${message} ${error.message || error}`, 'bot');
        if (retry) {
            setTimeout(retry, 5000);
        }
    };

    // Nettoyage complet de la zone des résultats de la recherche
    const clearResultDisplayArea = () => {
        // Si l'élément existe bien :
        if (finalResultsContentElement) {
            finalResultsContentElement.innerHTML = ''; // Tous les enfants de l'élement sont retirés du DOM
        }
        hideInfobox();
        if (resultsSearchBarContainer) {
            resultsSearchBarContainer.style.display = 'none'; // Cache la barre de recherche
        }
        if (speciesSearchInput) {
            speciesSearchInput.value = '';
        }
        if (speciesSuggestionsList) {
            speciesSuggestionsList.innerHTML = '';
            speciesSuggestionsList.style.display = 'none';
        }
        isCurrentlyLocallyFiltered = false; // Réinitialisationd de cette variable
    };

    // Fonction qui prend une URL et des options de requête et qui utilise fetch pour envoyer une requête au serveur
    // de manièer asynchrone
    const fetchAPI = async (url, options = {}) => {
        try {
            const response = await fetch(url, options);
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ error: `Erreur HTTP: ${response.status}` }));
                throw new Error(errorData.error || `Erreur HTTP ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error(`Erreur FetchAPI pour ${url}:`, error);
            throw error;
        }
    };

    // Curseur de chargement CSS (show et hide)
    const showLoadingCursor = () => {
        document.body.style.cursor = 'wait';
    };

    const hideLoadingCursor = () => {
        document.body.style.cursor = 'default';
    };

// *** GESTION DE L'AFFICHAGE DES RESULTATS (LISTE + INFOS) ***
//   * resultsData: un objet contenant les données des résultats (items, message, infos de pagination)
//   * convIdForTheseResults: L'ID de conversation associé à ces résultats (pour la pagination backend)
const displayPaginatedResults = (resultsData, convIdForTheseResults) => {
    // Vérifie si l'élément HTML principal pour afficher les résultats existe
    if (!finalResultsContentElement) {
        errorHandler(new Error("Zone d'affichage des résultats non trouvée."), "Erreur critique d'interface.");
        return;
    }

    // Si isCurrentlyLocallyFiltered est FAUX, cela signifie qu'on affiche
    // des résultats "frais" venant du backend (pas un filtre local)
    if (!isCurrentlyLocallyFiltered) {
        clearResultDisplayArea();
        // Met à jour l'ID de conversation global pour les résultats, utilisé par la pagination backend
        resultsConversationId = convIdForTheseResults;
    } else {
        // Affichage des résultats d'un filtre local.
        // On cible et supprime spécifiquement la liste des résultats précédente
        const listToClear = finalResultsContentElement.querySelector('.results-list');
        if (listToClear) {
            listToClear.remove();
        }
        // On cible et supprime le message spécifique "aucun résultat local trouvé" s'il existe
        const noLocalMsg = finalResultsContentElement.querySelector('.no-local-results-message');
        if (noLocalMsg) noLocalMsg.remove();
    }

    // Met à jour le type d'agrégation actuel basé sur les données reçues
    currentAggregationType = resultsData.aggregation_type || 'unknown'; // Utilise 'unknown' si 'aggregation_type' n'est pas fourni dans 'resultsData'

    // Extrait les propriétés de l'objet 'resultsData' dans des constantes locales pour un accès facile
    const { items, message, page, total_pages, total_items } = resultsData;

    // Si on n'est PAS en mode filtre local (on affiche des données du backend)
    if (!isCurrentlyLocallyFiltered) {
        // Met à jour les variables globales de pagination avec les informations de la page actuelle du backend
        currentPage = parseInt(page, 10); // Numéro de la page actuelle
        totalPages = parseInt(total_pages, 10); // Nombre total de pages disponibles
        totalItemsOverall = parseInt(total_items, 10); // Nombre total d'items pour cette recherche

        fullItemsForCurrentPage = items || []; // Stocke les items à afficher sur la page actuelle, utilise un tableau vide si "items" est null/undefined

        originalFullItemsForCurrentPage = [...fullItemsForCurrentPage]; // Crée une nouvelle copie du tableau fullItemsForCurrentPage
    }
    else {
        fullItemsForCurrentPage = items || [];
    }

    // Gestion de visibilité de la barre de recherche locale
    if (resultsSearchBarContainer) {
        resultsSearchBarContainer.style.display = originalFullItemsForCurrentPage.length > 0 ? 'flex' : 'none';
    }

    // Supprime les éventuels messages de résumé ou de "pas de résultats" des affichages précédents
    const existingSummary = finalResultsContentElement.querySelector('.results-summary');
    if(existingSummary) existingSummary.remove();
    const existingNoResults = finalResultsContentElement.querySelector('.results-message.no-results-message');
    if(existingNoResults) existingNoResults.remove();


    // Si la liste des items à afficher (rappel "fullItemsForCurrentPage") est vide.
    if (fullItemsForCurrentPage.length === 0) {
        const messageDiv = document.createElement('div'); // Crée un élément 'div' pour afficher un message

        messageDiv.className = 'results-message no-results-message'; // Class CSS pour le style

        if (isCurrentlyLocallyFiltered) {
            messageDiv.textContent = `Aucune espèce trouvée pour "${speciesSearchInput.value.trim()}" dans les résultats de cette page... Cherche peut-être sur une autre page ?`;
        } else {
            messageDiv.textContent = message || "Aucun résultat trouvé pour ces critères !";
        }
        // Ajoute ce message à la zone des résultats
        finalResultsContentElement.appendChild(messageDiv);
    }


    // Si la liste des items à afficher n'est PAS vide
    if (fullItemsForCurrentPage.length > 0) {

        // Crée un élément de liste non ordonnée (<ul>) pour afficher les résultats
        const resultsList = document.createElement('ul');
        resultsList.className = 'results-list'; // Class CSS

        // Boucle sur chaque item dans fullItemsForCurrentPage.
        fullItemsForCurrentPage.forEach((item) => {
            const li = document.createElement('li'); // Création d'un élément de liste (<li>)
            li.className = 'result-item-clickable'; // Class CSS pour le style

            // Récupère le nom vernaculaire et scientifique, avec "N/A" par défaut si non présents
            const nomVern = item.nomVernaculaire;
            const nomSci = item.nomScientifiqueRef || 'N/A';
            const groupeTaxoSimple = item.groupeTaxoSimple || "Autres";
            const taxoIcon = taxoIcons[groupeTaxoSimple] || taxoIcons["Autres"];

            li.textContent = `${taxoIcon} ${nomVern} (${nomSci})`; // Formattage de l'élément de la liste

            // Trouve l'index de cet item dans la liste originalFullItemsForCurrentPage.
            const originalIndex = originalFullItemsForCurrentPage.findIndex(origItem =>
                (origItem.nomScientifiqueRef === item.nomScientifiqueRef && origItem.nomVernaculaire === item.nomVernaculaire) ||
                (origItem._id && item._id && origItem._id === item._id) // Utilise _id si disponible (plus robuste)
            );

            // Si l'item a été trouvé dans la liste originale
            if (originalIndex !== -1) {
                li.dataset.itemOriginalIndex = originalIndex.toString();
                li.addEventListener('click', (event) => {
                    event.stopPropagation(); // Empêche le clic de se propager à des éléments parents (comme le document qui ferme l'infobox)
                    toggleInfobox(originalIndex, li); // Afficher/cacher l'infobox
                });
            } else {
                console.warn("Item filtré non trouvé dans la liste originale:", item);
                li.style.opacity = "0.5";
            }
            // Ajoute l'élément li (l'espèce) à la liste ul
            resultsList.appendChild(li);
        });
        finalResultsContentElement.appendChild(resultsList);
    }

    // Affiche le message de résumé (ex: "Page X sur Y...") si on n'est PAS en mode filtre local
    if (message && !isCurrentlyLocallyFiltered && (originalFullItemsForCurrentPage.length > 0 || totalItemsOverall > 0)) {
        const summaryDiv = document.createElement('div');
        summaryDiv.className = 'results-summary';
        summaryDiv.textContent = message;
        finalResultsContentElement.appendChild(summaryDiv);
    }

    // Gère l'affichage des contrôles de pagination
    if (!isCurrentlyLocallyFiltered) {
        // Si on n'est pas en mode filtre local, affiche la pagination normale (basée sur les données du backend)
        renderPaginationControls(totalItemsOverall > 0);
    } else {
        // Si on est en mode filtre local, on cache la pagination globale
        const pagination = finalResultsContentElement.querySelector('.pagination-controls');
        if (pagination) pagination.style.display = 'none';
    }
};

    // Création de l'infobox des espèces
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

    // Réglage de la positiond de l'infobox
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
        let top = targetRect.bottom + scrollTop + 5;
        let left = targetRect.left + scrollLeft;
        if (top + infoboxRect.height + margin > viewportHeight + scrollTop) {
            top = targetRect.top + scrollTop - infoboxRect.height - margin - 5;
        }
        if (top < scrollTop + margin) top = scrollTop + margin;
        if (left + infoboxRect.width + margin > viewportWidth + scrollLeft) {
            left = viewportWidth + scrollLeft - infoboxRect.width - margin;
        }
        if (left < scrollLeft + margin) left = scrollLeft + margin;
        infoboxElement.style.top = `${Math.max(0, top)}px`;
        infoboxElement.style.left = `${Math.max(0, left)}px`;
    };

    // Afficher/retirer l'infobox
    const toggleInfobox = (itemOriginalIndex, targetLiElement) => {

        createInfoboxElement(); // Création de l'infobox

        const item = originalFullItemsForCurrentPage[itemOriginalIndex];
        if (!item) {
            errorHandler(new Error(`Infobox: Item non trouvé à l'index original ${itemOriginalIndex}.`));
            return;
        }
        if (infoboxElement.classList.contains('infobox-visible') && currentlyDisplayedInfoboxItemIndex === itemOriginalIndex) {
            hideInfobox(); // Masquage de l'infobox
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
            nomScientifiqueRef: "Nom scientifique", regne: "Règne", groupeTaxoSimple: "Groupe taxonomique",
            totalObservationsEspece: "Total observations", departements: "Départements d'observation", statuts: "Statuts observés"
        }; // Catégories à afficher dans l'infobox

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

        // Agrégation de certaines informations (on récupère l'aggregation_type s'il existe)
        const aggregationTypeForItem = item.aggregation_type || currentAggregationType;

        // Si on doit afficher les détails des communes
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
        currentlyDisplayedInfoboxItemIndex = itemOriginalIndex;
    };

    // Masquage de l'infobox (si elle existe)
    const hideInfobox = () => {
        if (infoboxElement) {
            infoboxElement.classList.remove('infobox-visible');
            currentlyDisplayedInfoboxItemIndex = null;
        }
    };

    // Formattage pour l'infobox
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

    // *** GESTION DE LA PAGINATION ***

// hasResults: un bool qui est VRAI s'il y a des résultats à paginer
const renderPaginationControls = (hasResults) => {
    // Recherche dans finalResultsContentElement (la zone des résultats) un élément existant
    // avec la class CSS .pagination-controls
    const existingPagination = finalResultsContentElement.querySelector('.pagination-controls');
    if (existingPagination) {
        existingPagination.remove(); // les supprime pour éviter les duplications
    }

    if (!hasResults || totalPages <= 1) { // S'il n'y a aucun résultat ou qu'il n'y a qu'une seule page ou moins
        return;
    }

    const paginationDiv = document.createElement('div');
    paginationDiv.className = 'pagination-controls';

    // Fonction interne nommée createButton :
    const createButton = (label, clickHandler, isDisabled = false, title = '', arrowImage = null) => {
        const button = document.createElement('button');
        if (arrowImage) {
            const arrowImageEl = document.createElement('img');
            arrowImageEl.src = arrowImage;
            arrowImageEl.alt = label;
            arrowImageEl.classList.add('pagination-arrow-icon'); // Class CSS pour le style de l'icône
            button.appendChild(arrowImageEl); // Ajoute l'image à l'intérieur du bouton
        } else {
            button.textContent = label;
        }
        button.title = title;
        button.disabled = isDisabled;

        // Ecouteur d'événement pour le clic sur le bouton
        button.addEventListener('click', () => {
            isCurrentlyLocallyFiltered = false;
            if (speciesSearchInput){
                speciesSearchInput.value = '';
            }
            if (speciesSuggestionsList) {
                speciesSuggestionsList.innerHTML = '';
                speciesSuggestionsList.style.display = 'none';
            }
            hideInfobox(); // Cache l'infobox


            showLoadingCursor();

            clickHandler(); // Exécute la fonction 'clickHandler' passée en argument (ex: fetchPaginatedResults).
        });
        return button; // Renvoie le bouton créé.
    };

    // BOUTON PRECEDENT - Lorsqu'il est cliqué, il appelle 'fetchPaginatedResults' pour la page précédente
    const prevButton = createButton(
        'Précédent',
        () => fetchPaginatedResults(currentPage - 1),
        currentPage === 1,
        'Page précédente',
        '../static/ressources/arrow/precedent.webp'
    );

    // BOUTON SUIVANT : Appelle 'fetchPaginatedResults' pour la page suivante.
    const nextButton = createButton(
        'Suivant',
        () => fetchPaginatedResults(currentPage + 1),
        currentPage === totalPages,
        'Page suivante',
        '../static/ressources/arrow/suivant.webp'
    );

    // Champ de saisie du numéro de page
    const pageInputContainer = document.createElement('div');
    pageInputContainer.className = 'page-input-container'; // Class CSS

    // Label pour le champ de saisie
    const pageInputLabel = document.createElement('label');
    pageInputLabel.htmlFor = 'page-number-input'; // Lie le label à l'input par son ID
    pageInputLabel.textContent = 'Page :';
    pageInputLabel.className = 'page-input-label';

    // Pour la saisie du n° de page
    const pageInput = document.createElement('input');
    pageInput.type = 'number';
    pageInput.id = 'page-number-input'; // ID pour le lier au label et pour le JS
    pageInput.className = 'page-number-input';
    pageInput.min = '1';
    pageInput.max = totalPages.toString();
    pageInput.value = currentPage.toString();
    pageInput.setAttribute('aria-label', 'Numéro de page à atteindre');

    // Crée un span pour afficher le nombre total de pages (ex: "/ 10").
    const totalPagesSpan = document.createElement('span');
    totalPagesSpan.className = 'total-pages-indicator';
    totalPagesSpan.textContent = `/ ${totalPages}`;

    // Bouton "OK" pour valider la saisie du numéro de page.
    const goToPageButton = createButton(
        "OK",
        () => {
            const pageNum = parseInt(pageInput.value, 10); // Convertit la valeur de l'input en nombre
            if (!isNaN(pageNum) && pageNum >= 1 && pageNum <= totalPages) {
                fetchPaginatedResults(pageNum); // Charge la page demandée
            } else {
                pageInput.value = currentPage.toString();
                alert(`Veuillez entrer un numéro de page valide entre 1 et ${totalPages}.`);
            }
        },
        false,
        "Aller à la page spécifiée"
    );

    // Ecouteur si une touche du clavier est pressée
    pageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault(); // Empêche le comportement par défaut
            goToPageButton.click();
        }
    });

    // Assemble les éléments du conteneur de saisie de page
    pageInputContainer.appendChild(pageInputLabel);
    pageInputContainer.appendChild(pageInput);
    pageInputContainer.appendChild(totalPagesSpan);

    // Assemble tous les contrôles dans le conteneur principal 'paginationDiv'
    paginationDiv.appendChild(prevButton);
    paginationDiv.appendChild(pageInputContainer);
    paginationDiv.appendChild(goToPageButton);
    paginationDiv.appendChild(nextButton);

    // Ajoute le conteneur de pagination complet à la zone d'affichage des résultats
    if(finalResultsContentElement) {
        finalResultsContentElement.appendChild(paginationDiv);
    }
};

    // LA fonction qui permet de charger une nouvelle page (param : la page à afficher)
    const fetchPaginatedResults = async (page) => {
        if (!resultsConversationId) {
            displayMessage("Session de résultats invalide. Relance d'une recherche...", "bot");
            clearResultDisplayArea();
            setTimeout(() => startConversation(false), 2000);
            hideLoadingCursor();
            return;
        }

        const requestedPage = parseInt(page, 10);

        if (isNaN(requestedPage) || requestedPage < 1 || (totalPages > 0 && requestedPage > totalPages && totalPagesOverall > 0)) {
            const pageNumInput = document.getElementById('page-number-input');
            if (pageNumInput) pageNumInput.value = currentPage.toString();
            if (totalPages > 0 && totalPagesOverall > 0) {
                alert(`Numéro de page invalide. Entrez un nombre entre 1 et ${totalPages}.`);
            }
            hideLoadingCursor();
            return;
        }

        // showLoadingCursor() est maintenant appelé dans le handler du bouton de pagination
        try {
            const data = await fetchAPI(`${API_BASE_URL}/chat/results/${resultsConversationId}/page/${requestedPage}`);
            if (data.error) throw new Error(data.error);
            if (data.results_data) {
                isCurrentlyLocallyFiltered = false;
                displayPaginatedResults(data.results_data, resultsConversationId);
            } else {
                displayMessage("Aucune donnée reçue pour cette page.", "bot");
            }
        } catch (error) {
            errorHandler(error, 'Erreur pagination:', () => renderPaginationControls(totalItemsOverall > 0));
        } finally {
            hideLoadingCursor();
        }
    };


    // *** FONCTIONS POUR LA RECHERCHE LOCALE DANS LES RÉSULTATS ***
    const filterAndDisplayLocalSpeciesResults = () => {
        if (!speciesSearchInput) return;
        const searchTerm = speciesSearchInput.value.trim().toLowerCase();
        hideInfobox();
        if (speciesSuggestionsList) speciesSuggestionsList.style.display = 'none';

        if (!searchTerm) {
            if (isCurrentlyLocallyFiltered) {
                isCurrentlyLocallyFiltered = false;
                displayPaginatedResults({
                    items: originalFullItemsForCurrentPage,
                    message: `Page ${currentPage} sur ${totalPages} (${totalItemsOverall} espèces au total trouvées)`,
                    page: currentPage,
                    total_pages: totalPages,
                    total_items: totalItemsOverall
                }, resultsConversationId);
            }
            return;
        }

        const filteredItems = originalFullItemsForCurrentPage.filter(item =>
            item.nomScientifiqueRef && item.nomScientifiqueRef.toLowerCase().includes(searchTerm)
        );

        isCurrentlyLocallyFiltered = true;
        displayPaginatedResults({
            items: filteredItems,
            message: '',
            page: 1,
            total_pages: 1,
            total_items: filteredItems.length
        }, resultsConversationId);
    };


    // *** GESTION DU CHATBOT (QUESTIONS/REPONSES) ***
    const startConversation = async (isInitialLoad = false) => {
        if (isInitialLoad) {
            clearResultDisplayArea();
            resultsConversationId = null;
            fullItemsForCurrentPage = [];
            originalFullItemsForCurrentPage = [];
            isCurrentlyLocallyFiltered = false;
            currentAggregationType = 'unknown';
            currentPage = 1;
            totalPages = 1;
            totalItemsOverall = 0;
            const placeholder = document.createElement('div');
            placeholder.className = 'results-message initial-placeholder';
            placeholder.textContent = "Les résultats de ta recherche apparaîtront ici...";
            finalResultsContentElement.appendChild(placeholder);
        }
        chatLog.innerHTML = '';
        setInputState(false);
        consecutiveSkips = 0;
        displayMessage('Coucou 👋🏻 Prêt(e) pour une nouvelle recherche ? Plus tu es précis(e), plus je pourrai t\'aider !', "bot");

        showLoadingCursor(); // Curseur d'attente
        try {
            const data = await fetchAPI(`${API_BASE_URL}/chat/start`,{ method: 'POST', headers: { 'Content-Type': 'application/json' } });
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
        } finally {
            hideLoadingCursor();
        }
    };

    // Envoi des messages et génération des résultats
    const handleSend = async (messageToSend) => {
        if (!conversationId) {
            displayMessage("Session de questions non active. Relance...", 'bot');
            setTimeout(() => startConversation(false), 2000);
            return;
        }
        setInputState(false);
        hideInfobox();

        if (messageToSend.toLowerCase() === "passer") {
            consecutiveSkips++;
        } else {
            consecutiveSkips = 0;
        }
        if (consecutiveSkips >= MAX_CONSECUTIVE_SKIPS) {
            displayMessage("Il faut que tu m'aides à préciser mes réponses. 😊 Allez, je te laisse une autre chance !", 'bot');
            consecutiveSkips = 0;
            setInputState(false);
            setTimeout(() => startConversation(false), 5000);
            return;
        }

        showLoadingCursor();
        try {
            const data = await fetchAPI(`${API_BASE_URL}/chat/send`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: messageToSend, conversation_id: conversationId }),
            });

            if (data.error) {
                displayMessage(`Erreur serveur: ${data.error}`, 'bot');
                setInputState(true, currentQuestionIsSkippable);
            }
            else if (data.is_final_questions && data.results_data) {

                consecutiveSkips = 0;
                displayMessage("J'ai cherché pour toi, voici les résultats à droite !", "bot");
                isCurrentlyLocallyFiltered = false;
                if(speciesSearchInput) speciesSearchInput.value = '';
                displayPaginatedResults(data.results_data, data.conversation_id);
                displayMessage("C'est affiché ! Je reviens dans un instant...", "bot");
                setTimeout(() => startConversation(false), 3000);
            }
            else if (data.question && data.question.text) {
                displayMessage(data.question.text, 'bot');
                setInputState(true, data.question.is_skippable || false);
            }
            else {
                displayMessage("Oups, réponse inattendue. Relance...", 'bot');
                setTimeout(() => startConversation(false), 2000);
            }
        }

        catch (error) {
            errorHandler(error, 'Erreur envoi message:', () => setInputState(true, currentQuestionIsSkippable));
        }
        finally {
            hideLoadingCursor();
        }
    };

    // ****** FIN DES FONCTIONS UTILITAIRES *****

    // ********** EVENEMENTS UTILISATEUR ************
    document.addEventListener('click', (event) => {
        if (infoboxElement && infoboxElement.classList.contains('infobox-visible')) {
            if (!infoboxElement.contains(event.target) && !event.target.closest('.result-item-clickable')) {
                hideInfobox();
            }
        }
        if (speciesSuggestionsList && speciesSuggestionsList.style.display === 'block') {
            if (speciesSearchInput && !speciesSearchInput.contains(event.target) && !speciesSuggestionsList.contains(event.target)) {
                speciesSuggestionsList.style.display = 'none';
            }
        }
    });

    if (sendButton) sendButton.addEventListener('click', () => {
        const messageText = chatInput.value.trim();
        if (!messageText || chatInput.disabled) return;
        displayMessage(messageText, 'user');
        chatInput.value = '';
        handleSend(messageText);
    });

    if (chatInput) chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !chatInput.disabled) {
            if (sendButton) sendButton.click();
        }
    });

    if (skipButton) skipButton.addEventListener('click', () => {
        displayMessage("<i>(Je ne sais pas)</i>", 'user', true);
        if (chatInput) chatInput.value = '';
        handleSend("passer");
    });

    if (speciesSearchInput) {
        speciesSearchInput.addEventListener('input', () => {
            const query = speciesSearchInput.value.trim().toLowerCase();
            if (speciesSuggestionsList) {
                speciesSuggestionsList.innerHTML = '';
                speciesSuggestionsList.style.display = 'none';
            }
            if (query.length < 2) {
                if (isCurrentlyLocallyFiltered && query.length === 0) {
                    filterAndDisplayLocalSpeciesResults();
                }
                return;
            }
            const matchedSpecies = originalFullItemsForCurrentPage.filter(item =>
                item.nomScientifiqueRef && item.nomScientifiqueRef.toLowerCase().includes(query)
            ).slice(0, 7);
            if (matchedSpecies.length > 0 && speciesSuggestionsList) {
                matchedSpecies.forEach(item => {
                    const suggestionDiv = document.createElement('div');
                    suggestionDiv.textContent = item.nomScientifiqueRef;
                    suggestionDiv.classList.add('suggestion-item');
                    suggestionDiv.addEventListener('click', () => {
                        speciesSearchInput.value = item.nomScientifiqueRef;
                        speciesSuggestionsList.style.display = 'none';
                        filterAndDisplayLocalSpeciesResults();
                    });
                    speciesSuggestionsList.appendChild(suggestionDiv);
                });
                speciesSuggestionsList.style.display = 'block';
            }
        });
        speciesSearchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                filterAndDisplayLocalSpeciesResults();
                if (speciesSuggestionsList) speciesSuggestionsList.style.display = 'none';
            }
        });
    }

    if (speciesSearchButton) {
        speciesSearchButton.addEventListener('click', () => {
            filterAndDisplayLocalSpeciesResults();
            if (speciesSuggestionsList) speciesSuggestionsList.style.display = 'none';
        });
    }

    // ***** INITIALISATION *****
    startConversation(true);
    hideLoadingCursor();
});