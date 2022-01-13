# Lapin Blanc

## Ajouter des salariés

La configuration se faire sur l'interface d'administration, accessible à
http://lapin-blanc.telescoop.fr/configuration/.

Pour ajouter un salarié, aller sur la
[liste des utilisateurs](http://lapin-blanc.telescoop.fr/configuration/auth/user/)
puis cliquer sur le bouton en haut à droite "Ajouter un utilisateur".

![](readme-images/add-user.png)

Remplir ensuite les informations demandées. Ça devrait être assez simple.
Pour obtenir l'adresse du calendrier, aller dans les paramètres du calendrier Google,
puis trouver la section "Adresse secrète au format ical", c'est ce lien
(caché par défaut) qu'il faut utiliser.

Une fois les informations enregistrées, d'autres informations peuvent être ajoutées,
comme le nom et prénom. Pour n'afficher que le prénom sur l'interface, laisser le nom
vide. La partie "Permissions" peut être utile :

![](readme-images/permissions.png)

- Pour un ancien employé dont on veut garder l'historique mais dont on ne souhaite
plus qu'il ait accès à l'outil, décocher la case Actif
- La case Statut Équipe donne à l'utilisateur l'accès au site de configuration. Même
avec l'accès, un utilisateur non administrateur d'une entreprise n'a accès à rien sur
le site de configuration

### Types de salariés

Un salarié peut avoir deux statuts :

- normal, dans ce cas il ne voit que ses informations sur le site de Lapin Blanc
- administrateur d'une entreprise, dans ce cas il peut ajouter d'autres salariés
de cette entreprise, et depuis l'interface principale il a accès aux informations
de tous les salariés de cette entreprise

## Conventions de de nommage événements

- Lapin Blanc ignore ce qui commence par `!`
- Lapin Blanc ignore ce qu'il y a après le tiret ce qui permet d'ajouter des informations
non prises en compte, ex `nom du projet - détails`
- casse (majuscule/miniscule) : elle est ignorée, tout est converti en casse de titre
(majuscule au début des mots), sauf lorsqu'un nom est entièrement en majuscule, auquel cas
il est gardé tel quel

## Bogues connus

- Lapin Blanc ne prend pas en compte les événements récurrents.
- il faut ajouter à la main les jours fériés
- Lapin Blanc ne sait pas ignorer les événements avec invitation initiées par qqn d'autre
