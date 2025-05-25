document.addEventListener('DOMContentLoaded', function() {
    // ==========================================================================
    // ======================= SELECTEURS DOM COMMUNS ===========================
    // ==========================================================================
    const departementAreas = document.querySelectorAll('area.departement-area');
    const overlayImage = document.querySelector('.overlay-image');
    const overlayText = document.querySelector('.overlay-text');

    const canvasElement = document.getElementById('camembert');
    const departementChartContainer = document.getElementById('departement-chart-container');
    const miniDepartementChartCanvas = document.getElementById('mini-departement-chart');

    let camembertChart;
    let miniChartInstance;
    let currentActiveChartKey = 'default'; // Clé par défaut

    // ==========================================================================
    // ======================= SURVOL DES DEPARTEMENTS (OVERLAYS) ===============
    // ==========================================================================
    if (overlayImage && overlayText) {
        departementAreas.forEach(area => {
            const departementName = area.alt.toLowerCase();
            const overlayImageURL = `ressources/dep/${departementName}.png`;
            const overlayTextURL = `ressources/dep/${departementName}_text.png`;

            area.addEventListener('mouseenter', function() {
                overlayImage.src = overlayImageURL;
                overlayText.src = overlayTextURL;
                overlayImage.style.opacity = 1;
                overlayText.style.opacity = 1;
            });

            area.addEventListener('mouseleave', function() {
                overlayImage.style.opacity = 0;
                overlayText.style.opacity = 0;
            });
        });
    } else {
        console.error("Erreur : Élément .overlay-image ou .overlay-text non trouvé.");
    }

    // ==========================================================================
    // ======================= PARTIE CHART.JS PRINCIPAL (CAMEMBERT) ============
    // ==========================================================================
    if (!canvasElement) {
        console.error("L'élément Canvas avec l'ID 'camembert' n'a pas été trouvé. Le graphique principal ne sera pas initialisé.");
    }

    const chartDataSets = {
        default: { labels: ['Animalia', 'Plantae', 'Fungi', 'Bacteria', 'Chromista'], data: [1200, 850, 300, 500, 150], backgroundColor: ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF'], legendLabel: "Nombre d'espèces par règne" }, // Note: 'title' a été renommé 'legendLabel'
        especesParRegne: { labels: ['Animalia', 'Plantae', 'Fungi', 'Bacteria', 'Chromista'], data: [1200, 850, 300, 500, 150], backgroundColor: ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF'], legendLabel: "Nombre d'espèces par règne" },
        especesDansChaqueRegne: { labels: ['Mammifères', 'Oiseaux', 'Angiospermes', 'Champignons Ascomycètes'], data: [150, 350, 700, 250], backgroundColor: ['#FF9F40', '#FFCD56', '#4BC0C0', '#36A2EB', '#C9CBCF'], legendLabel: "Exemples d'espèces par groupes" },
        statutsConservation: { labels: ['Préoccupation mineure (LC)', 'Quasi menacée (NT)', 'Vulnérable (VU)', 'En danger (EN)', 'En danger critique (CR)'], data: [500, 120, 80, 40, 15], backgroundColor: ['#A1E8A1', '#F9E79F', '#F5CBA7', '#F1948A', '#EC7063'], legendLabel: "Statuts de conservation (Tous règnes)" },
        groupesTaxoParRegne: { labels: ['Classes (Animalia)', 'Divisions (Plantae)', 'Phyla (Fungi)'], data: [30, 15, 25], backgroundColor: ['#85C1E9', '#7DCEA0', '#F8C471'], legendLabel: "Diversité des groupes taxonomiques" },
        especesParStatutConservation: { labels: ['LC', 'NT', 'VU', 'EN', 'CR', 'DD', 'NE'], data: [600, 250, 150, 100, 50, 200, 30], backgroundColor: ['#76D7C4', '#F7DC6F', '#F0B27A', '#E74C3C', '#C0392B', '#BFC9CA', '#AAB7B8'], legendLabel: "Nombre d'espèces par statut UICN" }
    };

    // Options communes pour le graphique principal avec un titre FIXE
    const chartOptionsConfig = {
        responsive: true, maintainAspectRatio: true, layout: { padding: { top: 10, right: 10, bottom: 10, left: 10 } },
        plugins: {
            legend: { position: 'right', align: 'center', labels: { color: '#ffffff', font: { family: 'Georgia', size: 10 }, boxWidth: 15, padding: 10 } },
            title: {
                display: true,
                text: "Statistiques en BFC :", // VOTRE TITRE FIXE ICI
                color: '#ffffff',
                font: { size: 16, family: 'Georgia', weight: 'bold' }, // Taille de police un peu augmentée
                padding: { top: 0, bottom: 15 } // Un peu plus de padding en bas
            },
            tooltip: { callbacks: { label: function(context) { let label = context.label || ''; if (label) label += ': '; if (context.parsed !== null) label += context.raw.toLocaleString(); return label; } } }
        }
    };

    function updateChart(dataSetKey) {
        if (!canvasElement) return;
        const newDataSet = chartDataSets[dataSetKey];
        if (!newDataSet) {
            console.error("Jeu de données pour le graphique principal non trouvé :", dataSetKey);
            return;
        }
        currentActiveChartKey = dataSetKey;

        // Les options du graphique (y compris le titre) sont maintenant fixes et définies dans chartOptionsConfig
        // Nous n'avons plus besoin de cloner et de modifier currentChartOptions.plugins.title.text ici.

        const ctx = canvasElement.getContext('2d');
        if (camembertChart) {
            camembertChart.data.labels = newDataSet.labels;
            camembertChart.data.datasets[0].data = newDataSet.data;
            camembertChart.data.datasets[0].backgroundColor = newDataSet.backgroundColor;
            camembertChart.data.datasets[0].label = newDataSet.legendLabel; // Utilise legendLabel pour le dataset
            // camembertChart.options = chartOptionsConfig; // Pas besoin de réassigner si elles ne changent pas
            camembertChart.update();
        } else {
            camembertChart = new Chart(ctx, {
                type: 'pie',
                data: {
                    labels: newDataSet.labels,
                    datasets: [{
                        label: newDataSet.legendLabel, // Utilise legendLabel pour le dataset
                        data: newDataSet.data,
                        backgroundColor: newDataSet.backgroundColor,
                        borderColor: '#fff',
                        borderWidth: 1
                    }]
                },
                options: chartOptionsConfig // Utilise les options fixes
            });
        }
    }

    const chartButtons = document.querySelectorAll('.button_right1');

    function setActiveButton(clickedButton) {
        chartButtons.forEach(button => button.classList.remove('button_active'));
        if (clickedButton) {
            clickedButton.classList.add('button_active');
        }
    }

    // Initialisation du graphique principal et activation du bouton par défaut
    if (canvasElement) {
        // S'assurer que la clé 'default' existe ou prendre la première
        if (!chartDataSets[currentActiveChartKey] && Object.keys(chartDataSets).length > 0) {
            currentActiveChartKey = Object.keys(chartDataSets)[0]; // Fallback sur la première clé disponible
            console.warn(`Clé 'default' non trouvée pour chartDataSets. Initialisation avec '${currentActiveChartKey}'.`);
        }

        if (chartDataSets[currentActiveChartKey]) {
            updateChart(currentActiveChartKey); // Charge le graphique avec la clé initiale

            // Activer le bouton correspondant à la clé initiale (par data-chartkey ou le premier)
            let initialActiveButton = Array.from(chartButtons).find(btn => btn.dataset.chartkey === currentActiveChartKey);

            if (!initialActiveButton && chartButtons.length > 0) {
                // Si aucun bouton n'a le data-chartkey "default" (ou la clé initiale), on prend le premier bouton de la liste
                initialActiveButton = chartButtons[0];
                // On s'assure que ce premier bouton a un data-chartkey valide et met à jour le graphique en conséquence
                if (initialActiveButton.dataset.chartkey && chartDataSets[initialActiveButton.dataset.chartkey]) {
                    currentActiveChartKey = initialActiveButton.dataset.chartkey;
                    updateChart(currentActiveChartKey);
                } else {
                    console.warn("Le premier bouton n'a pas de data-chartkey valide. Le graphique pourrait ne pas correspondre au premier bouton.")
                }
            }

            if (initialActiveButton) {
                setActiveButton(initialActiveButton);
            } else if (chartButtons.length > 0) {
                // Si toujours pas de bouton actif (très peu probable si on prend le premier), on prend le premier de la liste
                // et on essaie d'afficher le graphique 'default'
                setActiveButton(chartButtons[0]);
                currentActiveChartKey = chartButtons[0].dataset.chartkey || 'default';
                updateChart(currentActiveChartKey);

            } else {
                console.warn("Aucun bouton '.button_right1' trouvé pour l'activation initiale.");
            }

        } else {
            console.error("Aucune donnée disponible dans chartDataSets pour initialiser le graphique principal.");
        }
    }


    chartButtons.forEach(button => {
        button.addEventListener('click', function(event) {
            event.preventDefault();
            const chartKey = this.dataset.chartkey;
            if (chartKey && chartDataSets[chartKey]) {
                updateChart(chartKey);
                setActiveButton(this);
            } else {
                console.warn(`Clé de graphique "${chartKey}" non valide ou jeu de données manquant pour le bouton : "${this.textContent.trim()}".`);
            }
        });
    });

    // ==========================================================================
    // ================= MINI-GRAPHIQUES DÉPARTEMENTAUX (POPUP) =================
    // ==========================================================================

    function getRandomColor() {
        const r = Math.floor(Math.random() * 200 + 55);
        const g = Math.floor(Math.random() * 200 + 55);
        const b = Math.floor(Math.random() * 200 + 55);
        return `rgb(${r},${g},${b})`;
    }

    function generateRandomPieData(numSegments = 3) {
        const labels = [];
        const data = [];
        const backgroundColor = [];
        for (let i = 0; i < numSegments; i++) {
            labels.push(`Segment ${String.fromCharCode(65 + i)}`);
            data.push(Math.floor(Math.random() * 100) + 10);
            backgroundColor.push(getRandomColor());
        }
        return { labels, data, backgroundColor };
    }

    const departementalChartData = {};
    const departementAltNames = Array.from(departementAreas).map(area => area.alt.toLowerCase());
    const chartKeysForDepartments = Object.keys(chartDataSets);

    departementAltNames.forEach(deptAltName => {
        departementalChartData[deptAltName] = {};
        const deptDisplayName = deptAltName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());

        chartKeysForDepartments.forEach(chartKey => {
            let numSegments;
            if (chartKey === 'especesParRegne' || chartKey === 'default' || chartKey === 'especesParStatutConservation') {
                numSegments = Math.floor(Math.random() * 3) + 3;
            } else if (chartKey === 'statutsConservation') {
                numSegments = 5;
            } else {
                numSegments = Math.floor(Math.random() * 2) + 2;
            }

            const randomData = generateRandomPieData(numSegments);
            departementalChartData[deptAltName][chartKey] = {
                labels: randomData.labels,
                data: randomData.data,
                backgroundColor: randomData.backgroundColor,
                titleSuffix: `pour ${deptDisplayName}`
            };
        });
    });
    // console.log("Données départementales générées:", departementalChartData);

    departementAreas.forEach(area => {
        area.addEventListener('click', function(event) {
            event.preventDefault();
            const departementKey = this.alt.toLowerCase();

            if (!departementChartContainer || !miniDepartementChartCanvas) {
                console.error("Conteneur (#departement-chart-container) ou canvas (#mini-departement-chart) pour le mini-graphique non trouvé.");
                return;
            }

            const deptDataSetsForCurrentType = departementalChartData[departementKey];
            const specificDeptData = deptDataSetsForCurrentType ? deptDataSetsForCurrentType[currentActiveChartKey] : null;

            // Récupérer le legendLabel du graphique principal pour l'utiliser dans le mini-graphique
            const mainChartInfo = chartDataSets[currentActiveChartKey];
            const mainChartLegendLabelBase = mainChartInfo ? (mainChartInfo.legendLabel || "Données") : "Données";


            if (specificDeptData) {
                if (miniChartInstance) {
                    miniChartInstance.destroy();
                }

                // Le titre du mini-graphique sera basé sur le legendLabel du graphique principal + le suffixe du département
                const miniChartTitle = `${mainChartLegendLabelBase.replace(/\s*\(Tous règnes\)\s*$/i, '').replace(/\s*par règne\s*$/i, '')} ${specificDeptData.titleSuffix || ''}`;

                const miniCtx = miniDepartementChartCanvas.getContext('2d');
                miniChartInstance = new Chart(miniCtx, {
                    type: 'pie',
                    data: {
                        labels: specificDeptData.labels,
                        datasets: [{
                            label: mainChartLegendLabelBase, // Le label du dataset peut être le legendLabel du graphique principal
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
                                labels: { font: { size: 10, family: 'Georgia' }, boxWidth: 12, padding: 8, color: '#FFFFFF' }
                            },
                            title: { // Le titre affiché DANS le mini-graphique
                                display: true,
                                text: miniChartTitle,
                                font: { size: 12, family: 'Georgia', weight: 'bold' },
                                color: '#0a7353',
                                padding: { top: 8, bottom: 8 }
                            },
                            tooltip: {
                                callbacks: {
                                    label: function(context) {
                                        // Pour le tooltip, on veut le label du segment + sa valeur
                                        let tooltipLabel = context.label || ''; // Nom du segment (ex: 'Segment A')
                                        if (tooltipLabel) {
                                            tooltipLabel += ': ';
                                        }
                                        if (context.parsed !== null) {
                                            tooltipLabel += context.formattedValue; // Valeur du segment
                                        }
                                        return tooltipLabel;
                                    }
                                }
                            }
                        }
                    }
                });

                const popupWidth = departementChartContainer.offsetWidth || 320;
                const popupHeight = departementChartContainer.offsetHeight || 300;

                let x = event.pageX + 15;
                let y = event.pageY + 15;

                if (x + popupWidth > window.innerWidth) x = window.innerWidth - popupWidth - 10;
                if (y + popupHeight > window.innerHeight) y = window.innerHeight - popupHeight - 10;
                if (x < 0) x = 10;
                if (y < 0) y = 10;

                departementChartContainer.style.left = `${x}px`;
                departementChartContainer.style.top = `${y}px`;
                departementChartContainer.style.display = 'block';

            } else {
                console.warn(`Pas de données de graphique disponibles pour le département "${departementKey}" et le type de graphique "${currentActiveChartKey}".`);
                departementChartContainer.style.display = 'none';
            }
        });
    });

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

window.addEventListener('load', function () {
    if (typeof imageMapResize === 'function') {
        imageMapResize();
    } else {
        console.warn("La fonction imageMapResize n'a pas été trouvée.");
    }
});