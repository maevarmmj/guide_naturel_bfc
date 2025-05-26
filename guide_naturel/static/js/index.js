// Attend que le document HTML initial soit complètement chargé et analysé

document.addEventListener('DOMContentLoaded', function() {

    // Sélectionne toutes les zones cliquables (<area>) de la carte qui ont la classe 'departement-area'
    const departementAreas = document.querySelectorAll('area.departement-area');
    // Sélectionne l'élément <img> utilisé pour afficher une image de survol de département
    const overlayImage = document.querySelector('.overlay-image');
    // Sélectionne l'élément <img> utilisé pour afficher le nom du département
    const overlayText = document.querySelector('.overlay-text');

    // Sélectionne l'élément <canvas> où le graphique principal (camembert) sera dessiné
    const canvasElement = document.getElementById('camembert');
    // Sélectionne les boutons du carousel
    const prevChartBtn = document.querySelector('.carousel-prev');
    const nextChartBtn = document.querySelector('.carousel-next');
    // Sélectionne le <div> qui contiendra le mini-graphique affiché au clic sur un département
    const departementChartContainer = document.getElementById('departement-chart-container');
    // Sélectionne l'élément <canvas> à l'intérieur du conteneur ci-dessus pour le mini-graphique
    const miniDepartementChartCanvas = document.getElementById('mini-departement-chart');

    const chartDotsContainer = document.querySelector('.chart-dots-container');

    // Instances des graphiques Chart.js :
    let camembertChart;
    let miniChartInstance;
    let mainChatData = Array;
    let currentChartIndex = 0;
    // Variable pour suivre quel type de données le graphique principal (et donc le mini-graphique) doit afficher
    // Initialisée à 'default', qui correspond à une clé dans chartDataSets
    let chartKeyValue  = 'default';
    let minichartData = Array;


    // ********** SURVOL DES DEPARTEMENTS *********

    if (overlayImage && overlayText) {
        // Boucle sur chaque zone cliquable de département
        departementAreas.forEach(area => {
            const departementName = area.alt.toLowerCase();
            // Construit les URLs pour les images de survol (image et texte)
            const overlayImageURL = `/static/ressources/dep/${departementName}.png`;
            const overlayTextURL = `/static/ressources/dep/${departementName}_text.png`;

            // Ajoute un écouteur d'événement pour le survol de la souris ('mouseenter')
            area.addEventListener('mouseenter', function() {
                // Met à jour les sources des images de survol
                overlayImage.src = overlayImageURL;
                overlayText.src = overlayTextURL;
                overlayImage.style.opacity = 1;
                overlayText.style.opacity = 1;
            });

            // Ajoute un écouteur d'événement pour lorsque la souris quitte la zone ('mouseleave')
            area.addEventListener('mouseleave', function() {
                overlayImage.style.opacity = 0;
                overlayText.style.opacity = 0;
            });
        });
    } else {
        console.error("Erreur : Élément .overlay-image ou .overlay-text non trouvé.");
    }


    // *********** PARTIE CHART.JS PRINCIPAL ***************

    // Vérifie si l'élément canvas pour le camembert existe
    if (!canvasElement) {
        console.error("L'élément Canvas avec l'ID 'camembert' n'a pas été trouvé");
    }

    // Définit un objet contenant les différents jeux de données pour le graphique principal.
    // Chaque clé (ex: 'default', 'especesParRegne') correspond à un type de graphique
    // que l'utilisateur peut sélectionner via les boutons '.button_right1'

    const chartDataSets = {
        default: {
            labels: ['Animalia', 'Plantae', 'Fungi', 'Bacteria', 'Chromista'],
            data: [1200, 850, 300, 500, 150],
            backgroundColor: ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF'],
            legendLabel: "Nombre d'espèces par règne" },
        especesParRegne: {
            labels: ['Animalia', 'Plantae', 'Fungi', 'Bacteria', 'Chromista'],
            data: [1200, 850, 300, 500, 150],
            backgroundColor: ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF'],
            legendLabel: "Nombre d'espèces par règne" },
        statutsConservationParRegne: {
            labels: ['Préoccupation mineure (LC)', 'Quasi menacée (NT)', 'Vulnérable (VU)', 'En danger (EN)', 'En danger critique (CR)'],
            data: [500, 120, 80, 40, 15],
            backgroundColor: ['#A1E8A1', '#F9E79F', '#F5CBA7', '#F1948A', '#EC7063'],
            legendLabel: "Statuts de conservation (Tous règnes)" },
        especesParStatutConservation: { labels: ['LC', 'NT', 'VU', 'EN', 'CR', 'DD', 'NE'],
            data: [600, 250, 150, 100, 50, 200, 30],
            backgroundColor: ['#76D7C4', '#F7DC6F', '#F0B27A', '#E74C3C', '#C0392B', '#BFC9CA', '#AAB7B8'],
            legendLabel: "Nombre d'espèces par statut UICN" }
    };

    // Définit un objet de configuration commun pour les options du graphique principal (responsivité, la légende, le titre)
    const chartOptionsConfig = {
        responsive: true,
        maintainAspectRatio: true,
        layout: {
            padding: {
                top: 10,
                right: 10,
                bottom: 10,
                left: 10 } },
        plugins: {
            legend: {
                position: 'right',
                align: 'center',
                title: {
                    display: true,
                    padding: 10,
                    color: '#ffffff',
                    font: { weight: 'bold'}
                },
                labels: { color: '#ffffff',
                    font: {
                    family: 'Georgia', size: 10 },
                    boxWidth: 15,
                    padding: 10 }
            },
            title: {
                display: true,
                text: "Statistiques en BFC :",
                color: '#ffffff',
                font: {
                    size: 16,
                    family: 'Georgia',
                    weight: 'bold' },
                padding: {
                    top: 0,
                    bottom: 0 }
            },
        }
    };

    /**
     * @function updateChart
     * @description Met à jour le graphique principal (camembert) avec un nouveau jeu de données
     * @param newDataSet - Les nouvelles données pour nos camemberts
     */

    function updateChart(newDataSet) {
        // Ne fait rien si l'élément canvas n'a pas été trouvé
        if (!canvasElement) return;

        if (!newDataSet) {
            console.error("Jeu de données pour le graphique principal non trouvé!");
            return;
        }

        // Récupère le contexte de dessin 2D du canvas
        const ctx = canvasElement.getContext('2d');

        const chartData = {
            labels: newDataSet.labels,
            datasets: [{
                label: newDataSet.title,
                data: newDataSet.data, // Ce sont les pourcentages
                backgroundColor: newDataSet.backgroundColor,
                borderColor: '#fff',
                borderWidth: 1
            }]
        };

        chartOptionsConfig.plugins.title.text = newDataSet.title;
        chartOptionsConfig.plugins.legend.title.text = newDataSet.legendLabel;
        chartOptionsConfig.plugins.tooltip = {callbacks: {
                                                    label: function(context) {
                                                        let label = context.label || '';
                                                        if (label) {
                                                            label += ': ';
                                                        }
                                                        if (context.parsed !== null) {
                                                            label += context.parsed.toFixed(2) + '%'; // Utilise le pourcentage
                                                        }
                                                        return label;
                                                    },
                                                    afterLabel: function(context) {
                                                        // Afficher le nombre brut d'espèces
                                                        const count = newDataSet.counts[context.dataIndex];
                                                        return `(${count} espèces)`;
                                                    }
                                                }}

        if (camembertChart) {
            camembertChart.data = chartData;
            camembertChart.update();
        } else {
            // Si le graphique n'existe pas encore, le crée :
            camembertChart = new Chart(ctx, {
                type: 'pie',
                data: chartData,
                options: chartOptionsConfig
            });
        }
        updatePaginationDots()
    }


    async function loadChartData(infoParam, pushHistory = true) {
        try {
            // Effectue une requête GET asynchrone vers la route Flask '/get_chart_data'
            // avec le paramètre 'info'.
            const response = await fetch(`/get_chart_data?info=${infoParam}`);

            // Vérifie si la réponse HTTP est OK (statut 200-299)
            if (!response.ok) {
                throw new Error(`Erreur HTTP! statut: ${response.status}`);
            }

            // Récupère les données JSON de la réponse.
            mainChatData = await response.json();

            if (mainChatData.length > 1) {
                prevChartBtn.style.display = 'block'; // Ou 'inline-block' selon votre CSS
                nextChartBtn.style.display = 'block';
            }else {
                prevChartBtn.style.display = 'none';
                nextChartBtn.style.display = 'none';
            }
            createPaginationDots();
            currentChartIndex = 0;
            // Appelle la fonction de rendu pour afficher le graphique avec les nouvelles données.
            updateChart(mainChatData[currentChartIndex]);

            // Synchroniser le bouton actif
            const matchingButton = Array.from(chartButtons).find(btn => btn.dataset.chartkey === infoParam);
            if (matchingButton) {
                setActiveButton(matchingButton);
            }else{
                setActiveButton(chartButtons[0]);
            }


            // Mettre à jour l'URL dans la barre d'adresse du navigateur.
            // Pourquoi : Permet aux utilisateurs de mettre en favori l'état actuel de la page
            //             et d'utiliser les boutons "Retour" / "Avant" du navigateur.
            //             Ceci se fait SANS recharger toute la page.
            if (pushHistory) {
                const newUrl = `/main_page?info=${infoParam}`;
                history.pushState({ info: infoParam }, '', newUrl);
            }
        } catch (error) {
            // Gestion des erreurs lors de la récupération des données.
            // Pourquoi : Afficher un message convivial à l'utilisateur en cas de problème réseau
            //             ou de réponse invalide du serveur.
            console.error('Erreur lors du chargement des données du graphique:', error);
            chartTitleElement.textContent = 'Impossible de charger le graphique. Veuillez réessayer.';
            if (camembertChart) {
                camembertChart.destroy();
                camembertChart = null;
            }
            camembertChart.style.display = 'none'; // Masque le canvas en cas d'erreur grave
        }
    }

     // NOUVEAU : Fonction pour afficher le graphique suivant
    function showNextChart() {
        currentChartIndex = (currentChartIndex + 1) % mainChatData.length;
        updateChart(mainChatData[currentChartIndex]);
    }

    // NOUVEAU : Fonction pour afficher le graphique précédent
    function showPrevChart() {
        currentChartIndex = (currentChartIndex - 1 + mainChatData.length) % mainChatData.length;
        updateChart(mainChatData[currentChartIndex]);
    }

    function createPaginationDots() {
        chartDotsContainer.innerHTML = ''; // Nettoie les points existants
        if (mainChatData.length > 1) { // Affiche les points seulement s'il y a plus d'un graphique
            chartDotsContainer.style.display = 'block'; // Ou 'flex' si vous voulez une flexbox
            mainChatData.forEach((key, index) => {
                const dot = document.createElement('span');
                dot.classList.add('chart-dot');
                dot.dataset.index = index; // Stocke l'index du graphique que ce point représente
                dot.addEventListener('click', () => {
                    currentChartIndex = index; // Met à jour l'index actuel
                    updateChart(mainChatData[currentChartIndex]); // Charge le graphique correspondant
                });
                chartDotsContainer.appendChild(dot);
            });
        } else {
            chartDotsContainer.style.display = 'none'; // Cache le conteneur si un seul graphique
        }
        updatePaginationDots(); // Met à jour l'état actif initial
    }

    function updatePaginationDots() {
        const dots = document.querySelectorAll('.chart-dot');
        dots.forEach((dot, index) => {
            if (index === currentChartIndex) {
                dot.classList.add('active');
            } else {
                dot.classList.remove('active');
            }
        });
    }


    // Sélectionne tous les boutons de la barre latérale droite qui permettent de changer le type de graphique
    const chartButtons = document.querySelectorAll('.button_right1');

    /**
     * @function setActiveButton
     * @description Gère l'état visuel "actif" des boutons de sélection du graphique :
     *              Retire la classe 'button_active' de tous les boutons, puis l'ajoute
     *              uniquement au bouton qui a été cliqué (ou qui est défini comme actif).
     * @param {HTMLElement} clickedButton - Le bouton à marquer comme actif.
     */
    function setActiveButton(clickedButton) {
        // Retire la classe 'button_active' de tous les boutons
        chartButtons.forEach(button => button.classList.remove('button_active'));
        // Si un bouton est fourni, lui ajoute la classe 'button_active'
        if (clickedButton) {
            clickedButton.classList.add('button_active');
        }
    }

    // ******  INITIALISATION DU CAMEMBERT PRINCIPAL ET ACTIVATION DU BOUTON PAR DEFAUT ******
    const initial_info = window.initial_info || 'default';

    if (canvasElement) {
        // Affiche le graphique principal avec les données initiales
        loadChartData(initial_info, false);
    }

    window.addEventListener('popstate', (event) => {
        const urlParams = new URLSearchParams(window.location.search);
        const infoFromUrl = urlParams.get('info') || 'default';

        loadChartData(infoFromUrl, false);
    });

    // Ajoute un écouteur d'événement "click" à chaque bouton de sélection du graphique
    chartButtons.forEach(button => {
        button.addEventListener('click', function(event) {
            event.preventDefault();
            // Récupère la clé du jeu de données depuis l'attribut 'data-chartkey' du bouton cliqué
            const info = event.target.getAttribute("data-chartkey");
            // Charge les données du graphique correspondant à l'identifiant, et met à jour l'historique.
            loadChartData(info);
            initialise_chart_data(info);
        });
    });

    if (prevChartBtn && nextChartBtn) {
        prevChartBtn.addEventListener('click', showPrevChart);
        nextChartBtn.addEventListener('click', showNextChart);
    } else {
        console.warn("Boutons de carousel (précédent/suivant) non trouvés.");
    }

    // ********* MINI-CAMEMBERTS PAR DEPARTEMENT ***********
    async function initialise_chart_data(info) {
        const response = await fetch(`/get_chart_data?info=${infoParam}`);

        if (!response.ok) {
            throw new Error(`Erreur HTTP! statut: ${response.status}`);
        }
        
        minichartData = await response.json();
    }

    // Objet pour stocker les données des graphiques pour chaque département.
    const departementalChartData = {};
    const departementAltNames = Array.from(departementAreas).map(area => area.alt.toLowerCase());
    const chartKeysForDepartments = Object.keys(chartDataSets); // Clés comme 'default', 'especesParRegne', etc.

    // Boucle sur chaque nom de département pour initialiser ses données de graphique
    departementAltNames.forEach(deptAltName => {
        departementalChartData[deptAltName] = {}; // Crée un objet pour ce département
        const deptDisplayName = deptAltName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());

        // Pour chaque type de graphique défini dans chartDataSets...
        chartKeysForDepartments.forEach(chartKey => {
            // Récupère les labels et les couleurs du jeu de données correspondant dans le graphique principal
            const mainChartDatasetInfo = chartDataSets[chartKey];

            if (mainChartDatasetInfo) {
                const labelsFromMainChart = mainChartDatasetInfo.labels;
                const backgroundColorsFromMainChart = mainChartDatasetInfo.backgroundColor;

                // Génère des valeurs de données aléatoires spécifiques au département,
                // mais en utilisant les labels et couleurs du graphique principal
                const randomDataValues = generateRandomDataForExistingLabels(labelsFromMainChart);

                departementalChartData[deptAltName][chartKey] = {
                    labels: labelsFromMainChart, // Utilise les labels du graphique principal
                    data: randomDataValues,       // Nouvelles données aléatoires pour ce département
                    backgroundColor: backgroundColorsFromMainChart, // Utilise les couleurs du graphique principal
                    titleSuffix: `pour ${deptDisplayName}` // Suffixe pour le titre du mini-graphique
                };
            } else {
                console.warn(`Dataset principal non trouvé pour chartKey: ${chartKey} lors de la génération des données départementales pour ${deptAltName}.`);
                departementalChartData[deptAltName][chartKey] = {
                    labels: ['Erreur'], data: [1], backgroundColor: ['#CCCCCC'], titleSuffix: `pour ${deptDisplayName}`
                };
            }
        });
    });

    // Ajoute un écouteur d'événement 'click' à chaque zone cliquable de département
    departementAreas.forEach(area => {
        area.addEventListener('click', function(event) {
            event.preventDefault(); // Empêche le comportement par défaut du lien <area>
            // Récupère le nom du département cliqué (depuis l'attribut 'alt')
            const departementKey = this.alt.toLowerCase();
            chartKeyValue = document.querySelector('.button_active')?.dataset.chartkey;

            if (!departementChartContainer || !miniDepartementChartCanvas) {
                console.error("Conteneur (#departement-chart-container) ou canvas (#mini-departement-chart) pour le mini-graphique non trouvé.");
                return;
            }

            // Récupère les données pour le département cliqué ET pour le type de graphique actuellement actif
            const deptDataSetsForCurrentType = departementalChartData[departementKey];
            const specificDeptData = deptDataSetsForCurrentType ? deptDataSetsForCurrentType[chartKeyValue] : null;

            // Récupère les informations (notamment le titre/label) du graphique principal actuellement affiché
            const mainChartInfo = chartDataSets[chartKeyValue];
            const mainChartLegendLabelBase = mainChartInfo ? (mainChartInfo.legendLabel || "Données") : "Données";

            // Si des données spécifiques existent pour ce département et ce type de graphique :
            if (specificDeptData) {
                // Si une instance de mini-graphique existe déjà, la détruit pour en créer une nouvelle
                if (miniChartInstance) {
                    miniChartInstance.destroy();
                }

                // Construit le titre pour le mini-graphique en combinant le titre du graphique principal
                const miniChartTitle = `${mainChartLegendLabelBase} ${specificDeptData.titleSuffix || ''}`;

                // Récupère le contexte de dessin 2D du canvas du mini-graphique
                const miniCtx = miniDepartementChartCanvas.getContext('2d');
                // Crée une nouvelle instance de Chart pour le mini-graphique
                miniChartInstance = new Chart(miniCtx, {
                    type: 'pie',
                    data: {
                        labels: specificDeptData.labels,
                        datasets: [{
                            label: mainChartLegendLabelBase,
                            data: specificDeptData.data,
                            backgroundColor: specificDeptData.backgroundColor,
                            borderColor: '#FFFFFF',
                            borderWidth: 1
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: true,
                        plugins: {
                            legend: {
                                display: specificDeptData.labels.length > 1 && specificDeptData.labels.length < 8,
                                position: 'bottom',
                                labels: {
                                    font: {
                                        size: 10,
                                        family: 'Georgia' },
                                    boxWidth: 12,
                                    padding: 8,
                                    color: '#FFFFFF' }
                            },
                            title: {
                                display: true,
                                text: miniChartTitle,
                                font: {
                                    size: 12,
                                    family: 'Georgia',
                                    weight: 'bold' },
                                color: '#0a7353',
                                padding: { top: 8, bottom: 8 }
                            },
                        }
                    }
                });

                // Calcule la position du popup du mini-graphique pour qu'il apparaisse près du clic
                // tout en essayant de rester visible dans la fenêtre.
                const popupWidth = departementChartContainer.offsetWidth; // Largeur du popup
                const popupHeight = departementChartContainer.offsetHeight; // Hauteur estimée du popup

                let x = event.pageX + 15; // Position X initiale (à droite du clic).
                let y = event.pageY + 15; // Position Y initiale (en dessous du clic).

                // Ajuste la position si le popup sort de la fenêtre :
                if (x + popupWidth > window.innerWidth) x = window.innerWidth - popupWidth - 10;
                if (y + popupHeight > window.innerHeight) y = window.innerHeight - popupHeight - 10;
                if (x < 0) x = 10; // Empêche de sortir à gauche
                if (y < 0) y = 10; // Empêche de sortir en haut

                // Applique la position calculée au conteneur du mini-graphique et le rend visible
                departementChartContainer.style.left = `${x}px`;
                departementChartContainer.style.top = `${y}px`;
                departementChartContainer.style.display = 'block';

            } else {
                console.warn(`Pas de données de graphique disponibles pour le département "${departementKey}" et le type de graphique "${chartKeyValue}".`);
                departementChartContainer.style.display = 'none';
            }
        });
    });

    // Ajoute un écouteur d'événement 'click' sur l'ensemble du document
    // Utilisé pour fermer le mini-graphique si l'utilisateur clique n'importe où en dehors de celui-ci
    document.addEventListener('click', function(event) {

        if (departementChartContainer && departementChartContainer.style.display === 'block' &&
            !event.target.closest('area.departement-area') &&
            !event.target.closest('#departement-chart-container')) {

            departementChartContainer.style.display = 'none';
            if (miniChartInstance) {
                miniChartInstance.destroy();
                miniChartInstance = null;
            }
        }
    });

}); // FIN DE DOMContentLoaded

// Attend que toutes les ressources de la page (y compris les images) soient chargées
window.addEventListener('load', function () {
    // Vérifie si la fonction 'imageMapResize' (de la bibliothèque image-map-resizer) est disponible
    if (typeof imageMapResize === 'function') {
        // Initialise la bibliothèque pour rendre les zones cliquables (<map>) de l'image responsives
        imageMapResize(undefined);
    } else {
        console.warn("La fonction imageMapResize n'a pas été trouvée.");
    }
});