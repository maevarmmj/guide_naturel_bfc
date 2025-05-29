// On attend que le document initial html soit complètement chargé...
document.addEventListener("DOMContentLoaded", function() {

    // ***** CHARGEMENT DU HEADER ****
    fetch('header.html')
        // Une fois la réponse du serveur reçue), on traite cette réponse.
        // Si réponse http ok, 'response.text()' lit le corps de la réponse comme du texte brut (le contenu HTML du header)
        .then(response => response.ok ? response.text() : Promise.reject(response.status + " " + response.statusText))

        // Si la lecture du texte a réussi, 'data' contient le HTML du header
        .then(data => {
            // Sélectionne l'élément HTML dans la page actuelle qui a l'ID 'header-placeholder'
            const headerPlaceholder = document.getElementById('header-placeholder');

            if (headerPlaceholder) {
                // Insère le contenu HTML du header (contenu dans 'data') à l'intérieur de l'élément placeholder
                headerPlaceholder.innerHTML = data;

            } else {
                // Si le placeholder n'est pas trouvé...
                console.error("Placeholder pour le header non trouvé !");
            }
        })
        // Si une erreur s'est produite à n'importe quelle étape de la promesse fetch (réseau, statut HTTP incorrect, etc.)...
        .catch(error => console.error('Erreur lors du chargement du header:', error));


    // ***** CHARGEMENT DU FOOTER ***
    fetch('footer.html')
        .then(response => response.ok ? response.text() : Promise.reject(response.status + " " + response.statusText))
        .then(data => {
            const footerPlaceholder = document.getElementById('footer-placeholder');
            if (footerPlaceholder) {
                footerPlaceholder.innerHTML = data;
                // Une fois le footer chargé et inséré dans le DOM,
                // appelle la fonction 'setupFooterNavListeners' pour configurer les écouteurs d'événements
                // sur les boutons de navigation du footer
                setupFooterNavListeners();
            } else {
                console.error("Placeholder pour le footer non trouvé !");
            }
        })
        .catch(error => console.error('Erreur lors du chargement du footer:', error));
});

/**
 * @function setupFooterNavListeners
 * @description Configure les écouteurs d'événements pour les boutons de navigation dans le footer.
 *              Permet de faire défiler la page vers le haut si l'utilisateur clique sur un lien
 *              qui pointe vers la page actuelle, au lieu de recharger la page.
 *              Si le lien pointe vers une autre page, le comportement de navigation par défaut est conservé.
 */

function setupFooterNavListeners() {
    // Sélectionne les boutons du footer par leurs IDs
    const accueilBtn = document.getElementById('footerBtnAccueil');
    const rechercheBtn = document.getElementById('footerBtnRecherche');
    const aproposBtn = document.getElementById('footerBtnApropos');

    // Détermine le nom du fichier de la page HTML actuellement affichée
    const currentPage = window.location.pathname.split('/').pop() || 'guide_naturel';

    /**
     * @function scrollToTop
     * @description Fonction réutilisable pour faire défiler la fenêtre vers le haut de la page en douceur
     * @param {Event} event - L'objet événement du clic, utilisé pour event.preventDefault()
     */
    const scrollToTop = (event) => {
        // Empêche le comportement par défaut du lien (qui serait de suivre le href)
        event.preventDefault();
        // window.scrollTo pour faire défiler la page.
        window.scrollTo({
            top: 0,
            behavior: 'smooth'// Transition douce
        });
    };

    // Footer : bouton "ACCUEIL"
    if (accueilBtn) {
        // Compare la page actuelle avec la destination du lien "ACCUEIL" ('index.html')
        if (currentPage === 'guide_naturel' || currentPage === '') {
            accueilBtn.addEventListener('click', scrollToTop);
        }
        // Si on n'est PAS sur la page d'accueil, le lien gardera son comportement par défaut
        // (naviguer vers 'index.html' en rechargeant la page).
    }

    // Footer : bouton "RECHERCHE"
    if (rechercheBtn) {
        // Compare la page actuelle avec la destination du lien "RECHERCHE" ('recherche.html')
        if (currentPage === 'recherche') {
            rechercheBtn.addEventListener('click', scrollToTop);
        }
    }

    // Footer : bouton "A PROPOS"
    if (aproposBtn) {
        // Compare la page actuelle avec la destination du lien "A PROPOS" (qui est 'apropos.html').
        if (currentPage === 'apropos') {
            aproposBtn.addEventListener('click', scrollToTop);
        }
    }
}
