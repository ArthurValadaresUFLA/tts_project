.PHONY: docs

docs:
	uv run pdoc \
		--output-directory docs/site \
		--docformat google \
		src/tts_project
	@echo "Documentação gerada em docs/site/index.html"
