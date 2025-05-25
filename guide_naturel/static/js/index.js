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
    // Sélectionne le <div> qui contiendra le mini-graphique affiché au clic sur un département
    const departementChartContainer = document.getElementById('departement-chart-container');
    // Sélectionne l'élément <canvas> à l'intérieur du conteneur ci-dessus pour le mini-graphique
    const miniDepartementChartCanvas = document.getElementById('mini-departement-chart');

    // Instances des graphiques Chart.js :
    let camembertChart;
    let miniChartInstance;
    // Variable pour suivre quel type de données le graphique principal (et donc le mini-graphique) doit afficher
    // Initialisée à 'default', qui correspond à une clé dans chartDataSets
    let currentActiveChartKey = 'default';


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
        especesDansChaqueRegne: {
            labels: ['Mammifères', 'Oiseaux', 'Angiospermes', 'Champignons Ascomycètes'],
            data: [150, 350, 700, 250],
            backgroundColor: ['#FF9F40', '#FFCD56', '#4BC0C0', '#36A2EB', '#C9CBCF'], legendLabel: "Exemples d'espèces par groupes" },
        statutsConservation: {
            labels: ['Préoccupation mineure (LC)', 'Quasi menacée (NT)', 'Vulnérable (VU)', 'En danger (EN)', 'En danger critique (CR)'],
            data: [500, 120, 80, 40, 15],
            backgroundColor: ['#A1E8A1', '#F9E79F', '#F5CBA7', '#F1948A', '#EC7063'],
            legendLabel: "Statuts de conservation (Tous règnes)" },
        groupesTaxoParRegne: {
            labels: ['Classes (Animalia)', 'Divisions (Plantae)', 'Phyla (Fungi)'],
            data: [30, 15, 25],
            backgroundColor: ['#85C1E9', '#7DCEA0', '#F8C471'],
            legendLabel: "Diversité des groupes taxonomiques" },
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
     * @param {string} dataSetKey - La clé du jeu de données à utiliser (doit correspondre à une clé dans chartDataSets)
     */

    function updateChart(dataSetKey) {
        // Ne fait rien si l'élément canvas n'a pas été trouvé
        if (!canvasElement) return;

        const newDataSet = chartDataSets[dataSetKey];
        if (!newDataSet) {
            console.error("Jeu de données pour le graphique principal non trouvé :", dataSetKey);
            return;
        }
        // Met à jour la variable globale qui stocke la clé du graphique actuellement affiché
        // Cette variable est utilisée par les mini-graphiques pour savoir quel type de données afficher
        currentActiveChartKey = dataSetKey;

        // Récupère le contexte de dessin 2D du canvas
        const ctx = canvasElement.getContext('2d');

        if (camembertChart) {
            camembertChart.data.labels = newDataSet.labels;
            camembertChart.data.datasets[0].data = newDataSet.data;
            camembertChart.data.datasets[0].backgroundColor = newDataSet.backgroundColor;
            camembertChart.data.datasets[0].label = newDataSet.legendLabel;

            camembertChart.update();
        } else {
            // Si le graphique n'existe pas encore, le crée :
            camembertChart = new Chart(ctx, {
                type: 'pie',
                data: {
                    labels: newDataSet.labels,
                    datasets: [{
                        label: newDataSet.legendLabel,
                        data: newDataSet.data,
                        backgroundColor: newDataSet.backgroundColor,
                        borderColor: '#fff',
                        borderWidth: 1
                    }]
                },
                options: chartOptionsConfig
            });
        }
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

    if (canvasElement) {
        // Vérifie si la clé 'default' (stockée dans currentActiveChartKey) n'existe pas dans chartDataSets
        // Si c'est le cas et qu'il y a au moins un jeu de données disponible,
        // utilise la première clé de chartDataSets comme clé par défaut
        if (!chartDataSets[currentActiveChartKey] && Object.keys(chartDataSets).length > 0) {
            currentActiveChartKey = Object.keys(chartDataSets)[0];
            console.warn(`Clé 'default' non trouvée pour chartDataSets. Initialisation avec '${currentActiveChartKey}'.`);
        }

        // Vérifie si un jeu de données existe pour la clé active (initialement 'default' ou le fallback)
        if (chartDataSets[currentActiveChartKey]) {
            // Affiche le graphique principal avec les données initiales
            updateChart(currentActiveChartKey);

            // Trouve le bouton qui correspond à la clé du graphique initial
            // On cherche d'abord un bouton ayant un attribut 'data-chartkey' égal à 'currentActiveChartKey'
            let initialActiveButton = Array.from(chartButtons).find(btn => btn.dataset.chartkey === currentActiveChartKey);

            if (!initialActiveButton && chartButtons.length > 0) {
                // Prend le premier bouton de la liste comme bouton actif par défaut !
                initialActiveButton = chartButtons[0];
                // Vérifie si ce premier bouton a un 'data-chartkey' valide et met à jour le graphique si nécessaire
                if (initialActiveButton.dataset.chartkey && chartDataSets[initialActiveButton.dataset.chartkey]) {
                    currentActiveChartKey = initialActiveButton.dataset.chartkey;
                    updateChart(currentActiveChartKey);
                } else {
                    console.warn("Le premier bouton n'a pas de data-chartkey valide. Le graphique pourrait ne pas correspondre au premier bouton.")
                }
            }

            // Si un bouton initial actif a été déterminé :
            if (initialActiveButton) {
                setActiveButton(initialActiveButton); // Le marque comme actif visuellement
            } else if (chartButtons.length > 0) {
                setActiveButton(chartButtons[0]); // Active le premier bouton
                currentActiveChartKey = chartButtons[0].dataset.chartkey || 'default';
                updateChart(currentActiveChartKey);
            } else {
                console.warn("Aucun bouton '.button_right1' trouvé pour l'activation initiale.");
            }
        } else {
            console.error("Aucune donnée disponible dans chartDataSets pour initialiser le graphique principal.");
        }
    }

    // Ajoute un écouteur d'événement "click" à chaque bouton de sélection du graphique
    chartButtons.forEach(button => {
        button.addEventListener('click', function(event) {
            event.preventDefault();
            // Récupère la clé du jeu de données depuis l'attribut 'data-chartkey' du bouton cliqué
            const chartKey = this.dataset.chartkey;
            // Si la clé existe et qu'un jeu de données correspondant est trouvé :
            if (chartKey && chartDataSets[chartKey]) {
                updateChart(chartKey);    // Met à jour le graphique principal
                setActiveButton(this); // Marque le bouton cliqué comme actif
            } else {
                // Avertit si la clé n'est pas valide ou si les données sont manquantes
                console.warn(`Clé de graphique "${chartKey}" non valide ou jeu de données manquant pour le bouton : "${this.textContent.trim()}".`);
            }
        });
    });

    // ********* MINI-CAMEMBERTS PAR DEPARTEMENT ***********
     /**
     * @function generateRandomDataForExistingLabels
     * @description Génère un ensemble de valeurs de données aléatoires pour une liste de labels existants
     * @param {string[]} mainChartLabels - Le tableau des labels du graphique principal
     * @returns {number[]} Un tableau de valeurs numériques aléatoires
     */
    function generateRandomDataForExistingLabels(mainChartLabels) {
        const data = [];
        mainChartLabels.forEach(() => {
            data.push(Math.floor(Math.random() * 100));
        });
        return data;
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

            if (!departementChartContainer || !miniDepartementChartCanvas) {
                console.error("Conteneur (#departement-chart-container) ou canvas (#mini-departement-chart) pour le mini-graphique non trouvé.");
                return;
            }

            // Récupère les données pour le département cliqué ET pour le type de graphique actuellement actif
            const deptDataSetsForCurrentType = departementalChartData[departementKey];
            const specificDeptData = deptDataSetsForCurrentType ? deptDataSetsForCurrentType[currentActiveChartKey] : null;

            // Récupère les informations (notamment le titre/label) du graphique principal actuellement affiché
            const mainChartInfo = chartDataSets[currentActiveChartKey];
            const mainChartLegendLabelBase = mainChartInfo ? (mainChartInfo.legendLabel || "Données") : "Données";

            // Si des données spécifiques existent pour ce département et ce type de graphique :
            if (specificDeptData) {
                // Si une instance de mini-graphique existe déjà, la détruit pour en créer une nouvelle
                if (miniChartInstance) {
                    miniChartInstance.destroy();
                }

                // Construit le titre pour le mini-graphique en combinant le titre du graphique principal
                const miniChartTitle = `${mainChartLegendLabelBase.replace(/\s*\(Tous règnes\)\s*$/i, '').replace(/\s*par règne\s*$/i, '')} ${specificDeptData.titleSuffix || ''}`;

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
                console.warn(`Pas de données de graphique disponibles pour le département "${departementKey}" et le type de graphique "${currentActiveChartKey}".`);
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
        imageMapResize();
    } else {
        console.warn("La fonction imageMapResize n'a pas été trouvée.");
    }
});