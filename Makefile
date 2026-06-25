RENDERER = python3 ./src/kbd-layout.py
XKB_IMPORTER = python3 ./src/import-xkb-geometry.py
CATALOG_GENERATOR = python3 ./src/generate-model-catalog.py
XKB_GEOMETRY_DIR = external/xkeyboard-config/geometry
MODEL_CATALOG = models/catalog.tsv
SERVER_PORT ?= 8000

models:
	@mkdir -p models/fixtures
	@$(CATALOG_GENERATOR) $(MODEL_CATALOG) models/fixtures/catalog.json
	@while IFS='	' read -r geometry_file geometry model_id name; do \
		case "$$geometry_file" in \#*|'') continue ;; esac; \
		$(XKB_IMPORTER) "$$geometry" "models/fixtures/$$model_id.json" \
			--model-id "$$model_id" --name "$$name" \
			--geometry-file "$(XKB_GEOMETRY_DIR)/$$geometry_file"; \
	done < $(MODEL_CATALOG)

render: models
	@while IFS='	' read -r geometry_file geometry model_id name; do \
		case "$$geometry_file" in \#*|'') continue ;; esac; \
		$(RENDERER) "models/fixtures/$$model_id.json" > "models/fixtures/$$model_id.svg"; \
	done < $(MODEL_CATALOG)

server: render
	python3 -m http.server $(SERVER_PORT)

.PHONY: models render server
