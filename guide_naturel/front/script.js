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
