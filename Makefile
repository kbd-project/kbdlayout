RENDERER = python3 ./src/kbd-layout.py
MODEL ?= models/fixtures/pc-104-ansi.json
XKB_IMPORTER = python3 ./src/import-xkb-geometry.py

models:
	$(XKB_IMPORTER) pc104 models/fixtures/pc-104-ansi.json --model-id pc-104-ansi --name "PC 104-key ANSI"
	$(XKB_IMPORTER) pc105 models/fixtures/pc-105-iso.json --model-id pc-105-iso --name "PC 105-key ISO"

render:
	@$(RENDERER) $(MODEL)
.PHONY: models render
