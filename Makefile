KEYMAPS = cz.map defkeymap.map fr.map ruwin_alt-UTF-8.map uk.map
RENDERER = python3 ./src/kbd-layout.py

examples:
	mkdir -p ./examples
	echo '<ul>' >./examples/index.html
	for keymap in $(KEYMAPS); do \
		$(RENDERER) ./keymaps/$$keymap >./examples/$$keymap-ansi.svg; \
		$(RENDERER) --iso ./keymaps/$$keymap >./examples/$$keymap-iso.svg; \
		echo "<li><a href=\"$$keymap-ansi.svg\">$$keymap (ANSI)</a></li>" >>./examples/index.html; \
		echo "<li><a href=\"$$keymap-iso.svg\">$$keymap (ISO)</a></li>" >>./examples/index.html; \
	done
	echo '</ul>' >>./examples/index.html
.PHONY: examples
