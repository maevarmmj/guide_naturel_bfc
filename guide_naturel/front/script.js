document.addEventListener('DOMContentLoaded', function() {
    const departementAreas = document.querySelectorAll('area.departement-area');
    const overlayImage = document.querySelector('.overlay-image');
    const overlayText = document.querySelector('.overlay-text');
    const infoBox = document.getElementById('info-box');

    // Survol des images
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

    // Description des dep
    fetch('ressources/departements.txt')
        .then(response => response.text())
        .then(data => {
            // Convertions données -> clé-valeur
            const departementInfos = parseDepartementInfos(data);

            departementAreas.forEach(area => {
                area.addEventListener('click', function(event) {
                    // Empêche le comportement par défaut de l'élément <area>
                    event.preventDefault();

                    const departementKey = this.alt.toLowerCase();
                    const x = event.pageX;
                    const y = event.pageY;

                    // Maj contenu avec le bon département
                    infoBox.innerHTML = `<strong>${departementKey.replace(/_/g, ' ').toUpperCase()}</strong><br>${departementInfos[departementKey] || "Pas d'information disponible"}`;

                    // Position du cadre
                    infoBox.style.left = `${x + 15}px`;
                    infoBox.style.top = `${y}px`;
                    infoBox.style.display = 'block';
                });
            });

            // Cache cadre qd on clique ailleurs
            document.addEventListener('click', function(event) {
                if (!event.target.closest('area.departement-area')) {
                    infoBox.style.display = 'none';
                }
            });

        })
        .catch(error => console.error('Erreur lors du chargement du fichier :', error));

    // Fonction de conversion clé -> valeur
    function parseDepartementInfos(data) {
        const infos = {};
        const lines = data.split('\n');

        lines.forEach(line => {
            const [key, value] = line.split('=');
            if (key && value) {
                infos[key.trim()] = value.trim();
            }
        });

        return infos;
    }
});

function resizeMapAreas() {
    const image = document.querySelector('.BFCcarte');
    const areas = document.querySelectorAll('area.departement-area');

    if (!image.complete) {
        image.addEventListener('load', resizeMapAreas);
        return;
    }

    const originalWidth = image.naturalWidth;
    const currentWidth = image.offsetWidth;
    const scale = currentWidth / originalWidth;

    areas.forEach(area => {
        const originalCoords = area.dataset.originalCoords;
        if (!originalCoords) return;

        const scaledCoords = originalCoords
            .split(',')
            .map(coord => Math.round(Number(coord) * scale))
            .join(',');

        area.coords = scaledCoords;
    });
}

// Initial call on load
window.addEventListener('load', resizeMapAreas);
// Recalculate on resize
window.addEventListener('resize', resizeMapAreas);

window.addEventListener('load', function () {
    if (typeof imageMapResize === 'function') {
        imageMapResize();
    }
});



document.addEventListener('DOMContentLoaded', function() {
    // ==========================================================================
    // ============== PARTIE EXISTANTE : CARTE, OVERLAYS, INFOBOX ===============
    // ==========================================================================
    const departementAreas = document.querySelectorAll('area.departement-area');
    const overlayImage = document.querySelector('.overlay-image');
    const overlayText = document.querySelector('.overlay-text');
    const infoBox = document.getElementById('info-box');

    // Survol des images
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
                // Optionnel: réinitialiser src pour éviter de garder l'image chargée en mémoire
                // overlayImage.src = "";
                // overlayText.src = "";
            });
        });
    } else {
        console.error("Erreur : Élément .overlay-image ou .overlay-text non trouvé.");
    }

    // Description des dep
    fetch('ressources/departements.txt')
        .then(response => response.text())
        .then(data => {
            const departementInfos = parseDepartementInfos(data);

            departementAreas.forEach(area => {
                area.addEventListener('click', function(event) {
                    event.preventDefault();
                    const departementKey = this.alt.toLowerCase();
                    const x = event.pageX;
                    const y = event.pageY;
                    infoBox.innerHTML = `<strong>${departementKey.replace(/_/g, ' ').toUpperCase()}</strong><br>${departementInfos[departementKey] || "Pas d'information disponible"}`;
                    infoBox.style.left = `${x + 15}px`;
                    infoBox.style.top = `${y}px`;
                    infoBox.style.display = 'block';
                });
            });

            // Cache cadre qd on clique ailleurs que sur une area ou l'infobox elle-même
            document.addEventListener('click', function(event) {
                if (!event.target.closest('area.departement-area') && !event.target.closest('#info-box')) {
                    if (infoBox) infoBox.style.display = 'none';
                }
            });
        })
        .catch(error => console.error('Erreur lors du chargement du fichier departements.txt:', error));

    // Fonction de conversion clé -> valeur pour departements.txt
    function parseDepartementInfos(data) {
        const infos = {};
        const lines = data.split('\n');
        lines.forEach(line => {
            const [key, value] = line.split('=');
            if (key && value) {
                infos[key.trim()] = value.trim();
            }
        });
        return infos;
    }

    // ==========================================================================
    // ======================= PARTIE AJOUTÉE : CHART.JS ========================
    // ==========================================================================

    const ctx = document.getElementById('camembert').getContext('2d');
    let camembertChart; // Déclarer ici pour qu'elle soit accessible dans les fonctions

    // Données initiales et pour chaque type de graphique
    // REMPLISSEZ CECI AVEC VOS VRAIES DONNÉES !
    const chartDataSets = {
        default: {
            labels: ['Forêt', 'Zones humides', 'Prairies'],
            data: [40, 30, 30], // Exemple de données
            backgroundColor: ['#48d962', '#73dea5', '#21cca4'],
            title: 'Répartition des zones naturelles (Défaut)'
        },
        especesParRegne: {
            labels: ['Animalia', 'Plantae', 'Fungi', 'Bacteria', 'Chromista'],
            data: [1200, 850, 300, 500, 150],
            backgroundColor: ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF'],
            title: "Nombre d'espèces par règne"
        },
        especesDansChaqueRegne: {
            labels: ['Mammifères (Animalia)', 'Oiseaux (Animalia)', 'Angiospermes (Plantae)', 'Champignons (Fungi)'],
            data: [150, 350, 700, 300],
            backgroundColor: ['#FF9F40', '#FFCD56', '#4BC0C0', '#36A2EB'],
            title: "Nombre d'espèces spécifiques"
        },
        statutsConservation: {
            labels: ['Préoccupation mineure', 'Quasi menacée', 'Vulnérable', 'En danger', 'En danger critique'],
            data: [500, 120, 80, 40, 15],
            backgroundColor: ['#A1E8A1', '#F9E79F', '#F5CBA7', '#F1948A', '#EC7063'],
            title: "Statuts de conservation"
        },
        groupesTaxoParRegne: {
            labels: ['Classes (Animalia)', 'Ordres (Plantae)', 'Familles (Fungi)'],
            data: [30, 50, 120],
            backgroundColor: ['#85C1E9', '#7DCEA0', '#F8C471'],
            title: "Nombre de groupes taxonomiques par règne"
        },
        especesParStatutConservation: {
            labels: ['LC', 'NT', 'VU', 'EN', 'CR', 'DD'],
            data: [60, 25, 15, 10, 5, 20],
            backgroundColor: ['#76D7C4', '#F7DC6F', '#F0B27A', '#E74C3C', '#C0392B', '#BFC9CA'],
            title: "Nombre d'espèces par statut de conservation"
        }
    };

    function updateChart(dataSetKey) {
        const newDataSet = chartDataSets[dataSetKey];
        if (!newDataSet) {
            console.error("Jeu de données non trouvé pour :", dataSetKey);
            return;
        }

        if (camembertChart) {
            camembertChart.data.labels = newDataSet.labels;
            camembertChart.data.datasets[0].data = newDataSet.data;
            camembertChart.data.datasets[0].backgroundColor = newDataSet.backgroundColor;
            camembertChart.data.datasets[0].label = newDataSet.title;
            if (camembertChart.options.plugins.title) { // Vérifier si le plugin title est configuré
                 camembertChart.options.plugins.title.text = newDataSet.title;
            }
            camembertChart.update();
        } else {
            camembertChart = new Chart(ctx, {
                type: 'pie',
                data: {
                    labels: newDataSet.labels,
                    datasets: [{
                        label: newDataSet.title,
                        data: newDataSet.data,
                        backgroundColor: newDataSet.backgroundColor,
                        borderColor: '#fff',
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true, // Garder true pour que le camembert reste rond, Chart.js gère l'espace avec la légende
                    // aspectRatio: 1, // Généralement pas nécessaire si maintainAspectRatio est true pour 'pie'
                    layout: {
                        padding: { // Ajustez ces valeurs pour contrôler l'espacement global
                            top: 10,
                            right: 10, // L'espace pour la légende à droite sera géré par Chart.js
                            bottom: 10,
                            left: 10
                        }
                    },
                    plugins: {
                        legend: {
                            position: 'right', // 'top', 'bottom', 'left', 'right'
                            align: 'center', // 'start', 'center', 'end' pour la position verticale/horizontale
                            labels: {
                                color: '#ffffff',
                                font: {
                                    family: 'Georgia',
                                    size: 10
                                },
                                boxWidth: 15, // Taille des carrés de couleur
                                padding: 10 // Espace entre les items de la légende
                            }
                        },
                        title: {
                            display: true,
                            text: newDataSet.title,
                            color: '#ffffff',
                            font: {
                                size: 14, // Taille du titre un peu réduite
                                family: 'Georgia'
                            },
                            padding: {
                                top: 0,
                                bottom: 10 // Espace sous le titre
                            }
                        },
                        tooltip: {
                             callbacks: {
                                label: function(context) {
                                    let label = context.label || '';
                                    if (label) {
                                        label += ': ';
                                    }
                                    if (context.parsed !== null) {
                                        label += context.raw;
                                    }
                                    return label;
                                }
                            }
                        }
                    }
                }
            });
        }
    }

    // Initialiser le graphique avec les données par défaut
    updateChart('default');

    const chartButtons = document.querySelectorAll('.button_right1');
    chartButtons.forEach(button => {
        // Utiliser un data-attribute sur les boutons HTML est plus robuste
        // Exemple: <a href="#" class="button_base button_right1" data-chartkey="especesParRegne">...</a>
        const chartKey = button.dataset.chartkey; // Lire depuis data-chartkey

        if (chartKey) { // Si l'attribut data-chartkey existe
            button.addEventListener('click', function(event) {
                event.preventDefault();
                updateChart(chartKey);
            });
        } else {
            // Fallback si data-chartkey n'est pas utilisé (moins recommandé)
             button.addEventListener('click', function(event) {
                event.preventDefault();
                const buttonText = this.textContent.trim();
                let dataSetKeyToUse = 'default';

                if (buttonText.includes("espèces par règne")) dataSetKeyToUse = 'especesParRegne';
                else if (buttonText.includes("espèces dans chaque règne")) dataSetKeyToUse = 'especesDansChaqueRegne';
                else if (buttonText.includes("Statuts de conservation")) dataSetKeyToUse = 'statutsConservation'; // Simplifié
                else if (buttonText.includes("groupes taxonomiques par règne")) dataSetKeyToUse = 'groupesTaxoParRegne';
                else if (buttonText.includes("espèces par statut de conservation")) dataSetKeyToUse = 'especesParStatutConservation';

                updateChart(dataSetKeyToUse);
            });
        }
    });

}); // FIN DE DOMContentLoaded
