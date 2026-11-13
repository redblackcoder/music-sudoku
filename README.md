# Music Sudoku

Sudoku where digits are replaced by musical symbols, as a printable web page and a PDF generator.

- `index.html` — web app; open in a browser and print.
- `generate_puzzles.py` — reads KrazyDad Sudoku PDFs from `puzzles/<level>/` and writes `musical_sudoku_puzzles.pdf` using the same symbol mapping as the web app. Requires `pip install pymupdf`.

Source puzzles are not included; download them from krazydad.com into `puzzles/easy`, `puzzles/intermediate`, `puzzles/hard`, etc.

Music symbols use the [Bravura](https://github.com/steinbergmedia/bravura) font by Steinberg, licensed under the SIL Open Font License 1.1.
