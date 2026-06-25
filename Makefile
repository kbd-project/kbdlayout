RENDERER = python3 ./src/kbd-layout.py
XKB_IMPORTER = python3 ./src/import-xkb-geometry.py
CATALOG_GENERATOR = python3 ./src/generate-model-catalog.py
KEYMAP_GENERATOR = python3 ./src/generate-keymaps.py
XKB_GEOMETRY_DIR = external/xkeyboard-config/geometry
MODEL_CATALOG = models/catalog.tsv
KEYMAP_SOURCE_ROOT ?= external/kbd/data/keymaps/i386
KEYMAP_ROOT ?= external/kbd/data/keymaps
MODEL_OUTPUT_ROOT ?= web/data/models
KEYMAP_OUTPUT_ROOT ?= web/data/keymaps
SERVER_PORT ?= 8000

models:
	@mkdir -p $(MODEL_OUTPUT_ROOT)
	@$(CATALOG_GENERATOR) $(MODEL_CATALOG) $(MODEL_OUTPUT_ROOT)/catalog.json
	@while IFS='	' read -r geometry_file geometry model_id name; do \
		case "$$geometry_file" in \#*|'') continue ;; esac; \
		$(XKB_IMPORTER) "$$geometry" "$(MODEL_OUTPUT_ROOT)/$$model_id.json" \
			--model-id "$$model_id" --name "$$name" \
			--geometry-file "$(XKB_GEOMETRY_DIR)/$$geometry_file"; \
	done < $(MODEL_CATALOG)

render: models
	@while IFS='	' read -r geometry_file geometry model_id name; do \
		case "$$geometry_file" in \#*|'') continue ;; esac; \
		$(RENDERER) "$(MODEL_OUTPUT_ROOT)/$$model_id.json" > "$(MODEL_OUTPUT_ROOT)/$$model_id.svg"; \
	done < $(MODEL_CATALOG)

keymaps:
	@mkdir -p $(KEYMAP_OUTPUT_ROOT)
	$(KEYMAP_GENERATOR) $(KEYMAP_SOURCE_ROOT) $(KEYMAP_OUTPUT_ROOT) --keymaps-root $(KEYMAP_ROOT)

server: render keymaps
	python3 -m http.server $(SERVER_PORT) --directory web

.PHONY: models render keymaps server
