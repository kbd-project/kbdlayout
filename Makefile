RENDERER = python3 ./src/kbd-layout.py
MODEL ?= models/fixtures/pc-104-ansi.json
XKB_IMPORTER = python3 ./src/import-xkb-geometry.py
XKB_GEOMETRY_DIR = external/xkeyboard-config/geometry
MODEL_CATALOG = models/catalog.tsv

models:
	@mkdir -p models/fixtures
	@while IFS='	' read -r geometry_file geometry model_id name; do \
		case "$$geometry_file" in \#*|'') continue ;; esac; \
		$(XKB_IMPORTER) "$$geometry" "models/fixtures/$$model_id.json" \
			--model-id "$$model_id" --name "$$name" \
			--geometry-file "$(XKB_GEOMETRY_DIR)/$$geometry_file"; \
	done < $(MODEL_CATALOG)

render:
	@$(RENDERER) $(MODEL)
.PHONY: models render
