# Changelog

## v2026.03.23-1

### Added
- CBHI Form-1 report module (user + admin): create, list, view, print, CSV, Excel.
- CBHI Form-2 report module (user + admin): create, list, view, print, CSV, Excel.
- Consolidated reports now include HP, Morbidity, CBHI Form-1, and CBHI Form-2.
- Consolidated module filter (all, hp, morbidity, cbhi1, cbhi2) for page, print, CSV, and Excel.
- User edit support for all report modules.
- Admin edit support for CBHI Form-1 and CBHI Form-2.
- Admin dashboard quick links for module-wise consolidated views.

### Changed
- Login flow now supports case-insensitive username matching.
- Login accepts email as a credential (user and admin routes).

### Security and Access
- User data remains scoped to owner login ID.
- Admin routes retain full cross-user access and control.

### Deployment
- Released from branch `main`.
- App endpoint confirmed reachable: `https://possireports.onrender.com`.
