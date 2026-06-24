RENDERER = python3 ./src/kbd-layout.py
MODEL ?= models/fixtures/minimal-ansi.json

render:
	$(RENDERER) $(MODEL)
.PHONY: render
