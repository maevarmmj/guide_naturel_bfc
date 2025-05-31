# 🌳 Site Web - Le Guide Naturel BFC 🌳


### Créé en :
![HTML5](https://img.shields.io/badge/html5-%23E34F26.svg?style=for-the-badge&logo=html5&logoColor=white)
![CSS3](https://img.shields.io/badge/css3-%231572B6.svg?style=for-the-badge&logo=css3&logoColor=white)
![JavaScript](https://img.shields.io/badge/javascript-%23323330.svg?style=for-the-badge&logo=javascript&logoColor=%23F7DF1E)
![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)

### Avec :
![Flask](https://img.shields.io/badge/Flask-000?style=for-the-badge&logo=flask&logoColor=fff)
![MongoDB](https://img.shields.io/badge/MongoDB-%234ea94b.svg?style=for-the-badge&logo=mongodb&logoColor=white)

### Top contributeurs :
<a href="https://github.com/maevarmmj/guide_naturel_bfc/graphs/contributors">
    <img src="https://contrib.rocks/image?repo=maevarmmj/guide_naturel_bfc" alt="contrib.rocks image" />
</a>



## 🌿 Notre Objectif

Le Guide Naturel BFC est un site web interactif conçu dans le cadre d'un projet étudiant en Big Data. Son objectif est d'aider les utilisateurs (jeunes enfants/adolescents) à explorer et découvrir la faune et la flore de la région Bourgogne-Franche-Comté. La page d'accueil emmène les utilisateurs sur les statistiques de la région via une carte interactive, notamment en lien avec les statuts de conservation des espèces. L'application propose un chatbot intelligent, Anna, qui guide les utilisateurs à travers une série de questions pour affiner leur recherche d'espèces, ainsi qu'une interface pour visualiser les résultats de manière conviviale et informative. 


## 🌿 Fonctionnalités Principales

*   **Carte interactive :** statistiques de la région BFC, et des départements en détail grâce à de merveilleux graphiques.
*   **Chatbot Intelligent :** Un assistant conversationnel qui pose des questions ciblées pour aider à trouver des informations sur des espèces spécifiques en fonction de critères tels que le règne, le groupe taxonomique, le département, la commune, et le statut de conservation.
*   **Recherche d'Espèces :** Affichage des espèces correspondant aux critères de recherche, avec des informations détaillées, de manière ergonomique et intuitive (pagination, barre de recherche).
*   **Infobox Détaillée :** En cliquant sur une espèce dans les résultats, une infobulle apparaît avec des informations supplémentaires (nom scientifique, règne, observations, départements, etc.).
*   **Recherche Locale dans les Résultats :** Possibilité de filtrer les espèces affichées sur la page actuelle par leur nom scientifique.
*   **Gestion des "Je ne sais pas" :** Le chatbot gère les cas où l'utilisateur ne connaît pas la réponse à une question, avec un mécanisme pour relancer la conversation si l'utilisateur est bloqué.
*   **Interface Responsive :** Adaptation de l'affichage pour une expérience utilisateur optimale sur ordinateurs et appareils mobiles.

## 🌿 Technologies Utilisées

### Backend
*   **Python :** Langage principal pour la logique serveur
*   **Flask :** Micro-framework web pour servir l'application et créer l'API du chatbot
    *   Gestion des routes (`/page_principale`, `/recherche`, `/chat/results/`)
    *   Traitement des requêtes JSON
*   **MongoDB :** Base de données NoSQL utilisée pour stocker :
    *   Les données principales sur la faune et la flore de la BFC (collection "Nature")
    *   Les logs pour la Business Intelligence :
        *   `completed_searches` : Enregistre les filtres finaux des recherches utilisateurs
        *   `question_interactions` : Enregistre les réponses et les "skips" aux questions du chatbot
*   **Pymongo :** Driver Python officiel pour interagir avec MongoDB
*   **TheFuzz (FuzzyWuzzy) :** Bibliothèque pour la correspondance approximative de chaînes (fuzzy string matching) afin de corriger les entrées utilisateur en cas d'erreurs

### Frontend
*   **HTML5 :** Structure des pages web
*   **CSS3 :** Style et mise en page des éléments, incluant des techniques de design responsive (Flexbox, Media Queries)
*   **JavaScript :**
    *   Gestion des graphiques de la page d'acceuil
    *   Logique d'interaction de l'interface utilisateur du chatbot
    *   Appels "fetch" asynchrones à l'API backend
    *   Manipulation dynamique du DOM pour afficher les messages, les résultats, la pagination, et les infobox
    *   Gestion des événements utilisateur

### Business Intelligence (sur MongoDB Charts)
*   Analyse des statistiques de recherche pour adapter les futures améliorations (focus sur une catégorie, reformulation de questions, etc.)

## 🌿 Sécurité et gouvernance des données

### Sécurité des données

* **Accès limité à la base de données :** Rôles définis pour les requêtes, requêtes possibles seulement depuis des adresses IP précises.
* **Mots de passes stocker dans un .env**

### Gouvernance des données

* **Données fiables :** Récupérer sur le site de l'Inventaire National du Patrimoine Naturel (INPN)
* **Licence ouverte (Etalab)**
* **Nettoyage et validation préalable des données :** Mise en places de test unitaires, vérification de la concordance netre les résultats et le type de données renvoyé pour les requêtes.
