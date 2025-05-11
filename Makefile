run:
	uv run python $(filter-out $@,$(MAKECMDGOALS)) $(args)