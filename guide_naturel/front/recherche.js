document.addEventListener('DOMContentLoaded', () => {
    const chatLog = document.getElementById('chat-log');
    const chatInput = document.getElementById('chat-input');
    const sendButton = document.getElementById('send-chat-button');
    // Cible le conteneur spécifique pour les résultats finaux
    const finalResultsContentElement = document.getElementById('final-chatbot-results-content');

    // MODIFIEZ CETTE URL SI VOTRE BACKEND TOURNE AILLEURS/SUR UN AUTRE PORT
    const API_BASE_URL = 'http://localhost:5001'; // Port de l'exemple Python précédent

    let conversationId = null;

function addMessageToLog(message, sender) {
    const p = document.createElement('p');
    p.textContent = message;
    p.classList.add(sender === 'user' ? 'user-message' : 'bot-message');
    // p.style.opacity = 0; // Optionnel: Forcer l'opacité à 0 avant l'ajout au DOM, mais le CSS devrait suffire

    chatLog.appendChild(p);

    // Forcer un reflow/repaint avant d'ajouter la classe 'visible'
    // Cela garantit que la transition se déclenche correctement
    // requestAnimationFrame est plus propre que setTimeout(0) pour ça.
    requestAnimationFrame(() => {
        requestAnimationFrame(() => { // Double requestAnimationFrame est une astuce robuste
            p.classList.add('visible');
        });
    });
    // Alternative plus simple mais parfois moins fiable sur certains navigateurs :
    // setTimeout(() => {
    //     p.classList.add('visible');
    // }, 10); // Un très court délai

    chatLog.scrollTop = chatLog.scrollHeight;
}

function displayFinalResults(resultsText) {
    if (finalResultsContentElement) {
        finalResultsContentElement.textContent = resultsText;
    } else {
        addMessageToLog("Zone de résultats non trouvée.", "bot");
        addMessageToLog(resultsText, "bot");
    }

    // L'input et le bouton sont déjà désactivés par la logique d'envoi précédente
    // s'ils n'ont pas été réactivés par une nouvelle question.
    // Mais pour être sûr pour le redémarrage :
    chatInput.disabled = true;
    sendButton.disabled = true;

    addMessageToLog("Recherche terminée. Les résultats sont affichés.", "bot");

    // Option de redémarrage automatique :
    addMessageToLog("Une nouvelle recherche va commencer dans quelques secondes...", "bot");
    conversationId = null; // Très important de réinitialiser l'ID de conversation

    setTimeout(() => {
        // Vider les anciens messages du log avant de redémarrer
        // ou juste laisser les anciens et ajouter les nouveaux.
        // Pour vider :
        // chatLog.innerHTML = ''; // Vider le log visuellement

        // Vider aussi les résultats précédents
        if (finalResultsContentElement) {
            finalResultsContentElement.textContent = ''; // Le placeholder CSS réapparaîtra
        }

        startConversation(); // Redémarrer une nouvelle conversation
    }, 5000); // Délai de 5 secondes (5000 ms), ajustez selon vos préférences
}

async function startConversation() {
    // Vider le log au début d'une nouvelle conversation si pas déjà fait
    // C'est une bonne pratique pour éviter l'accumulation si on ne vide pas dans displayFinalResults
    // chatLog.innerHTML = ''; // Décommentez si vous voulez toujours un log propre au démarrage.

    chatInput.disabled = true;
    sendButton.disabled = true;
   // addMessageToLog("Connexion au chatbot...", "bot");

        try {
            const response = await fetch(`${API_BASE_URL}/chat/start`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                // body: JSON.stringify({}) // Pas de body nécessaire pour /start dans notre exemple
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ error: `Erreur HTTP: ${response.status}` }));
                throw new Error(errorData.error || `Erreur HTTP non spécifiée`);
            }
            const data = await response.json();

            if (data.error) {
                addMessageToLog(`Erreur au démarrage: ${data.error}`, 'bot');
                return;
            }
            conversationId = data.conversation_id;
            if (data.question && data.question.text) {
                addMessageToLog(data.question.text, 'bot');
            }
            chatInput.disabled = false;
            sendButton.disabled = false;
            chatInput.focus();

        } catch (error) {
            console.error('Erreur au démarrage de la conversation:', error);
            addMessageToLog(`Impossible de démarrer le chatbot: ${error.message}. Vérifiez que le serveur Python est lancé.`, 'bot');
        }
    }

    async function sendMessage() {
        const messageText = chatInput.value.trim();
        if (!messageText && !chatInput.dataset.allowEmpty) { // data-allow-empty sur l'input si besoin
            return;
        }

        if (!conversationId) {
            addMessageToLog("Erreur: La conversation n'est pas active.", 'bot');
            return;
        }

        addMessageToLog(messageText, 'user');
        const currentInput = chatInput.value; // Sauvegarder avant de vider pour l'envoi
        chatInput.value = '';
        chatInput.disabled = true;
        sendButton.disabled = true;

        try {
            const response = await fetch(`${API_BASE_URL}/chat/send`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: currentInput, conversation_id: conversationId }),
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ error: `Erreur HTTP: ${response.status}` }));
                throw new Error(errorData.error || `Erreur HTTP non spécifiée`);
            }
            const data = await response.json();

            if (data.error) {
                addMessageToLog(`Erreur du serveur: ${data.error}`, 'bot');
                // En cas d'erreur, on pourrait vouloir réactiver l'input si l'erreur n'est pas fatale
                // Pour l'instant, on le laisse désactivé si le serveur renvoie une erreur.
            } else if (data.is_final && data.results) {
                displayFinalResults(data.results);
            } else if (data.question && data.question.text) {
                addMessageToLog(data.question.text, 'bot');
                chatInput.disabled = false;
                sendButton.disabled = false;
                chatInput.focus();
            } else {
                addMessageToLog("Réponse inattendue du serveur ou fin de la conversation.", 'bot');
                // Laisser l'input désactivé
            }

        } catch (error) {
            console.error('Erreur lors de l\'envoi du message:', error);
            addMessageToLog(`Erreur de communication: ${error.message}. Le serveur est-il toujours actif ?`, 'bot');
            // Laisser l'input désactivé en cas d'erreur réseau/communication
        }
    }

    sendButton.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', (event) => {
        if (event.key === 'Enter' && !chatInput.disabled) {
            sendMessage();
        }
    });

    // Démarrer la conversation au chargement
    startConversation();
});