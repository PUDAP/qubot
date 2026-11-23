# Saved modular edges

These two edges were copied from `puda-imre-mof/edges/qubot-modules` when `main` stopped holding site edges. They are not part of `main`, and they are not the edges running on IMRE.

`miniqubot-edge` and `pipqubot-mof-edge` were built and not switched. Their Dockerfiles still expect the old `qubot-submodules` build context. Host `.env` files were not copied.

PipQuBot XL and SyringeQubot stay with the site that runs them. They are not in this directory.
