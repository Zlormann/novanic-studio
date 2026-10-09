# NovaNic Studio 3.0 — Automatisations 💜

## État des fonctionnalités

| Fonction | Mise en place | Conditions |
| --- | --- | --- |
| Catalogue musical enrichi | Oui | GitHub Actions + GitHub Pages |
| Journal de synchronisation | Oui | GitHub Actions + GitHub Pages |
| Annonces NovaTeam | Oui | Textes générés pour les nouvelles chansons |
| Articles Blogger automatiques | Code installé | Nécessite les secrets OAuth Blogger |

La playlist officielle est `https://soundcloud.com/novanic/sets/novanic-de-lombre-aux-toiles`.
La vérification est programmée toutes les **6 heures environ** (GitHub peut retarder les exécutions).

## Pages du site

- [Générateur d'articles](https://zlormann.github.io/novanic-studio/)
- [Catalogue des chansons](https://zlormann.github.io/novanic-studio/chansons/)
- [Journal de synchronisation](https://zlormann.github.io/novanic-studio/journal/)
- [Annonces NovaTeam](https://zlormann.github.io/novanic-studio/annonces/)

Les pages sont générées automatiquement puis déployées par GitHub Actions. Le catalogue propose un lecteur SoundCloud, une fiche par chanson et une pochette **si SoundCloud fournit une image publique**. Le journal conserve au maximum 100 événements. Les annonces sont des textes à copier, **pas des publications Facebook automatiques**.

## Lancer une synchronisation manuelle

1. Ouvrir [Actions](https://github.com/Zlormann/novanic-studio/actions).
2. Choisir **NovaNic - Synchroniser SoundCloud**.
3. Cliquer sur **Run workflow**, branche `main`.
4. Ouvrir le dernier résultat et vérifier les étapes **Verifier les tests automatiques**, **Synchroniser la playlist et Blogger**, **Mettre le catalogue en ligne**.

Les tests unitaires se lancent automatiquement avant toute synchronisation. Si SoundCloud n'est pas accessible, le script échoue sans effacer l'état des chansons précédentes.

## Publication Blogger : autorisation requise

GitHub Pages ne peut pas publier seul sur Blogger. Le script utilise l'**API Blogger v3 avec OAuth 2.0** depuis GitHub Actions. Il n'utilise **pas Google Apps Script**.

### 1. Google Cloud

1. Ouvrir [Google Cloud Console](https://console.cloud.google.com/) avec le compte propriétaire du blog.
2. Créer ou choisir un projet et **activer Blogger API v3**.
3. Configurer l'écran de consentement OAuth. Pour un compte personnel, choisir le type d'utilisateur approprié et renseigner les informations demandées.
4. Créer un **client OAuth 2.0 de type Application Web**.
5. Dans ses URI de redirection autorisés, ajouter exactement `https://developers.google.com/oauthplayground`.

### 2. Autoriser le compte Blogger

1. Ouvrir [OAuth 2.0 Playground](https://developers.google.com/oauthplayground/).
2. Dans les paramètres (roue dentée), activer **Use your own OAuth credentials** et entrer **uniquement sur cette page Google** le Client ID et le Client Secret.
3. Autoriser la portée `https://www.googleapis.com/auth/blogger` avec le compte Google ayant accès au blog.
4. Échanger le code d'autorisation contre des jetons et récupérer le **refresh token**.
5. Si l'application OAuth reste en mode **Testing**, le refresh token peut expirer après 7 jours. Pour un usage durable, terminer la configuration et publier l'application OAuth lorsque nécessaire, selon les règles Google.

**Ne jamais publier, envoyer en message, capturer dans une image ou committer un Client Secret ou Refresh Token.** L'authentification doit rester privée.

### 3. Secrets GitHub

Ouvrir [Settings → Secrets and variables → Actions](https://github.com/Zlormann/novanic-studio/settings/secrets/actions), puis créer ces **Repository secrets** :

- `BLOGGER_CLIENT_ID` — identifiant du client OAuth
- `BLOGGER_CLIENT_SECRET` — secret du client OAuth
- `BLOGGER_REFRESH_TOKEN` — jeton de renouvellement OAuth
- `BLOGGER_BLOG_ID` — facultatif, ID du blog dans Blogger

Le workflow récupère ces secrets seulement au moment de l'exécution. Ils ne sont pas placés dans les pages publiques.

### 4. Choisir le mode de publication

Dans `.github/workflows/soundcloud-sync.yml` :
- `BLOGGER_AS_DRAFT: 'false'` : **publication publique automatique** des nouvelles chansons.
- `BLOGGER_AS_DRAFT: 'true'` : création de **brouillons Blogger** pour vérification manuelle.

**Le mode actuel est `false`**, mais aucun article ne peut être envoyé sans les secrets OAuth valides.

### 5. Prévenir les doublons

- Les cinq chansons mémorisées avant l'activation de la nouvelle version sont conservées comme **archives** et ne sont pas publiées rétroactivement.
- Les nouvelles chansons reçoivent un identifiant SoundCloud et un marqueur HTML unique dans l'article.
- Avant toute publication, le script cherche ce marqueur dans les articles Blogger existants (publics et brouillons).
- Si cette recherche échoue, la publication est reportée plutôt que de risquer un doublon.
- Le suivi des publications est conservé dans `chansons/state.json`.

**Limites :** les actions GitHub ne sont pas instantanées ; les métadonnées et pochettes peuvent manquer si SoundCloud bloque l'extraction ; des changements d'identifiant de piste peuvent créer un doublon malgré les protections ; le journal est public et n'affiche donc pas les secrets.

## Autorisations GitHub nécessaires

- Dépôt **public** pour le site GitHub Pages.
- **Settings → Actions → General → Workflow permissions : Read and write permissions** pour permettre au bot de sauvegarder les fichiers générés.
- **Settings → Pages → Source : GitHub Actions**.
- Le workflow utilise les permissions `contents: write`, `pages: write`, `id-token: write` pour mettre à jour le dépôt et déployer le site.
- Aucun jeton Facebook n'est nécessaire : les annonces sont seulement générées.

## Tester localement

Installer Python et `yt-dlp`, puis exécuter :

```bash
python -m pip install yt-dlp
python -m unittest discover -s tests -v
```

© 2026 NovaNic — « Pas un empire. Une maison. »
