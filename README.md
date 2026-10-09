# NovaNic Studio 3.0 💜

**De l’ombre aux étoiles** — générateur d'articles et automatisation musicale NovaNic.

## Accès rapide

- [✍️ Générateur d'articles](https://zlormann.github.io/novanic-studio/)
- [🎵 Catalogue musical](https://zlormann.github.io/novanic-studio/chansons/)
- [📋 Journal de synchronisation](https://zlormann.github.io/novanic-studio/journal/)
- [📣 Annonces NovaTeam](https://zlormann.github.io/novanic-studio/annonces/)
- [📖 Guide de configuration complet](AUTOMATISATION.md)

## Fonctionnement

Le générateur permet de créer des articles HTML à coller dans Blogger, avec aperçu et sauvegarde locale d'un brouillon.

Une automatisation GitHub Actions consulte toutes les 6 heures environ la [playlist SoundCloud NovaNic](https://soundcloud.com/novanic/sets/novanic-de-lombre-aux-toiles), met à jour le catalogue, récupère les titres et pochettes disponibles, génère des annonces pour les nouvelles chansons et tient un journal public. Les cinq chansons présentes au premier relevé sont conservées comme archives.

**Publication Blogger :** le code est installé mais il faut configurer les secrets OAuth Blogger dans GitHub. Sans ces secrets, aucune publication n'est effectuée. Les annonces Facebook sont des textes à copier, pas des publications automatiques.

## Tests

```bash
python -m pip install yt-dlp
python -m unittest discover -s tests -v
```

Les tests s'exécutent également avant chaque synchronisation GitHub.

© 2026 NovaNic — « Pas un empire. Une maison. »
