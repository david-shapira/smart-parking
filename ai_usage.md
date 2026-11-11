# AI Usage

AI assistance was used for the Pokémon garden dashboard redesign in `web/index.html`, including its Hebrew interface text, layout and styling, Pokémon assignment and sprite display, and browser-side rendering. The dashboard continues to use the project's existing API for live data and release actions.

For this change, the API, camera simulator, and Docker Compose configuration were not changed with AI assistance.

## Percentage

No verified project-wide percentage is reported. The dashboard file was substantially AI-assisted, but saying this represents exactly 20% of the project would require a defined measure (such as lines of code, files, or development effort) and a review of the full project history. Treat any 20% figure as an informal estimate, not an audited measurement.

## Redis Data Storage

Redis writes its AOF and RDB persistence files under `/data` in the Redis container. In `docker-compose.yml`, `/data` is backed by the named Docker volume `redis-data`, so the data persists when the container is recreated. `docker compose down -v` removes the volume and its stored data.