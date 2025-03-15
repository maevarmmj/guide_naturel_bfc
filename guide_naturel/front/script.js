document.addEventListener('DOMContentLoaded', function() {
    const departementAreas = document.querySelectorAll('area.departement-area');
    const overlayImage = document.querySelector('.overlay-image');
    const overlayText = document.querySelector('.overlay-text');

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
});
